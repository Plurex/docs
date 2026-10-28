# Plurex documentation

Mintlify documentation for the [Plurex platform](https://platform.plurex.io), public market data, account trading and paper trading.

## Local development

Install or upgrade the Mintlify CLI, then start the preview from this directory:

```bash
npm install --global mint@latest
mint dev
```

The preview runs at `http://localhost:3000`. Site settings and navigation live in `docs.json`. OpenAPI 3.2 support and build validation have been verified with Mintlify CLI `4.2.1125`.

## Updating the Platform API

The docs describe a pinned commit of the [plurex repository](https://github.com/Plurex/plurex), recorded in `upstream.lock.json`. `.upstream/plurex` is a gitignored clone of it, checked out at that commit and excluded from Mintlify by `.mintignore`. See `AGENTS.md` for how the spec and authored pages divide the work, and `agent_plans/automated_docs_bootstrap.md` for the refresh plan.

`api-reference/platform/plurex-platform-api.yaml` (**OpenAPI 3.2**) is a copy of `platform-public-api/` at the pinned commit. Every endpoint and stream page references it directly, preserving its schemas, tag hierarchy and operation metadata. Streams are `POST` operations with an `application/jsonl` `200` response described by `itemSchema`; their pages turn the playground off.

After replacing the spec, sync the endpoint and stream pages and the API reference navigation:

```bash
python3 -m venv /tmp/plurex-docs-venv
/tmp/plurex-docs-venv/bin/pip install -r scripts/requirements.txt
/tmp/plurex-docs-venv/bin/python scripts/sync-platform-api.py
```

The script uses the spec's navigation tags, summaries and descriptions, while retaining established URLs for existing operations. It writes endpoint pages, stream pages and the whole API reference tab, placing each stream beside its query operations, adds a capability check (`snippets/capability-check.mdx`) to every host and venue page, and shows each operation's badges (`snippets/operation-badges.mdx`): its kind (Query, Command or Stream, from the path) and then the spec's badge tags; keep explanatory prose in authored pages. When operations are removed, remove their obsolete pages and add appropriate redirects in `docs.json`.

Validate changes with an up-to-date Mintlify CLI:

```bash
mint openapi-check api-reference/platform/plurex-platform-api.yaml
mint validate
mint broken-links
```

## Publishing

The Mintlify GitHub integration deploys changes pushed to the configured default branch. Manage the integration in the [Mintlify dashboard](https://dashboard.mintlify.com).
