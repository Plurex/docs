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

`api-reference/platform/plurex-platform-api.yaml` (**OpenAPI 3.2**) and `plurex-platform-async-api.yaml` (**AsyncAPI 3.0**) are copies of `platform-public-api/` at the pinned commit. Endpoint and stream pages reference these files directly, preserving their schemas, tag hierarchy and operation metadata.

After replacing the specs, sync the endpoint and stream pages and the API reference navigation:

```bash
python3 -m venv /tmp/plurex-docs-venv
/tmp/plurex-docs-venv/bin/pip install -r scripts/requirements.txt
/tmp/plurex-docs-venv/bin/python scripts/sync-platform-api.py
```

The script uses the spec's navigation tags, summaries and descriptions, while retaining established URLs for existing operations. It writes endpoint and stream frontmatter and the whole API reference tab, placing each stream beside its HTTP operations; keep explanatory prose in authored pages. When operations are removed, remove their obsolete pages and add appropriate redirects in `docs.json`.

Validate changes with an up-to-date Mintlify CLI:

```bash
mint openapi-check api-reference/platform/plurex-platform-api.yaml
mint validate
mint broken-links
```

## Publishing

The Mintlify GitHub integration deploys changes pushed to the configured default branch. Manage the integration in the [Mintlify dashboard](https://dashboard.mintlify.com).
