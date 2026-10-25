#!/usr/bin/env python3
"""Sync Mintlify's API reference from the canonical Platform OpenAPI and AsyncAPI documents."""

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api-reference/platform"
SOURCE = API / "plurex-platform-api.yaml"
STREAMS = API / "plurex-platform-async-api.yaml"

# Keep established URLs where their operations still exist.
SLUGS = {
    "ListOpenOrders": "list-orders",
    "ListOpenPositions": "list-positions",
    "ListAccountMarginStates": "list-margin-states",
    "GetAccountMarketState": "get-market-state",
    "GetMarketLeverage": "get-leverage",
    "SetMarketLeverage": "set-leverage",
    "GetMarketPositionMode": "get-position-mode",
    "SetMarketPositionMode": "set-position-mode",
    "CreateAccount": "create",
}


def slug_for(action):
    return SLUGS.get(action, re.sub(r"(?<!^)(?=[A-Z])", "-", action).lower())


def frontmatter(metadata):
    # JSON strings are also valid YAML scalars, including multiline text.
    return "---\n" + "".join(f"{key}: {json.dumps(value)}\n" for key, value in metadata.items()) + "---\n"


def sync():
    source = yaml.safe_load(SOURCE.read_text())
    streams = yaml.safe_load(STREAMS.read_text())
    tags = {tag["name"]: tag for tag in source["tags"]}
    pages_by_tag = {}
    pages = []
    for path, item in source["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "put", "post", "delete", "patch", "head", "options", "trace"}:
                continue
            module = path.split("/")[3]
            action = path.rsplit("/", 1)[1]
            slug = slug_for(action)
            page = f"api-reference/platform/{module}/{slug}"
            nav_tags = [tag for tag in operation["tags"] if tags[tag].get("kind") == "nav"]
            if len(nav_tags) != 1:
                raise ValueError(f"Expected one navigation tag for {path}")
            pages_by_tag.setdefault(nav_tags[0], []).append(page)
            metadata = {
                "title": operation["summary"],
                "description": operation.get("description", operation["summary"]),
                "openapi": f"/{SOURCE.relative_to(ROOT)} {method.upper()} {path}",
            }
            pages.append((ROOT / f"{page}.mdx", frontmatter(metadata)))

    # AsyncAPI operations carry the domain tag, then the OpenAPI nav leaf, so each stream sits beside its REST
    # operations.
    for key, operation in streams["operations"].items():
        channel = streams["channels"][operation["channel"]["$ref"].rsplit("/", 1)[1]]
        parts = channel["address"].split("/")
        module, action = parts[3], parts[5]
        page = f"api-reference/platform/{module}/{slug_for(action)}"
        leaf = operation["tags"][1]["name"]
        if tags.get(leaf, {}).get("kind") != "nav":
            raise ValueError(f"Stream {key} has no OpenAPI navigation tag")
        pages_by_tag.setdefault(leaf, []).append(page)
        metadata = {
            "title": operation["summary"],
            "description": operation.get("description", operation["summary"]),
            "asyncapi": f"/{STREAMS.relative_to(ROOT)} {key}",
        }
        pages.append((ROOT / f"{page}.mdx", frontmatter(metadata)))

    def group(name):
        tag = tags[name]
        children = [group(child) for child, value in tags.items() if value.get("parent") == name and value.get("kind") == "nav"]
        return {"group": tag.get("summary", name), "pages": pages_by_tag.get(name, []) + children}

    config_path = ROOT / "docs.json"
    config = json.loads(config_path.read_text())
    reference = next(tab for tab in config["navigation"]["tabs"] if tab["tab"] == "API reference")
    reference["groups"] = [
        {"group": "Getting started", "pages": [
            "api-reference/platform/overview",
            "api-reference/platform/conventions",
            "api-reference/platform/errors",
        ]},
        *[group(name) for name, tag in tags.items() if tag.get("kind") == "nav" and "parent" not in tag],
    ]

    for path, content in pages:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Synced {len(pages)} operations and streams and API navigation from {SOURCE.relative_to(ROOT)} and {STREAMS.relative_to(ROOT)}")


if __name__ == "__main__":
    sync()
