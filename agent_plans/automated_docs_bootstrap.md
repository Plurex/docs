# Automated documentation: tooling and bootstrap

Status (2026-10-25): planned. Phase 1 builds the tooling; Phase 2 runs once plurex WIP is on `main`; Phase 3 is the
steady-state refresh. Update this file when a phase completes or a decision changes.

Goals:

1. The docs record exactly which plurex commit they describe, so drift is always measurable.
2. Every plurex change since that commit is evaluated for documentation impact. A "no impact" verdict is a recorded
   decision, never a silent skip.
3. Agents understand changes semantically (what changed for a developer), and their output is checked against the
   source of truth before it reaches review.
4. Plurex stays the only source of truth for the API contract. The docs repo copies, renders and explains it, and never
   redefines it.

The repos stay separate. `platform-public-api/` (OAS, AGENTS.md, DESIGN.md) is the contract boundary. The
module AGENTS.md files and `agent_plans/` describe behaviour that never appears in the spec.

## Concepts

- **Upstream ref.** The plurex ref the docs track. `origin/main` before production. After release, the lock follows the
  deployed commit or release tag, so docs never run ahead of what users can call. Scripts take a ref; nothing hardcodes
  `main`.
- **Lock.** `upstream.lock.json` at the repo root: `{repo, ref, commit, syncedAt, refreshLog}`. It is written only by a
  completed refresh.
- **Reference checkout.** `.upstream/plurex`: a gitignored clone of `git@github.com:Plurex/plurex.git`, owned by
  the scripts and never edited by hand or by agents. It sits on a detached HEAD at the commit being worked on (the
  target during a refresh, the lock commit otherwise), so agents can read and search the exact source as plain files.
  It is independent of anyone's working plurex checkout and its branches or WIP, and in CI it is the same path
  (`actions/checkout` with `path: .upstream/plurex`). Not a submodule: a pointer to a private repo would break the
  Mintlify deploy, and the lock already records the commit.
- **Range.** `<lock.commit>..<target commit>`, first-parent, read from the reference checkout after a fetch.
- **Refresh log.** `refresh-log/<date>-<from7>-<to7>.md`, one per run. It records every commit with its triage tier,
  the topics, each topic's verdict and reason, and the pages changed. This is the audit trail, and the next run reads
  it as context.

## Phase 1 — Tooling (this repo)

### 1.1 Docs AGENTS.md

`AGENTS.md` at the root, with `CLAUDE.md` pointing to it. Fold in `.junie/guidelines.md` and then delete it (or reduce
it to a pointer). Content:

- Audience and voice: written for traders and developers who build trading systems; second person; trading meaning
  first.
- Banned internal vocabulary. Inherit the list from platform-public-api AGENTS.md "Spec descriptions" (receiver,
  baseline, projection, provider-sized, manifest, durable, and so on) and extend it as new terms leak.
- Generated vs authored. Endpoint pages are generated from the OAS by `sync-platform-api.py`, so explanation goes in
  guides and conventions pages, never in endpoint frontmatter. The spec's descriptions are the reference; guides link
  to them rather than restate schemas.
- Never document beyond the spec at the locked commit: no roadmap items, nothing marked as planned.
- Removed operations get redirects in `docs.json`.
- Validation: `mint openapi-check`, `mint validate`, `mint broken-links`.
- Git: no commits without explicit instruction; no AI attribution.

### 1.2 Triage path map

`scripts/triage-paths.yaml`: ordered glob → tier rules, first match wins. Tiers:

| Tier | Meaning | Initial paths |
|------|---------|---------------|
| `contract` | Always deep-reviewed | `platform-public-api/*.yaml`, `platform-public-api/DESIGN.md`, `platform-public-api/AGENTS.md` |
| `behaviour` | Deep-reviewed unless triage proves internal | `platform-public-api/src/**`, `platform-server/**`, `execution-host*/**`, `execution-venue/**`, `execution-providers/**`, `execution-accounts/**`, `execution-common/**`, module `AGENTS.md` |
| `context` | Read for intent, rarely a direct doc change | `agent_plans/**`, root `AGENTS.md` |
| `product` | Affects app guides (`platform/*`) | `platform-app/**` |
| `ignore` | Recorded in the log, no agent review | `platform-android-app/**`, `monitoring/**`, `docker*/**`, `aws/**`, `build/**`, `gradle/**`, `*.conf`, `telemetry/**`, `admin/**` |

A commit's tier is the highest tier among its paths. Unmatched paths default to `behaviour`, so a new module gets
reviewed until it is mapped. Tune the map from the refresh logs.

### 1.3 Scripts

All deterministic, with no agent involvement. They take `--ref` (default `origin/main`) and work on
`.upstream/plurex`.

- `.gitignore` gains `.upstream/`. The leading dot also keeps it out of Mintlify's page scan. Confirm that `mint dev`
  and `mint validate` ignore it (add a `.mintignore` entry if they don't), and that agents can still search it
  explicitly even though it is gitignored.
- `scripts/plurex_checkout.py [--commit <sha>]`: clones the repo if it is missing, fetches, and checks out the given
  commit detached (default: the lock commit). It refuses to run if the checkout has local changes, and prints the
  resolved commit.
- `scripts/plurex_range.py`: fetches, resolves the target commit, and emits JSON for the range: per commit the sha,
  subject, body, author date, touched paths with tiers, diffstat and commit tier. With no lock (bootstrap) it emits only
  the target commit and `"mode": "bootstrap"`.
- `scripts/sync_from_plurex.py --commit <sha>`: copies the OAS with `git show <sha>:<path>`, so the copy
  depends only on the commit, not on where the checkout sits, then runs `sync-platform-api.py`, and then the three `mint` checks. It does not write the lock.
- `scripts/write_lock.py --commit <sha> --log <file>`: the final step of a successful refresh.
- `scripts/check_drift.py`: prints the lock commit, the target commit, commits behind, and counts per tier. This is the
  "should I refresh?" check.

`sync-platform-api.py` stays as it is. Removed operations are reported, never deleted silently.

### 1.4 Streams in the docs

Done. Streams are OpenAPI 3.2 operations (`application/jsonl` with `itemSchema`), so `sync-platform-api.py` generates
their pages like any other, with the playground off. The AsyncAPI document was removed upstream in `1d46584e7`.

### 1.5 Refresh skill and workflow

A project skill. The scripts in `scripts/` do the mechanical work (which commits, which files) and stay runnable
without Claude, by hand or in CI. The skill owns the judgement (what the changes mean for the docs).

- `.claude/skills/refresh-docs/SKILL.md` contains the procedure below. It is user-invoked only (`/refresh-docs
  [--ref <ref>]`), never triggered automatically, because it rewrites docs. Supporting files sit next to it and load
  on demand: `rubric.md` (tiers, verdicts, when to `ask`), `log-template.md`, and `bootstrap.md` (the Phase 2
  procedure, selected when there is no lock).
- `.claude/agents/` defines one project subagent per role, each with its own tool limits. `docs-triage` is read-only.
  `docs-topic-reviewer` reads `.upstream/plurex` and the docs, with no edits. `docs-writer` edits docs pages only.
  `docs-verifier` is read-only and runs Bash for the `mint` checks; it never edits, so it cannot fix what it judges.
- The topic reviews run in parallel. The skill can either start the subagents itself or run a Workflow; decide in
  Phase 1 after a trial run on a real commit range.

The workflow:

1. **Triage** (one agent, cheap). Input: the range JSON and the previous refresh log. It confirms or overrides each
   commit's path tier and gives a reason for each override. `ignore` commits are logged without review.
2. **Topics.** The agent groups the relevant commits into topics (for example "candles", "cancel semantics", "VALR
   support"). Commits that build on or reverse each other land in the same topic.
3. **Deep review** (one agent per topic, in parallel). It reads the full diffs plus the relevant AGENTS.md, DESIGN.md
   and plans, then judges the topic **by its state at the target commit**, not by the history. Output: what changed
   for a developer; the affected pages (searched by operationId, schema name and concept); and a verdict of `update`,
   `new-content`, `no-impact` or `ask`, with a reason.
4. **Draft.** Edits for `update` and `new-content` topics. `ask` topics are collected as questions for Laurence and
   left undrafted.
5. **Verify** (independent agent). It checks every changed claim against the spec and source at the target commit,
   runs the banned-vocabulary check, and **challenges each `no-impact` verdict on `behaviour`-tier commits**.
   Disagreements go back to the draft step once, then into the log as `ask`.
6. **Close.** Run the `mint` checks and write the refresh log. Write the lock only if nothing is left unresolved (or
   Laurence accepts the open `ask` items). Leave everything uncommitted for review.

Done when: running the command against a range of a few known commits produces a log with correct tiers and sensible
verdicts.

## Phase 2 — Bootstrap run (after plurex WIP lands on `main`)

There is no lock, so the bootstrap is a **full reconciliation**, not a diff. Prerequisite: the current docs WIP on
`platform-api-v1-refresh` is committed first, so the bootstrap's changes can be reviewed on their own.

1. **Pin.** Run `plurex_checkout.py --commit origin/main` to create the reference checkout and pin it. Everything below
   reads that commit.
2. **Sync.** Run `sync_from_plurex.py` and record the generated-page delta.
3. **Source digest** (agent). A structured summary of the public product at the pinned commit: the domains, concepts,
   capabilities, paging, errors, auth, streams, paper, and the supported hosts and venues. It is drawn from the
   OAS info and tag descriptions, platform-public-api AGENTS.md and DESIGN.md, the module AGENTS.md files, and the
   roadmap (used only to separate shipped from planned). Saved as `refresh-log/bootstrap-digest.md` for later runs to
   use.
4. **Page audit** (parallel agents, one per authored page or group: `index`, `platform/*`, `api-reference/platform/{overview,quickstart,conventions}`).
   Each claim is classified as correct, stale, wrong or unverifiable against the digest and spec.
5. **Gap analysis and information architecture.** Concepts in the digest with no guide. Likely candidates: capabilities
   ("what can this account do"), paging and reconciliation, size vs notional, paper as a host, errors and retries,
   streams, and instruments and symbols. The output is a proposed nav, plus a list of new pages ranked by developer value.
   **Laurence approves the information architecture before drafting.**
6. **Draft and verify.** Same as Phase 1.5 steps 4–5, applied to audit fixes and the approved new pages.
7. **Close.** Run the `mint` checks, write `refresh-log/<date>-bootstrap-<to7>.md`, and write the first lock.

## Phase 3 — Steady state

- Run `scripts/check_drift.py` whenever plurex merges something notable, and `/refresh-docs` when it reports
  `contract` or `behaviour` commits.
- Later: a plurex GitHub Action on `main` sends a `repository_dispatch` to the docs repo, which opens an issue (or a
  draft PR from the refresh) with the drift summary.
- At release, switch the ref from `origin/main` to the deployed commit or release tag.
- Optional plurex convention: add "docs repo" to the "change together" list in platform-public-api AGENTS.md, as a
  docs-impact note in the commit message rather than a same-commit edit.

## Open questions

- Is the docs repo public? If so, the refresh logs must not quote internal diffs or plans verbatim, only their public
  meaning. (The log format assumes this until confirmed.)
- Whether reference SDK examples (Kotlin client) belong in the docs, and whether they come from plurex tests.
