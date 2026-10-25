# Plurex documentation

Mintlify site documenting the Plurex platform for developers and traders who build trading systems. Plurex (the
platform repository, `git@github.com:Plurex/plurex.git`) is the source of truth; this repository describes it from the
point of view of someone using it.

## Who owns what

- **The specs own the reference.** `api-reference/platform/plurex-platform-api.yaml` (OpenAPI 3.2) and
  `plurex-platform-async-api.yaml` (AsyncAPI 3.0) are byte-for-byte copies from `platform-public-api/` in plurex. Their
  operation, schema and field descriptions are the endpoint reference. Never edit the copies; fix wording upstream.
- **Endpoint pages are generated.** `scripts/sync-platform-api.py` writes every page under
  `api-reference/platform/{venues,hosts,accounts,paper}/` and the whole "API reference" tab navigation (including stream
  pages, placed beside their REST operations). Never hand-edit them; put explanation in authored pages.
- **Authored pages own the meaning.** Welcome, concepts, capabilities, guides, paper trading, the web app and the API
  reference's overview, conventions and errors pages explain how the platform is meant to be used. Link to endpoint
  pages for exact shapes instead of restating schemas field by field.
- **Upstream checkout.** `.upstream/plurex` is a gitignored clone pinned to the commit the docs describe
  (`upstream.lock.json`). Read source and internal design docs there, never from another working copy. It is excluded
  from Mintlify by `.mintignore`.

When authored docs and a spec disagree, the spec at the locked commit wins for shapes and the code wins for behaviour;
record the disagreement as spec feedback for plurex instead of papering over it.

## Accuracy rules

- Document only what exists at the locked commit. No roadmap items, no "coming soon", nothing planned.
- Never describe how Plurex is built: no internal architecture, storage, event sourcing, policies, thresholds, internal
  module names or class names.
- Every claim about behaviour must be traceable to the spec or source at the locked commit. If unsure, leave it out.
- Never hard-code facts the API reports at runtime when they can change (fee rates, leverage ranges, increments,
  candle history limits). Show them as examples and tell the reader where to read the live value.
- Host and venue IDs (`bybit`, `valr`, `bybit-paper`, `valr-paper`) may appear in examples. Always tell readers to
  discover hosts and venues with the List operations.
- Never claim per-host behaviour that the reader can read from capabilities; teach them to read the capability.
- Do not document: the Bearer/OTP authentication path, internal `/api/internal` routes, the reference Kotlin client
  (unpublished), market-data streams, idempotency keys, request IDs, per-key scopes, organisations or teams, invite
  codes, the app dashboard or subscription screens, paper "fidelity" grades or per-market fidelity, internal paper
  matching policy names.

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
| The owner of accounts and API keys | the **tenant** |
| The real host a paper host simulates | the **model host** (`modelHostId`) |
| A host market's limits | the market's **order rules** |
| Paper funding events | **funding times** |

"Aggregate" is fine in its plain sense ("an aggregated API across venues and hosts"), and "high-fidelity paper
trading" is the product's own description. What stays internal is the paper engine's fidelity assessment: grades,
per-market fidelity and substitution tables.

## Voice and style

- Second person, active voice, present tense. Lead with what the reader can do and why it matters.
- Trading meaning first, then what a caller needs: which operation, what to check, how to retry and reconcile.
- Be direct about limits. Where hosts differ, say so and point to the capability that says how.
- British English spelling (behaviour, recognise, cancelled), matching the specs. Enum values and field names stay
  exactly as the spec spells them.
- Short paragraphs. Use tables for comparisons, `<Steps>` for procedures, `<Note>`, `<Tip>`, `<Warning>` sparingly.
- Code: JSON bodies and `curl` with `--request POST`, `--header 'Content-Type: application/json'`, credentials from
  environment variables (`PLUREX_API_KEY`, `PLUREX_API_SECRET`, `PLUREX_TENANT_ID`, `PLUREX_ACCOUNT_ID`). Language-
  agnostic pseudocode or Python for algorithms. Decimal values are always JSON strings.
- Every example must validate against the spec schemas: exact field names, `type` discriminators, required fields.
- Diagrams: Mermaid code blocks.

## Mintlify

- Every page starts with frontmatter: `title` and `description` (one sentence). Do not repeat the title as an H1.
- H2 and H3 only. Internal links are absolute without extension: `[Submit an order](/api-reference/platform/hosts/submit-order)`.
- New pages must be added to `docs.json` navigation (the "Documentation" tab). Removed or moved pages need a redirect.
- Validate before finishing:

  ```bash
  mint validate
  mint broken-links
  mint openapi-check api-reference/platform/plurex-platform-api.yaml
  ```

## Site map

Documentation tab:

- Get started: `index`, `how-plurex-works`, `quickstart`, `authentication`
- Concepts: `concepts/venues-and-hosts`, `concepts/venues`, `concepts/hosts`, `concepts/accounts`,
  `concepts/instruments`
- Capabilities: `capabilities/overview`, `capabilities/host-capabilities`, `capabilities/order-rules`,
  `capabilities/venue-capabilities`
- Trading guides: `guides/orders`, `guides/streams`, `guides/portfolio`, `guides/market-data`
- Paper trading: `paper/overview`, `paper/fees-and-funding`, `paper/going-live`
- Web app: `platform/overview`, `platform/add-exchange`

API reference tab: `api-reference/platform/{overview,conventions,errors}` then the generated pages.

## Refreshing from plurex

The plan is in `agent_plans/automated_docs_bootstrap.md`. Until the refresh tooling exists: update `.upstream/plurex`,
copy both spec files from `platform-public-api/` at the target commit, run `scripts/sync-platform-api.py` (see
README), review authored pages against the changes, and update `upstream.lock.json`.

## Git

Never commit unless explicitly asked. No AI attribution in commits or pull requests. Never use `--no-verify`.
