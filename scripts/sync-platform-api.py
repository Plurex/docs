#!/usr/bin/env python3
"""Sync Mintlify's API reference from the canonical Platform OpenAPI document."""

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api-reference/platform"
SOURCE = API / "plurex-platform-api.yaml"

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

# Header and market summary schemas per capability source.
SOURCES = {
    "hosts": ("host", "ExecutionHostCapabilities", "HostMarketSummary"),
    "venues": ("venue", "VenueCapabilities", "VenueMarketSummary"),
}

# Discovery operations are where capabilities are read, so they get no check.
DISCOVERY = {"List", "ListMarkets"}

# The operation kind is the path segment after the module (/api/v1/hosts/command/SubmitOrder). Its badge comes first.
KINDS = {
    "query": ("Query", "Reads state and changes nothing. Always safe to repeat."),
    "command": ("Command", "Changes state. Safe to repeat unless it has the Not safe to repeat badge."),
    "stream": (
        "Stream",
        "The response stays open and carries one JSON message per line until an Ended line.",
    ),
}

# What the header leaves alone do not say: market descriptors, plain header values, and notes on leaves that are not
# request variants. "resolves" marks market descriptors that settle a PerMarket header leaf. Every path is checked
# against the spec, so a renamed field fails the sync.
EXTRA = {
    "SubmitOrder": {
        "notes": {"orders.submitOrder.clientOrderId": "when you send a clientOrderId"},
        "market": [
            ("orderTypes.market", "non-null when the market accepts Market orders"),
            ("orderTypes.triggerLimit", "non-null when it accepts TriggerLimit orders"),
            ("orderTypes.triggerMarket", "non-null when it accepts TriggerMarket orders"),
            ("orderTypes.limit", "always present; its terms are the Limit order rules"),
        ],
    },
    "GetMarketLeverage": {
        "resolves": True,
        "market": [("settings.leverage.get", "true when this market's leverage can be read")],
    },
    "SetMarketLeverage": {
        "resolves": True,
        "market": [
            ("settings.leverage.setEffectScope", "non-null when this market's leverage can be set"),
            ("settings.leverage.min", "with max and step, the values you can set"),
        ],
    },
    "GetMarketPositionMode": {
        "resolves": True,
        "market": [("settings.positionMode.get", "true when this market's position mode can be read")],
    },
    "SetMarketPositionMode": {
        "resolves": True,
        "market": [
            ("settings.positionMode.setEffectScope", "non-null when this market's position mode can be set"),
            ("settings.positionMode.values", "the modes you can set"),
        ],
    },
    "GetPrices": {
        "resolves": True,
        "market": [("marketData.prices.{kind}.get", "true for each price kind the market serves")],
    },
    "GetBestQuotes": {
        "resolves": True,
        "market": [("marketData.bestQuote.get", "true when the market serves a best quote")],
    },
    "GetMarketStatistics": {
        "resolves": True,
        "market": [
            ("marketData.statistics.get", "true when the market serves statistics"),
            ("marketData.statistics.supportedFields", "which statistics it reports"),
        ],
    },
    "GetIndicativeFundings": {
        "resolves": True,
        "market": [("marketData.indicativeFunding.get", "true when the market serves indicative funding")],
    },
    "GetOpenInterests": {
        "resolves": True,
        "market": [("marketData.openInterest.get", "true when the market serves open interest")],
    },
    "ListCandles": {
        "resolves": True,
        "market": [
            ("marketData.candles.{priceKind}.list", "true when the series can be listed with ByInstrument"),
            ("marketData.candles.{priceKind}.listBefore", "true when it can be listed with ByInstrumentBefore"),
            ("marketData.candles.{priceKind}.supportedIntervals", "the intervals you can request"),
        ],
    },
    "ListTransactions": {
        "header": [("accountTransactions.supportedTransactionTypes", "the posting types the host reports")],
    },
    "SubscribeToPrices": {
        "resolves": True,
        "market": [("marketData.prices.{kind}.subscribe", "true for each price kind the market streams")],
    },
    "SubscribeToBestQuotes": {
        "resolves": True,
        "market": [("marketData.bestQuote.subscribe", "true when the market streams its best quote")],
    },
    "SubscribeToMarketStatistics": {
        "resolves": True,
        "market": [
            ("marketData.statistics.subscribe", "true when the market streams statistics"),
            ("marketData.statistics.supportedFields", "which statistics it reports"),
        ],
    },
    "SubscribeToIndicativeFundings": {
        "resolves": True,
        "market": [("marketData.indicativeFunding.subscribe", "true when the market streams indicative funding")],
    },
    "SubscribeToOpenInterests": {
        "resolves": True,
        "market": [("marketData.openInterest.subscribe", "true when the market streams open interest")],
    },
    "SubscribeToCandles": {
        "resolves": True,
        "market": [
            ("marketData.candles.{priceKind}.subscribe", "true when the series can be streamed"),
            ("marketData.candles.{priceKind}.supportedIntervals", "the intervals you can request"),
        ],
    },
    "SubscribeToAccountOrders": {
        "header": [
            ("accountOrders.changes", "the change types the host sends"),
            ("accountOrders.includesFillDetails", "whether FillApplied events carry the execution"),
        ],
    },
    "SubscribeToAccountTransactions": {
        "header": [("accountTransactions.supportedTransactionTypes", "the posting types the host reports")],
    },
}


def slug_for(action):
    return SLUGS.get(action, re.sub(r"(?<!^)(?=[A-Z])", "-", action).lower())


def lower_camel(name):
    return name[:1].lower() + name[1:]


def frontmatter(metadata):
    # JSON strings are also valid YAML scalars, including multiline text.
    return "---\n" + "".join(f"{key}: {json.dumps(value)}\n" for key, value in metadata.items()) + "---\n"


class Schemas:
    """Resolves local schema references in one spec."""

    def __init__(self, spec):
        self.schemas = spec["components"]["schemas"]

    def name(self, schema):
        return schema["$ref"].rsplit("/", 1)[1] if "$ref" in schema else None

    def resolve(self, schema):
        while "$ref" in schema:
            schema = self.schemas[self.name(schema)]
        return schema

    def nullable_inner(self, schema):
        """The non-null member of `anyOf: [X, null]`, or None."""
        members = schema.get("anyOf") or []
        rest = [member for member in members if member.get("type") != "null"]
        return rest[0] if len(members) == 2 and len(rest) == 1 else None

    def variant_value(self, schema):
        """The single `type` value that identifies a union member, if it has one."""
        enum = self.resolve(schema).get("properties", {}).get("type", {}).get("enum", [])
        return enum[0] if len(enum) == 1 else None



# Capabilities


def capability_leaves(schemas, root):
    """Map each header capability path to its kind: always, support, cursor or value."""
    leaves = {}

    def walk(schema, path):
        name = schemas.name(schema)
        if name == "Supported":
            leaves[path] = "always"
            return
        if name == "OperationSupport":
            leaves[path] = "support"
            return
        if name == "CursorQueryCapability":
            leaves[path] = "cursor"
            return
        resolved = schemas.resolve(schema)
        if resolved.get("type") == "object" and "properties" in resolved:
            for key, child in resolved["properties"].items():
                walk(child, f"{path}.{key}" if path else key)
        else:
            leaves[path] = "value"

    walk({"$ref": f"#/components/schemas/{root}"}, "")
    return leaves


def summary_paths(schemas, root):
    """Every field path in a market summary, through nullable descriptors."""
    paths = set()

    def walk(schema, path, depth):
        if depth > 6:
            return
        inner = schemas.nullable_inner(schema)
        resolved = schemas.resolve(inner or schema)
        if path:
            paths.add(path)
        if resolved.get("type") == "object":
            for key, child in resolved.get("properties", {}).items():
                walk(child, f"{path}.{key}" if path else key, depth + 1)

    walk({"$ref": f"#/components/schemas/{root}"}, "", 0)
    return paths


def request_variants(schemas, operation):
    """Map lowerCamel request values to the field and value a reader sends, e.g. byId -> query.type ById."""
    body = schemas.resolve(operation["requestBody"]["content"]["application/json"]["schema"])
    variants = {}
    for field, schema in body.get("properties", {}).items():
        resolved = schemas.resolve(schema)
        for member in resolved.get("oneOf", []):
            value = schemas.variant_value(member)
            if value:
                variants[lower_camel(value)] = {"field": f"{field}.type", "value": value}
        for value in resolved.get("enum", []):
            variants.setdefault(lower_camel(value), {"field": field, "value": value})
    return variants


def capability_check(schemas, module, action, operation):
    """The CapabilityCheck props for one operation, or None for discovery operations."""
    if module not in SOURCES or action in DISCOVERY:
        return None
    source, header_root, market_root = SOURCES[module]
    leaves = capability_leaves(schemas, header_root)
    market_fields = summary_paths(schemas, market_root)
    extra = EXTRA.get(action, {})
    variants = request_variants(schemas, operation)
    key = lower_camel(action)

    header = []
    for path, kind in leaves.items():
        segments = path.split(".")
        if key not in segments[1:]:
            continue
        others = [segment for segment in segments[1:] if segment != key]
        item = {"path": f"capabilities.{path}"}
        if others and others[0] in variants:
            item["when"] = variants[others[0]]
        if kind == "always":
            item["always"] = True
        elif kind in ("support", "cursor"):
            item["support"] = True
        note = extra.get("notes", {}).get(path)
        if note:
            item["note"] = note
        header.append(item)
    for path, note in extra.get("header", []):
        if not any(path == leaf or leaf.startswith(path + ".") for leaf in leaves):
            raise ValueError(f"{action}: no header capability {path}")
        if note and not any(item["path"] == f"capabilities.{path}" for item in header):
            header.append({"path": f"capabilities.{path}", "note": note})

    market = []
    for path, note in extra.get("market", []):
        concrete = re.sub(r"\{(\w+)\}", lambda match: _first_enum_key(schemas, operation, match.group(1)), path)
        if concrete not in market_fields:
            raise ValueError(f"{action}: no {market_root} field {concrete}")
        market.append({"path": re.sub(r"\{(\w+)\}", r"<\1>", path), "note": note})

    if not header and not market:
        return {"source": source, "none": True}
    props = {"source": source, "header": header, "market": market}
    if extra.get("resolves"):
        props["perMarket"] = True
    return props


def _first_enum_key(schemas, operation, field):
    body = schemas.resolve(operation["requestBody"]["content"]["application/json"]["schema"])
    return lower_camel(schemas.resolve(body["properties"][field])["enum"][0])


def jsx_props(props):
    parts = []
    for key, value in props.items():
        if value is True:
            parts.append(key)
        elif isinstance(value, str):
            parts.append(f"{key}={json.dumps(value)}")
        else:
            parts.append(f"{key}={{{json.dumps(value)}}}")
    return " ".join(parts)


def capability_block(props):
    if props is None:
        return ""
    return (
        'import { CapabilityCheck } from "/snippets/capability-check.mdx";\n\n'
        f"<CapabilityCheck {jsx_props(props)} />\n"
    )


def badge_block(tags, kind, operation):
    """The operation's kind, then its badge tags, labelled and described as the spec defines them."""
    if kind not in KINDS:
        raise ValueError(f"Unknown operation kind {kind}")
    label, description = KINDS[kind]
    badges = [{"name": kind, "label": label, "description": description}] + [
        {"name": name, "label": tags[name]["summary"], "description": tags[name]["description"]}
        for name in operation["tags"] if tags[name].get("kind") == "badge"
    ]
    if not badges:
        return ""
    return (
        'import { OperationBadges } from "/snippets/operation-badges.mdx";\n\n'
        f"<OperationBadges badges={{{json.dumps(badges)}}} />\n"
    )


def sync():
    source = yaml.safe_load(SOURCE.read_text())
    schemas = Schemas(source)
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
            kind = path.split("/")[4]
            # A stream's response never finishes, so the playground could not show it.
            if kind == "stream":
                metadata["playground"] = "none"
            blocks = [
                block for block in (
                    badge_block(tags, kind, operation),
                    capability_block(capability_check(schemas, module, action, operation)),
                ) if block
            ]
            pages.append((ROOT / f"{page}.mdx", frontmatter(metadata) + "".join("\n" + block for block in blocks)))

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
    print(f"Synced {len(pages)} operation pages and API navigation from {SOURCE.relative_to(ROOT)}")


if __name__ == "__main__":
    sync()
