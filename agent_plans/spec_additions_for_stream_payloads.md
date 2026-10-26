# Spec additions for stream payloads (`platform-public-api/`)

**Goal.** Each stream page in the docs now ends with its event payload, which Mintlify renders from the OpenAPI file.
Mintlify's OpenAPI renderer handles unions well, so these are small additions that make those payloads, and the REST
pages, easier to read. The JSON on the wire doesn't change.

This adds to `asyncapi_spec_guidelines_for_plurex.md`, and replaces its rule 10 ("nested unions inside fields ...
untested"): nested unions are fine, as long as the rules below hold.

## How the docs use the specs now

- Stream pages are generated from the AsyncAPI file. Envelope frames (`Subscribe`, `Subscribed`, `Rejected`, `Event`,
  `Ended`, ...) are expanded inline.
- The frame field whose schema contains a union somewhere below it (today, `Event.data`) points to an "Event data"
  section at the end of the page. That section is the schema **with the same name from the OpenAPI file**, rendered by
  Mintlify: `AccountTransaction` and `AccountOrderEvent` today.
- A page can embed only one schema, so each stream must have exactly one such payload. The docs sync fails if it finds
  more than one, if the schema is missing from the OpenAPI file, or if any schema it reaches differs in shape between
  the two files. Shape here ignores `description` and `discriminator`.

## Additions

1. **Give every union variant a `title`, set to its `type` value.** Without one, Mintlify labels the tabs "Option 1",
   "Option 2", ... in the order of the `oneOf` list. With `title: Perp` on `InstrumentPerp`, the tab reads "Perp". This
   was verified in `mint dev` on 2026-10-26. It applies to all 31 `oneOf` schemas in the OpenAPI file, none of which
   have titled variants today. Those include `Instrument`, `Order`, `OrderNew`, `OrderChange`, `MarketSizing`, the
   request unions (`GetOrder`, `ListCandles`, `CancelOrder`, ...) and the result unions (`PriceResult`, ...).
   The REST pages benefit too: Submit an order and Get an order show the same tabs. Put the same titles in the AsyncAPI
   copies so the two files stay alike.
   - Check the generated SDKs afterwards. Some generators use `title` when they name a type.

   ```yaml
   InstrumentPerp:
     title: Perp
     type: object
     required: [type, base, quote]
     properties:
       type: {type: string, enum: [Perp]}
       ...
   ```

2. **Give every schema a `description`, starting with one plain sentence that says what it is.** Mintlify shows a
   schema's description at the top of its rendering, and on every field that references it. These have
   none today: `AccountOrderEvent`, `Order`, `OrderChange`, `OrderChangeCancelled`, `OrderChangeCreated`,
   `OrderChangeRejected`, `Fill`, `AssetValue`, `MarketSizing`, `MarketSizingNotional`, `MarketSizingSize`, `Trigger`,
   `TriggerCondition`, `TriggerReferencePrice`, every `Instrument*` variant, and the enums `OptionRight`, `TradeRole`,
   `OrderSide`, `OrderState` and `AccountTransactionType`. `AccountOrderEvent` and `Order` matter most: the orders stream's
   "Event data" section opens with no explanation.

3. **A stream payload is always a `$ref` to a named schema that is also in the OpenAPI file, with the same shape.**
   Keep it to one payload schema per stream; the other frame fields stay plain (no unions).
   Don't define a union inline in a frame; the docs sync rejects it. In practice: when a stream sends what a REST
   operation returns, reference that same component (as `AccountTransaction` already does). When a stream sends
   something new, add it to the OpenAPI file's `components.schemas` too, even if no REST operation returns it, as
   `AccountOrderEvent` already is.

4. **Keep shared schemas identical in both files**, descriptions included. The "Event data" section shows the OpenAPI
   text, while the frames above it show the AsyncAPI text. The descriptions match today. Ideally
   `check_contract.py` would enforce it, comparing every schema name that appears in both files (OpenAPI may keep its
   `discriminator` object).

5. **Say "null" in the description of a nullable union field.** Mintlify's OpenAPI view shows
   `anyOf: [{$ref: <a union>}, {type: 'null'}]` as plain `object`, not `object | null` (nullable plain objects and
   scalars are labelled correctly). The description is the only place a reader learns the field can be null. Existing
   fields already do this ("Related instrument, or null when unknown or not applicable."); keep it a rule.

## Not needed

- No change to message structure or channel layout beyond `asyncapi_spec_guidelines_for_plurex.md`.
- No `discriminator` in the AsyncAPI file. The docs don't use it.
