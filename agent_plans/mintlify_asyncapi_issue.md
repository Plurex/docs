# AsyncAPI pages drop `oneOf` and nullable `anyOf` schemas

**Mintlify CLI:** 4.2.1125 (`mint dev`).
**Spec:** AsyncAPI 3.0.0.

## Summary

The AsyncAPI page renderer does not handle schema composition. On an AsyncAPI page:

1. A field whose schema is a `oneOf` has every variant's properties merged into one list. Nothing shows that they are
   alternatives, and the shared discriminator field (`type`) is listed once per variant.
2. A field whose schema is `anyOf: [{$ref: <a oneOf>}, {type: 'null'}]` shows as `type: anyOf` with nothing to expand.
3. A field whose schema is `anyOf: [{$ref: <an object>}, {type: 'null'}]` shows as `type: object`, so you can't tell it
   can be null.
4. A message whose `payload` is itself a `oneOf` shows its title and summary but no fields.

The OpenAPI renderer handles the same schemas well: a tab per variant (named from the variant's `title`), `string | null`
for nullable scalars, and expandable children. Messages on event streams are usually tagged unions, so on AsyncAPI pages
the payload a reader most needs to see is the part that's missing.

## Reproduction

Three files in an empty directory, then `mint dev`. `openapi.yaml` is the same schema served from a REST endpoint, for
comparison.

`docs.json`

```json
{
  "$schema": "https://mintlify.com/docs.json",
  "theme": "mint",
  "name": "repro",
  "colors": { "primary": "#000000" },
  "navigation": { "groups": [{ "group": "Repro", "pages": ["async", "openapi"] }] }
}
```

`async.mdx` and `openapi.mdx`

```mdx
---
title: "AsyncAPI"
asyncapi: "/async.yaml events"
---
```

```mdx
---
title: "OpenAPI"
openapi: "/openapi.yaml GET /event"
---
```

`async.yaml`

```yaml
asyncapi: 3.0.0
info: {title: Repro, version: 1.0.0}
servers:
  prod: {host: example.com, protocol: wss}
channels:
  events:
    address: /events
    messages:
      Event: {$ref: '#/components/messages/Event'}
      Frame: {$ref: '#/components/messages/Frame'}
operations:
  receiveEvents:
    action: send
    channel: {$ref: '#/channels/events'}
    summary: Events
    messages:
      - $ref: '#/channels/events/messages/Event'
      - $ref: '#/channels/events/messages/Frame'
components:
  messages:
    Event:
      title: Event
      summary: Plain object payload with a oneOf field and a nullable field.
      payload: {$ref: '#/components/schemas/Event'}
    Frame:
      title: Frame
      summary: Payload that is itself a oneOf.
      payload: {$ref: '#/components/schemas/Shape'}
  schemas:
    Circle:
      title: Circle
      type: object
      required: [type, radius]
      properties:
        type: {type: string, enum: [Circle], description: Variant tag.}
        radius: {type: number, description: Radius in metres.}
    Square:
      title: Square
      type: object
      required: [type, side]
      properties:
        type: {type: string, enum: [Square], description: Variant tag.}
        side: {type: number, description: Side length in metres.}
    Shape:
      description: A shape, told apart by `type`.
      oneOf:
        - $ref: '#/components/schemas/Circle'
        - $ref: '#/components/schemas/Square'
    Person:
      type: object
      required: [name]
      properties:
        name: {type: string, description: The person's name.}
    Event:
      type: object
      required: [topic, shape]
      properties:
        topic: {type: string, description: The topic this event belongs to.}
        shape:
          $ref: '#/components/schemas/Shape'
        owner:
          description: Who owns the shape, or null.
          anyOf:
            - $ref: '#/components/schemas/Person'
            - type: 'null'
        previous:
          description: The shape before this change, or null.
          anyOf:
            - $ref: '#/components/schemas/Shape'
            - type: 'null'
```

`openapi.yaml`: `openapi: 3.1.0`, one `GET /event` whose `200` response is `$ref: '#/components/schemas/Event'`, and the
same `components.schemas` block as above.

## Expected

On `/async`, as on `/openapi`:

- `shape`: `object`, with one tab per variant (`Circle`, `Square`), each tab showing that variant's fields.
- `owner`: `object | null`, expandable to `name`.
- `previous`: `object | null`, with the `Circle` and `Square` tabs.
- `Frame`: the `Circle` and `Square` tabs.

## Actual

On `/async` (screenshot attached: `mintlify_asyncapi_issue.png`, every section expanded):

| Field | Rendered as |
| --- | --- |
| `shape` | `type: object`, "4 properties": `type` (Circle), `radius`, `type` (Square), `side` in one flat list |
| `owner` | `type: object`, "1 property". No sign it can be null |
| `previous` | `type: anyOf`, no children |
| `Frame` message | Title and summary only; no fields |

On `/openapi` the same schemas render as expected: `shape` shows `Circle` and `Square` tabs and `owner` shows
`object | null`. (One small gap there too: `previous` shows as `object` rather than `object | null`, though its tabs
render.)

## Impact

We document multiplexed WebSocket streams. Each frame's payload is a plain object, but the event's `data` field holds
domain objects whose fields are unions (order types, instrument kinds, order changes), and some of those are nullable.
Readers can't see those shapes on the AsyncAPI pages, so we've stopped using the `asyncapi` frontmatter and now generate
plain MDX pages from the spec. That loses the WSS sidebar badge, the Connect panel and the Messages panel.

## Ask

Please make the AsyncAPI renderer use the OpenAPI renderer's handling of `oneOf`, `anyOf` and `type: 'null'` for
message payloads and their nested fields.
