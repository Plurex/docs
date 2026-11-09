# Plurex documentation

Mintlify site documenting the Plurex platform for developers and traders who build trading systems. Plurex (the
platform repository, `git@github.com:Plurex/plurex.git`) is the source of truth; this repository describes it from the
point of view of someone using it.

## Who owns what

- **The spec owns the reference.** `api-reference/platform/plurex-platform-api.yaml` (OpenAPI 3.2) is a byte-for-byte
  copy from `platform-public-api/` in plurex. Its operation, schema and field descriptions are the endpoint reference.
  Never edit the copy; fix wording upstream.
- **Endpoint pages are generated.** `scripts/sync-platform-api.py` writes every page under
  `api-reference/platform/{venues,hosts,accounts,paper}/` and the whole "API reference" tab navigation
  (including stream pages, placed beside their query operations). Never hand-edit them; put explanation in authored
  pages.
  - Every page references its OpenAPI operation. Streams are `QUERY` operations whose `200` is `application/jsonl` with
    an `itemSchema` message union; their pages set `playground: "none"`, because the response never finishes. The Try it playground is also off
    for every endpoint through `api.playground.display` in `docs.json`.
  - Every host and venue page carries a "Check support" block (`snippets/capability-check.mdx`). Header capabilities are
    derived from the spec; market descriptors and extra notes come from the `EXTRA` table in the script, which fails
    the sync when a path no longer exists. Change the block's wording in the snippet, and its content in `EXTRA`.
  - Every operation page shows the operation's badges (`snippets/operation-badges.mdx`). The first is its kind
    (Query, Command or Stream), from the path segment after the module, worded in the script's `KINDS` table. The
    rest come from the spec's `kind: badge` tags: label from the tag `summary`, hover text from its `description`.
- **Authored pages own the meaning.** Welcome, concepts, capabilities, guides, paper trading, the web app and the API
  reference's overview, conventions and errors pages explain how the platform is meant to be used. Link to endpoint
  pages for exact shapes instead of restating schemas field by field.
- **Screenshots are copied.** plurex keeps a screenshot of every page of the web app in `docs/screenshots`, listed in
  its README and captured by a tour of the real app with seeded test data. `scripts/sync-app-screenshots.py` copies the
  ones listed in its `SHOTS` table into `images/app/` at the locked commit, cropping any that show one dialog, and
  fails when one is missing or no longer listed upstream. Never edit or add images there by hand: add the shot to
  `SHOTS`, or ask plurex for a new one in its README. Use them on the Web app pages, in `<Frame>` with alt text that
  says what the image shows.
- **Upstream checkout.** `.upstream/plurex` is a gitignored clone pinned to the commit the docs describe
  (`upstream.lock.json`). Read source and internal design docs there, never from another working copy. It is excluded
  from Mintlify by `.mintignore`.

When authored docs and a spec disagree, the spec at the locked commit wins for shapes and the code wins for behaviour;
record the disagreement as spec feedback for plurex instead of papering over it.

## Accuracy rules

- Document only what exists at the locked commit and has appeared in the public API or the web app. Document the app
  as it is. Nothing that is only in the backend, on the roadmap or "coming soon".
- Leave out limits that are not product decisions yet, such as how many paper accounts a tenant can have. Plurex has no
  monetisation plan, and today's limits are temporary.
- Never describe how Plurex is built: no internal architecture, storage, event sourcing, policies, thresholds, internal
  module names or class names. That includes how data is sourced or served (feeds, caches, "fetched from the venue"):
  say what a value means, not how Plurex got it.
- Every claim about behaviour must be traceable to the spec or source at the locked commit. If unsure, leave it out.
- Never hard-code facts the API reports at runtime when they can change (fee rates, leverage ranges, increments,
  candle history limits). Show them as examples and tell the reader where to read the live value.
- Host and venue IDs (`bybit`, `valr`, `bybit-paper`, `valr-paper`) may appear in examples. Always tell readers to
  discover hosts and venues with the List operations.
- Never claim per-host behaviour that the reader can read from capabilities; teach them to read the capability.
- Do not document: the Bearer/OTP authentication path, internal `/api/internal` routes, the reference Kotlin client
  (unpublished), idempotency keys, request IDs, invite codes, roles other than the owner and member the app shows,
  the back office, paper "fidelity" grades or per-market fidelity, internal paper matching policy names.
- API key access, per-key permissions included, is documented as the web app presents it: its sections, presets and
  permission labels, and the operations each permission allows. Not the stored tree or its field names, which only the
  internal API carries. `platform/api-keys` owns it.
- Organisations, members and invites are documented as the web app presents them, and `platform/organisations` owns
  them. A member's access uses the same editor as a key's: link to `platform/api-keys` instead of repeating it. The
  app's labels are American (**Organization**, **New organization**); bold them as the app spells them, and write
  "organisation" in prose.
- There are two kinds of tenant: a user and an organisation. Never describe a user as having a personal or shadow
  organisation. The switcher's **Personal** is you, working as yourself.

## Vocabulary

Never use internal words: receiver, baseline, projection, warm projection, provider-sized, manifest, durable,
decider, aggregate (as an event-sourcing term), event-sourced, checkpoint, fidelity, target host, boundary (for
funding), emulation per market, core/toApi/toCore, org, user (as an owner).

Use the public words:

| Concept | Say |
| --- | --- |
| The structure listing what a host or venue supports | its **capabilities** |
| A request type such as GetOrder | an **operation**; its alternatives (ById, ByClientOrderId) are **variants** |
| Always-available operations | **always supported** |
| Plurex's continuous data for a market | Plurex's **live feed** for the market |
| The owner of accounts and API keys | the **tenant**: a user (you) or an **organisation** |
| The real host a paper host simulates | the **model host** (`modelHostId`) |
| A host market's limits | the market's **order rules** |
| Paper funding events | **funding times** |

"Aggregate" is fine in its plain sense ("an aggregated API across venues and hosts"), and "high-fidelity paper
trading" is the product's own description. What stays internal is the paper engine's fidelity assessment: grades,
per-market fidelity and substitution tables.

## Voice and style

- Keep it to the point: say what a thing is, what it does and what it returns, then only what changes how the reader
  uses it. Cut anything a badge, a schema, a capability or the conventions page already says. Badges (Query,
  Command, Stream, Check capabilities, Paged, Batch, Not safe to repeat) are not restated in prose. Wordy spec descriptions are fixed
  upstream (see `agent_plans/spec_feedback_for_plurex.md`), not around them.
- Second person, active voice, present tense. Lead with what the reader can do and why it matters.
- Trading meaning first, then what a caller needs: which operation, what to check, how to retry and reconcile.
- Be direct about limits. Where hosts differ, say so and point to the capability that says how.
- British English spelling (behaviour, recognise, cancelled), matching the spec. Enum values and field names stay
  exactly as the spec spells them.
- Short paragraphs. Use tables for comparisons, `<Steps>` for procedures, `<Note>`, `<Tip>`, `<Warning>` sparingly.
- Code: JSON bodies and `curl` with `--request QUERY` for queries and streams and `--request POST` for commands, `--header 'Content-Type: application/json'`, credentials from
  environment variables (`PLUREX_API_KEY`, `PLUREX_API_SECRET`, `PLUREX_TENANT_ID`, `PLUREX_ACCOUNT_ID`). Language-
  agnostic pseudocode or Python for algorithms. Decimal values are always JSON strings.
- Every example must validate against the spec schemas: exact field names, `type` discriminators, required fields.
- Diagrams: Mermaid code blocks.

## Mintlify

- Every page starts with frontmatter: `title` and `description` (one sentence). Do not repeat the title as an H1.
- H2 and H3 only. Internal links are absolute without extension: `[Submit an order](/api-reference/platform/hosts/submit-order)`.
- New pages must be added to `docs.json` navigation: the "Guides" tab, or the "Web app" tab for pages about the
  app. The site is not in production: move, rename and remove pages as straight cutovers, with no redirects, and fix
  every link to them.
- Validate before finishing:

  ```bash
  mint validate
  mint broken-links
  mint openapi-check api-reference/platform/plurex-platform-api.yaml
  ```

## Site map

Guides tab:

- Get started: `index`, `how-plurex-works`, `quickstart`, `authentication`
- Concepts: `concepts/venues-and-hosts`, `concepts/venues`, `concepts/hosts`, `concepts/accounts`,
  `concepts/instruments`
- Capabilities: `capabilities/overview`, `capabilities/host-capabilities`, `capabilities/order-rules`,
  `capabilities/venue-capabilities`
- Trading guides: `guides/orders`, `guides/streams`, `guides/portfolio`, `guides/market-data`
- Paper trading: `paper/overview`, `paper/leverage-and-liquidation`, `paper/fees-and-funding`, `paper/going-live`

API reference tab: `api-reference/platform/{overview,conventions,errors}` then the generated pages.

Web app tab:

- Web app: `platform/overview`, `platform/terminal`, `platform/accounts`, `platform/add-exchange`
- Access and security: `platform/organisations`, `platform/api-keys`, `platform/settings`

## Refreshing from plurex

The plan is in `agent_plans/automated_docs_bootstrap.md`. Until the refresh tooling exists: update `.upstream/plurex`,
copy the spec from `platform-public-api/` at the target commit, run `scripts/sync-platform-api.py` and
`scripts/sync-app-screenshots.py` (see README), look at every screenshot that changed, review authored pages against the
changes, and update `upstream.lock.json`.

## Git

Never commit unless explicitly asked. No AI attribution in commits or pull requests. Never use `--no-verify`.
