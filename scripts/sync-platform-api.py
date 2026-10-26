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

# Header and market summary schemas per capability source.
SOURCES = {
    "hosts": ("host", "ExecutionHostCapabilities", "HostMarketSummary"),
    "venues": ("venue", "VenueCapabilities", "VenueMarketSummary"),
}

# Discovery operations are where capabilities are read, so they get no check.
DISCOVERY = {"List", "ListMarkets"}

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
    variants = request_variants(schemas, operation) if operation else {}
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
    if operation is None:
        props["stream"] = True
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


# Streams

PAYLOAD_HEADING = "Event data"
PAYLOAD_ANCHOR = "event-data"


def comparable(schema):
    """A schema without its prose and discriminator, which may differ between the OpenAPI and AsyncAPI files."""
    if isinstance(schema, dict):
        return {key: comparable(value) for key, value in schema.items() if key not in {"description", "discriminator"}}
    if isinstance(schema, list):
        return [comparable(value) for value in schema]
    return schema


def check_shared(source_schemas, stream_schemas, name):
    """The embedded payload is rendered from the OpenAPI spec, so it and everything it reaches must match there."""
    pending = [name]
    while pending:
        current = pending.pop()
        if current not in source_schemas.schemas:
            raise ValueError(f"Stream schema {current} is missing from {SOURCE.name}")
        if comparable(source_schemas.schemas[current]) != comparable(stream_schemas.schemas[current]):
            raise ValueError(f"Schema {current} differs between {SOURCE.name} and {STREAMS.name}")
        pending += re.findall(r"#/components/schemas/(\w+)", json.dumps(stream_schemas.schemas[current]))


def mdx_text(text):
    text = " ".join(str(text).split())
    return (
        text.replace("{", "\\{").replace("}", "\\}").replace("<", "&lt;").replace(">", "&gt;")
    )


def type_label(schemas, schema):
    inner = schemas.nullable_inner(schema)
    if inner is not None:
        return f"{type_label(schemas, inner)} | null"
    resolved = schemas.resolve(schema)
    if resolved.get("oneOf"):
        return "object"
    kind = resolved.get("type", "object")
    if isinstance(kind, list):
        return " | ".join(kind)
    if kind == "array":
        return f"{type_label(schemas, resolved['items'])}[]"
    if resolved.get("format"):
        return f"{kind}<{resolved['format']}>"
    return kind


def field_description(schemas, schema):
    inner = schemas.nullable_inner(schema) or schema
    text = schema.get("description") or inner.get("description") or schemas.resolve(inner).get("description", "")
    resolved = schemas.resolve(inner)
    enum = resolved.get("enum")
    if enum and len(enum) == 1 and f"Always {enum[0]}" not in text:
        text = f"{text} Always `{enum[0]}`.".strip()
    elif enum and len(enum) > 1:
        text = f"{text} One of: {', '.join(f'`{value}`' for value in enum)}.".strip()
    return text


def render_fields(schemas, schema, indent, depth, linked):
    """ResponseFields for the properties of an object schema."""
    resolved = schemas.resolve(schema)
    required = set(resolved.get("required", []))
    return "".join(
        render_field(schemas, name, child, name in required, indent, depth, linked)
        for name, child in resolved.get("properties", {}).items()
    )


def render_field(schemas, name, schema, required, indent, depth, linked):
    pad = " " * indent
    attributes = f'name="{name}" type="{type_label(schemas, schema)}"' + (" required" if required else "")
    body = mdx_text(field_description(schemas, schema))
    target = linked_schema(schemas, schema, linked)
    if target:
        body += f" Its fields are under [{PAYLOAD_HEADING}](#{PAYLOAD_ANCHOR}) below."
    children = render_children(schemas, schema, indent + 2, depth + 1, linked)
    return f"{pad}<ResponseField {attributes}>\n{pad}  {body}\n{children}{pad}</ResponseField>\n"


def render_children(schemas, schema, indent, depth, linked):
    if depth > 8:
        return ""
    pad = " " * indent
    inner = schemas.nullable_inner(schema) or schema
    resolved = schemas.resolve(inner)
    if resolved.get("type") == "array":
        return render_children(schemas, resolved["items"], indent, depth, linked)
    if linked_schema(schemas, schema, linked):
        return ""
    if resolved.get("oneOf"):
        raise ValueError(f"Stream message field holds an unnamed union: {schema}")
    if resolved.get("type") == "object" and resolved.get("properties"):
        fields = render_fields(schemas, inner, indent + 2, depth, linked)
        return f'{pad}<Expandable title="properties">\n{fields}{pad}</Expandable>\n'
    return ""


def has_union(schemas, schema, seen=frozenset()):
    """Whether a union appears anywhere below this schema."""
    name = schemas.name(schema)
    if name in seen:
        return False
    seen = seen | {name} if name else seen
    resolved = schemas.resolve(schema)
    if resolved.get("oneOf"):
        return True
    children = [*resolved.get("anyOf", []), *resolved.get("properties", {}).values()]
    if "items" in resolved:
        children.append(resolved["items"])
    return any(has_union(schemas, child, seen) for child in children if child.get("type") != "null")


def linked_schema(schemas, schema, linked):
    """The named schema a field points to instead of expanding inline, recorded in `linked`, or None.

    A schema with a union anywhere below it is the stream's payload. Mintlify renders it at the end of the page from
    the OpenAPI spec (`openapi-schema`), because its union tabs read better than nested expandables.
    """
    inner = schemas.nullable_inner(schema) or schema
    resolved = schemas.resolve(inner)
    if resolved.get("type") == "array":
        return linked_schema(schemas, resolved["items"], linked)
    name = schemas.name(inner)
    if name is None or not has_union(schemas, inner):
        return None
    linked.add(name)
    return name


def render_message(schemas, message, linked):
    lines = [f"### {message.get('title', message['name'])}", ""]
    description = message.get("description") or message.get("summary", "")
    if description:
        lines += [mdx_text(description), ""]
    lines.append(render_fields(schemas, message["payload"], 0, 0, linked))
    for example in message.get("examples", [])[:1]:
        lines += ["```json Example", json.dumps(example["payload"], indent=2), "```", ""]
    return "\n".join(lines)


def stream_page(streams, key, channel, server_operation, control_operation, capability):
    """The page body and the payload schema Mintlify renders after it."""
    schemas = Schemas(streams)
    linked = set()
    messages = streams["components"]["messages"]

    def operation_messages(operation):
        return [messages[ref["$ref"].rsplit("/", 1)[1]] for ref in operation["messages"]]

    server = next(iter(streams["servers"].values()))
    url = f"{server['protocol']}://{server['host']}{channel['address']}"
    security = next(iter(streams["components"]["securitySchemes"].values()))
    sections = [
        capability,
        "## Connect",
        "",
        f"```text\n{url}\n```",
        "",
        f"{mdx_text(security.get('description', ''))} Send them on the WebSocket upgrade request, then subscribe "
        "accounts with the messages below. See [Stream account updates](/guides/streams) for the protocol, limits, "
        "close codes and how to reconcile.",
        "",
        "## Messages you send",
        "",
        mdx_text(control_operation.get("description", "")),
        "",
        *[render_message(schemas, message, linked) for message in operation_messages(control_operation)],
        "## Messages you receive",
        "",
        *[render_message(schemas, message, linked) for message in operation_messages(server_operation)],
    ]
    if len(linked) != 1:
        raise ValueError(f"Stream {key} must carry exactly one payload schema, found {sorted(linked)}")
    (payload,) = linked
    sections += [
        f"## {PAYLOAD_HEADING}",
        "",
        "The `data` object each event carries.",
        "",
    ]
    return "\n".join(section for section in sections if section is not None), payload


def sync():
    source = yaml.safe_load(SOURCE.read_text())
    streams = yaml.safe_load(STREAMS.read_text())
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
            block = capability_block(capability_check(schemas, module, action, operation))
            pages.append((ROOT / f"{page}.mdx", frontmatter(metadata) + ("\n" + block if block else "")))

    # One MDX page per channel, rendered from the AsyncAPI document: Mintlify's AsyncAPI view does not show nested
    # unions or nullable references. Frames are expanded inline; Mintlify renders the event payload after them from the
    # OpenAPI spec. The page takes its title and description from the operation the server sends.
    # AsyncAPI operations carry the domain tag, then the OpenAPI nav leaf, so each stream sits beside its REST
    # operations.
    stream_schemas = Schemas(streams)
    for key, channel in streams["channels"].items():
        operations = [
            operation for operation in streams["operations"].values()
            if operation["channel"]["$ref"] == f"#/channels/{key}"
        ]
        server_operations = [operation for operation in operations if operation["action"] == "send"]
        control_operations = [operation for operation in operations if operation["action"] == "receive"]
        if len(server_operations) != 1 or len(control_operations) != 1:
            raise ValueError(f"Expected one server and one control operation for stream {key}")
        operation = server_operations[0]
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
        }
        capability = capability_block(capability_check(schemas, module, action, None))
        body, payload = stream_page(streams, key, channel, operation, control_operations[0], capability)
        check_shared(schemas, stream_schemas, payload)
        metadata["openapi-schema"] = f"/{SOURCE.relative_to(ROOT)} {payload}"
        pages.append((ROOT / f"{page}.mdx", frontmatter(metadata) + "\n" + body))

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
    print(f"Synced {len(pages)} operation and stream pages and API navigation from {SOURCE.relative_to(ROOT)} and {STREAMS.relative_to(ROOT)}")


if __name__ == "__main__":
    sync()
