# Spec feedback for plurex (`platform-public-api/`)

**Status (2026-10-26): pending.** Nothing here is in plurex yet: checked against the locked commit `ddf3a5e` and
`origin/main`, which is the same commit. Earlier feedback, `asyncapi_spec_guidelines_for_plurex.md`, was adopted in
`7e4a8d407` (see `refresh-log/2026-10-26-66422bd-ddf3a5e.md`).

Four parts, none of which change the JSON on the wire except part D:

- **A. Unions:** title every union variant and flag nullable unions, in both files, REST and streams alike.
- **B. Stream payloads:** small additions that make stream payloads easier to read.
- **C. Response examples:** the OpenAPI file has no examples, so every error example in the docs shows the wrong code.
- **D. The `error` field:** always `null`; settle it before launch.

# A. Unions

These apply to every union in both spec files: request bodies, responses, nested fields and stream frames. They are
not specific to streams.

1. **Give every union variant a `title`, set to its `type` value.** Without one, Mintlify labels the tabs "Option 1",
   "Option 2", ... in the order of the `oneOf` list, on every REST and stream page. With `title: Perp` on
   `InstrumentPerp`, the tab reads "Perp". This was verified in `mint dev` on 2026-10-26.
   - Scope: every `oneOf` in both files. None of the variants have titles today.
     - OpenAPI (31): `Instrument`, `Order`, `OrderNew`, `OrderChange`, `MarketSizing`, `GetOrder`, `GetOrders`,
       `ListOpenOrders`, `ListClosedOrders`, `ListFills`, `ListCandles`, `CancelOrder`, `CancelOrders`,
       `CancelAllOrders`, `CancelResult`, `AccountMarketState`, `MarketLeverageSetting`, `MarketSettingEffectScope`,
       `TriggerReferencePricePolicy`, `StatisticsWindow`, `OperationSupport`, `CursorQueryCapability`,
       `ExecutionAccountCredentialNew`, `PriceResult`, `BestQuoteResult`, `MarketStatisticsResult`,
       `IndicativeFundingResult`, `OpenInterestResult`, `AccountStreamControl`, `AccountOrderStreamMessage`,
       `AccountTransactionStreamMessage`.
     - AsyncAPI (4): `Instrument`, `Order`, `OrderChange`, `MarketSizing`.
     - Any new union gets titles too.
   - Where a variant schema is shared by both files, give it the same title in both.
   - Ideally `check_contract.py` fails on an untitled `oneOf` variant.
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

2. **Say "null" in the description of every nullable union field.** Mintlify's OpenAPI view shows
   `anyOf: [{$ref: <a union>}, {type: 'null'}]` as plain `object`, not `object | null` (nullable plain objects and
   scalars are labelled correctly). The description is the only place a reader learns the field can be null. Existing
   fields already do this ("Related instrument, or null when unknown or not applicable."); keep it a rule everywhere.

# B. Stream payloads

Each stream page in the docs now ends with its event payload, which Mintlify renders from the OpenAPI file.
Mintlify's OpenAPI renderer handles unions well, so these are small additions.

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

1. **Give every schema a `description`, starting with one plain sentence that says what it is.** Mintlify shows a
   schema's description at the top of its rendering, and on every field that references it. These have
   none today: `AccountOrderEvent`, `Order`, `OrderChange`, `OrderChangeCancelled`, `OrderChangeCreated`,
   `OrderChangeRejected`, `Fill`, `AssetValue`, `MarketSizing`, `MarketSizingNotional`, `MarketSizingSize`, `Trigger`,
   `TriggerCondition`, `TriggerReferencePrice`, every `Instrument*` variant, and the enums `OptionRight`, `TradeRole`,
   `OrderSide`, `OrderState` and `AccountTransactionType`. `AccountOrderEvent` and `Order` matter most: the orders stream's
   "Event data" section opens with no explanation.

2. **A stream payload is always a `$ref` to a named schema that is also in the OpenAPI file, with the same shape.**
   Keep it to one payload schema per stream; the other frame fields stay plain (no unions).
   Don't define a union inline in a frame; the docs sync rejects it. In practice: when a stream sends what a REST
   operation returns, reference that same component (as `AccountTransaction` already does). When a stream sends
   something new, add it to the OpenAPI file's `components.schemas` too, even if no REST operation returns it, as
   `AccountOrderEvent` already is.

3. **Keep shared schemas identical in both files**, descriptions included. The "Event data" section shows the OpenAPI
   text, while the frames above it show the AsyncAPI text. The descriptions match today. Ideally
   `check_contract.py` would enforce it, comparing every schema name that appears in both files (OpenAPI may keep its
   `discriminator` object).

## Not needed

- No change to message structure or channel layout beyond `asyncapi_spec_guidelines_for_plurex.md`.
- No `discriminator` in the AsyncAPI file. The docs don't use it.

# C. Response examples

## The problem

The OpenAPI file has no `example` or `examples` anywhere. Mintlify then builds every example from the schema, taking the
first value of each enum and the first variant of each union.

For errors, every response component references `ErrorEnvelope`, and the first `ErrorCode` value is `InvalidRequest`. So
on every endpoint page the 401, 403, 404, 409, 415, 422, 429 and 5xx examples all show `"code": "InvalidRequest"`. That
is wrong for every status but 400. The right codes are only in the response descriptions ("404 NotFound; code is
AccountNotFound, OrderNotFound or NotFound").

Success examples have the same weakness: placeholder strings, decimals as `"<string>"`, and only the first variant of
each union (every order example is a `Limit`, every instrument a `Spot`).

The single envelope for every status is right and should stay. This is only about examples. The AsyncAPI file already
has a valid example on every message, enforced by `check_contract.py`; the OpenAPI file has no equivalent rule.

## Additions

1. **Named error examples on every shared response component**, one per code the status can carry, keyed by the code.
   Every operation references these components, so this fixes every endpoint page at once. About 22 examples:

   | Component | Examples |
   | --- | --- |
   | `BadRequest` (400) | `InvalidRequest` |
   | `Unauthenticated` (401) | `Unauthenticated` |
   | `Forbidden` (403) | `Forbidden` |
   | `NotFound` (404) | `AccountNotFound`, `OrderNotFound`, `NotFound` |
   | `Conflict` (409) | `DuplicateClientOrderId`, `OrderAlreadyClosed`, `Conflict` |
   | `UnsupportedMediaType` (415) | `UnsupportedMediaType` |
   | `Rejected` (422) | `InsufficientFunds`, `InvalidProviderCredentials`, `AccountLimit`, `NotSupported`, `Rejected` |
   | `RateLimited` (429) | `RateLimited` |
   | `UnexpectedError` (500) | `UnexpectedError` |
   | `UpstreamFailure` (502) | `UpstreamFailure`, `CancelAllFailed` |
   | `Unavailable` (503) | `Unavailable` |
   | `UpstreamTimeout` (504) | `UpstreamTimeout` |

   For 5xx, `toPublicError()` sends the status text as `message` ("Internal Server Error", "Bad Gateway", "Service
   Unavailable", "Gateway Timeout"), so the examples can use it exactly. For 4xx the message is the failure's own text;
   use a realistic message from the code path that raises it. The 4xx messages below are placeholders. If part D
   removes `error`, drop it from the examples.

   ```yaml
   NotFound:
     description: 404 NotFound; code is AccountNotFound, OrderNotFound or NotFound.
     content:
       application/json:
         schema:
           $ref: '#/components/schemas/ErrorEnvelope'
         examples:
           AccountNotFound:
             summary: The accountId does not exist
             value: {code: AccountNotFound, message: Account not found, error: null}
           OrderNotFound:
             summary: The account exists, but the order identifier does not
             value: {code: OrderNotFound, message: Order not found, error: null}
           NotFound:
             summary: Unknown path, host or venue
             value: {code: NotFound, message: Not Found, error: null}
   UpstreamFailure:
     description: 502 UpstreamFailure; code is UpstreamFailure or CancelAllFailed.
     content:
       application/json:
         schema:
           $ref: '#/components/schemas/ErrorEnvelope'
         examples:
           UpstreamFailure:
             summary: The host or venue failed or returned something unreadable
             value: {code: UpstreamFailure, message: Bad Gateway, error: null}
           CancelAllFailed:
             summary: The host failed to cancel all orders
             value: {code: CancelAllFailed, message: Bad Gateway, error: null}
   ```

   The docs side should check in `mint dev` that Mintlify shows the named examples as a choice per status.

2. **Realistic success examples for the operations readers start from**, written as `examples` on the 200 response
   (and on the request body where the request is a union). Priority:
   - SubmitOrder: one request per order type (`Limit`, `Market` by `Size` and by `Notional`, `TriggerLimit`,
     `TriggerMarket`), each with its returned order.
   - GetOrder, ListOpenOrders, ListFills: an order part-filled and one with `averagePrice: null`.
   - Host List and ListMarkets: a header with real capability values, and a perpetual and a spot market summary.
   - Venue List and ListMarkets, GetPrices (with one `Unavailable` result), ListCandles.
   - ListWallets, ListPositions, GetMarketState (`Derivative` and `Spot`).

   Values are illustrative: decimals as strings, IDs as in the docs (`bybit`, `acc_123`).

3. **Have `check_contract.py` validate every OpenAPI example against its schema**, closed-world, as it does for
   AsyncAPI messages and captured traffic. Also require at least the error examples in part C.1, so a new code without
   an example fails the check.

Not asked for: narrowing each operation's responses to the codes it can actually return. That needs a response
component per operation, and the operation descriptions already name the codes that apply.

# D. The `error` field

`ErrorEnvelope.error` is described as "Reserved for structured detail; currently always null". Both places the server
builds an envelope (`platform-server/.../api/pub/PublicErrors.kt`) hard-code `error = null`, and the docs' Errors page
says "Always `null`."

Settle it before launch, because afterwards it is fixed: removing a field is breaking under the spec's own evolution
rules. As it stands it does no work:

- Every client decodes a field that never carries anything, and every reader wonders what it is for.
- It is typed `string | null`, so it could not carry structured detail without changing type, which is also breaking.
  "Reserved" reserves nothing useful.

Options:

1. **Remove it (recommended).** The envelope becomes `{code, message}`. If structured detail is needed later, add a new
   optional field with an object schema; that is additive.
2. **Give it a purpose now.** Make it a nullable object with a defined shape (for example the offending field and
   reason for `InvalidRequest`) and populate it.

When it changes, the docs update `api-reference/platform/errors` (the envelope example and field table).
