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

The docs describe a pinned commit of the [plurex repository](https://github.com/Plurex/plurex), recorded in `upstream.lock.json`. `.upstream/plurex` is a gitignored clone of it, checked out at that commit and excluded from Mintlify by `.mintignore`. See `AGENTS.md` for how the specs and authored pages divide the work, and `agent_plans/automated_docs_bootstrap.md` for the refresh plan.

`api-reference/platform/plurex-platform-api.yaml` (**OpenAPI 3.2**) and `plurex-platform-async-api.yaml` (**AsyncAPI 3.0**) are copies of `platform-public-api/` at the pinned commit. Endpoint pages reference the OpenAPI file directly, preserving its schemas, tag hierarchy and operation metadata. Stream pages are rendered to MDX from the AsyncAPI file, because Mintlify's AsyncAPI view does not show nested unions or nullable references. Each stream page embeds its event payload with `openapi-schema` frontmatter, so Mintlify renders it from the OpenAPI file; the sync fails if that schema differs in shape between the two files.

After replacing the specs, sync the endpoint and stream pages and the API reference navigation:

```bash
python3 -m venv /tmp/plurex-docs-venv
/tmp/plurex-docs-venv/bin/pip install -r scripts/requirements.txt
/tmp/plurex-docs-venv/bin/python scripts/sync-platform-api.py
```

The script uses the spec's navigation tags, summaries and descriptions, while retaining established URLs for existing operations. It writes endpoint pages, stream pages and the whole API reference tab, placing each stream beside its HTTP operations, adds a capability check (`snippets/capability-check.mdx`) to every host and venue page, and shows each operation's badges (`snippets/operation-badges.mdx`) from the spec's badge tags; keep explanatory prose in authored pages. When operations are removed, remove their obsolete pages and add appropriate redirects in `docs.json`.

Validate changes with an up-to-date Mintlify CLI:

```bash
mint openapi-check api-reference/platform/plurex-platform-api.yaml
mint validate
mint broken-links
```

## Publishing

The Mintlify GitHub integration deploys changes pushed to the configured default branch. Manage the integration in the [Mintlify dashboard](https://dashboard.mintlify.com).
