# AsyncAPI spec guidelines (`plurex-platform-async-api.yaml`)

**Goal.** The public docs render the AsyncAPI spec in Mintlify, so the spec should let a reader see every message they
can send or receive on a stream, with its fields, without knowing how the schemas are built. These rules change only
how the spec declares messages. The JSON on the wire stays exactly the same.

Rules 1–3 were verified against a Mintlify render on 2026-10-26. The rest are general practice; those marked
*untested* should be checked in `mint dev` in the docs repo.

## Messages

1. **One message per wire shape.** Each kind of frame (`Subscribe`, `Unsubscribe`, `Subscribed`, `Unsubscribed`,
   `Rejected`, `Event`, `Ended`) is its own entry in `components.messages`. Don't wrap the variants in a single message
   whose payload is a `oneOf` union. Mintlify renders a union payload as an empty `{}`.
2. **Payload is a `$ref` to a plain `type: object` schema.** Keep using the existing concrete leaves
   (`AccountStreamSubscribe`, `AccountTransactionStreamEvent`, `AccountStreamEnded`, ...). The `oneOf` unions
   (`AccountStreamControl`, `Account...StreamMessage`) can stay in `components.schemas` for SDK generation, but no
   message payload should point at them.
3. **Operations list their messages.** On each channel:
   - The channel's `messages` map holds every message used on it.
   - The server operation (`action: send`, `{domain}{Action}`) lists everything the server sends: `Subscribed`,
     `Unsubscribed`, `Rejected`, the stream's `Event`, `Ended`.
   - The client operation (`action: receive`, `{domain}{Action}Control`) lists `Subscribe` and `Unsubscribe`.
   - The docs sync expects exactly one `send` operation per channel and takes the page title and description from it,
     so keep that shape.
4. **Name messages per stream where the payload differs.** Shared control and reply messages
   (`AccountStreamSubscribe`, `AccountStreamRejected`, ...) can be reused across the account streams. Event messages
   are per stream (`AccountOrderStreamEvent`, `AccountTransactionStreamEvent`).
5. **No `discriminator` at message level.** The `type` field already tells the frames apart. If you do add one,
   AsyncAPI 3.0 expects a plain property-name string, not OpenAPI's `{propertyName, mapping}` object. Mintlify
   rendering with a discriminator is *untested*.

## Text the reader sees

6. **Every message gets a `title`, a `summary` and a `description`** that say when it is sent and what follows it.
   For example: "Sent once per refused account, before the request's Subscribed; the connection stays open." This is
   the reader's main explanation of the protocol, so the ordering rules (reply order, nothing after `Ended` or
   `Unsubscribed`, order per topic) belong here, not only in `info.description`.
7. **Every field has a `description`**, including `id`, `topic`, `topics` and `code`, plus limits (`maxItems: 25`)
   stated in words as well as in the keyword.
8. **Add `examples` to each message** (a full JSON frame, valid against its schema). Rendering is *untested*. Even if
   Mintlify doesn't show them, the docs repo's guide examples can be checked against them.
9. **Keep protocol-wide rules in `info.description`:** connecting and authentication, the subscribe and reply
   sequence, idle and slow-consumer closes, reconciliation, compatibility. Keep it short and in the public vocabulary
   (accounts, topics, events). Don't use internal names such as multiplexer, outbox or resolver.
10. **Nested unions inside fields** (`instrument`, `change`, `sizing`) are expected. How well Mintlify expands them
    inside a message is *untested*, so check one `Event` page in `mint dev`.

## Checker (`check_contract.py`)

11. Enforce:
    - every message payload is a `$ref` to an object schema;
    - every member of a stream's server union has a message on the server operation, and every control variant has
      one on the Control operation, so the message lists and the unions can't drift apart;
    - captured traffic validates against one of its operation's messages.
12. Keep the existing rules: `{domain}{Action}` keys, `{domain}{Action}Control`, one type per socket, domain tag then
    OpenAPI nav leaf tag on each operation.

## Future streams (venue market data)

13. Follow the same pattern for every new stream: plain-object payloads, one message per frame type, the shared
    control and reply messages for that topic type, and a per-stream `Event`. A new topic type (for example an
    instrument topic) gets its own `...StreamTopic`, `...StreamSubscribe` and so on, written out as concrete leaves.
