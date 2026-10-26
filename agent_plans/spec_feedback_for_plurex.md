# Spec feedback for plurex (`platform-public-api/`)

**Status (2026-10-26): adopted** in plurex `db1121cdf` (merged as `02f04962b`), checked in the docs refresh
`refresh-log/2026-10-26-ddf3a5e-02f0496.md`. Every part landed: titled union variants and a description on every
schema in both files; stream payloads as one `$ref` (`Event.data`); named error examples per code and success
examples for every operation in C.2, validated by `check_contract.py`; `ErrorEnvelope.error` removed; and operation
descriptions without badge phrases, enforced by the checker. Kept as the record of what was asked. Earlier feedback,
`asyncapi_spec_guidelines_for_plurex.md`, was adopted in `7e4a8d407`. Paper engine findings are separate:
`paper_trading_gap_findings.md`.

Five parts, none of which change the JSON on the wire except part D:

- **A. Unions:** title every union variant and flag nullable unions, in both files, REST and streams alike.
- **B. Stream payloads:** small additions that make stream payloads easier to read.
- **C. Response examples:** the OpenAPI file has no examples, so every error example in the docs shows the wrong code.
- **D. The `error` field:** always `null`; settle it before launch.
- **E. Operation descriptions:** cut them to what the operation is, does and returns; leave the rest to badges.

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

# E. Operation descriptions

## The problem

Operation descriptions repeat what the badges already say, explain how Plurex serves data, and bury what the operation
does. Get indicative fundings, for example (408 characters):

> The current indicative funding rate for each perpetual: an estimate, so the rate that settles can differ. One result
> per requested instrument, in request order. An instrument without a value comes back as an Unavailable result with its
> error code, so one instrument cannot fail the batch. Served from Plurex's live feed for the market when one is
> running, otherwise fetched from the venue. No API key needed.

Only the first sentence is about this operation. The rest is the Batch badge, the batch rules in the docs' conventions
page, the No API key badge, and how Plurex sources the data, which readers don't need.

The docs now render the badge tags (`kind: badge`) on every operation page, with the tag's `summary` as the label and
its `description` on hover. So the badges no longer need repeating in prose.

## Rules

1. **Say what the operation is, does and returns**, in the first sentence. Add only what is specific to this
   operation and changes how a caller uses it: an ordering, a limit, an error code with an operation-specific meaning,
   how to recover when the outcome is unclear.
2. **Don't restate a badge.** No "No API key needed" (No API key), no "one result per instrument, in request order ...
   one instrument cannot fail the batch" (Batch), no "follow nextCursor" (Paged), no "hosts without X return
   422 NotSupported" (Check capabilities), no "Not safe to repeat: ..." (Not safe to repeat). Keep the recovery step,
   which is specific ("If the outcome is unclear, check ListTransactions before retrying").
3. **Don't say "Safe to repeat."** Extend the Not safe to repeat badge description instead: "Commands without this
   badge are safe to repeat." (The docs overview already says so.) Every command without the badge is safe to repeat
   today.
4. **Don't describe how Plurex works inside**: no "served from Plurex's live feed when one is running, otherwise
   fetched from the venue", no caches or feeds. Field descriptions may still say when a field is `null` or what time it
   carries.
5. **Don't repeat what the schemas, responses or capability fields already say**, such as which 404 codes exist, or which
   variants a capability gates.
6. **No "yet".** "Option markets are not listed yet" becomes "Option markets are not listed."
7. Aim for one or two sentences. Ideally `check_contract.py` rejects descriptions that contain badge phrases.

The same rules apply to the AsyncAPI operations and messages.

## Proposed descriptions

| Operation | Description |
| --- | --- |
| List venues | Lists every venue with the market data it supports. |
| List venue markets | Lists a venue's markets with the market data each one supports, optionally filtered. Option markets are not listed. |
| Get order book | The current order book of one market, at the depth the venue provides. An unknown market returns 422 NotSupported. |
| Get recent trades | The venue's recent public trades for one market, oldest first. The venue limits how many; this is not a complete history. An unknown market returns 422 NotSupported. |
| Get prices | The current price of one kind (traded, mark or index) for each instrument. |
| Get best quotes | The best bid and ask for each instrument. |
| Get market statistics | Venue-reported statistics for each instrument, over the window its market declares. |
| Get indicative fundings | The current indicative funding rate for each perpetual. It is an estimate: the rate that settles can differ. |
| Get open interests | The current open interest for each derivative, in the unit its market declares. |
| List candles | Closed candles for one market, price kind and interval, newest first. The forming candle is never included, and a page has no gaps. ByInstrument starts from the latest closed candle, ByInstrumentBefore from the candles that end at or before `before`; paging past the first page needs the market's listBefore. A price kind or interval the market does not list returns 422 NotSupported. |
| List hosts | Lists every host, real and paper, with the operations it supports. |
| List host markets | Lists a host's markets with each market's order types, order rules and settings, optionally filtered. Option markets are not listed. |
| Get an order | Gets one order by ID or clientOrderId. |
| Get orders | Gets the orders you name. Unknown identifiers are left out. |
| List open orders | (unchanged) |
| List closed orders | Lists filled, cancelled and rejected orders, globally or for one instrument, optionally from a before or after time. |
| List fills | (unchanged) |
| List account transactions | Lists the account's balance postings: trading fees, funding payments, interest, deposits, withdrawals and more. They come in the order the host's listTransactions capability states, and posting IDs match the transaction stream. |
| List wallets, List open positions, List margin states, Get market account state, Get market leverage, Get market position mode | (unchanged) |
| Submit an order | Submits one order and returns it as the host accepted it. If the outcome is unclear (a timeout or 5xx), look the order up by clientOrderId before resubmitting. 409 DuplicateClientOrderId means an order with that clientOrderId already exists. |
| Cancel an order | Cancels one open order. Ack means the host accepted the cancel; some hosts cancel asynchronously, so confirm the final state with the order stream or GetOrder. 404 OrderNotFound means the host does not know the identifier as an open order: it never existed, it closed and was forgotten, or it is not visible yet, so check rather than assume it is gone. 409 OrderAlreadyClosed means the order already finished and may have filled; do not retry. |
| Cancel orders | Cancels the orders you name and returns one CancelResult per identifier, so a call can partly succeed. A Failed result carries the code CancelOrder would return for that identifier. An error that stops the whole call, such as a missing account, is returned as an ordinary error. |
| Cancel all orders | Cancels every open order on the account, or on one instrument. Success means none remain open; orders already closed count as cancelled. Any other failure returns 502 CancelAllFailed: check ListOpenOrders for what is still open. |
| Set market leverage | Sets the account's leverage for one market and returns the resulting setting. |
| Set market position mode | Sets the account's position mode for one market and returns the resulting mode. |
| Connect an exchange or broker account | Connects an exchange or broker account with its API credentials. If the outcome is unclear, check List accounts before retrying. |
| Update account credentials | Replaces the account's exchange or broker credentials. |
| Rename an account | Renames an account. |
| Delete an account | Deletes an account. Repeating after success returns 404 AccountNotFound. |
| List accounts | Lists your accounts, optionally filtered. |
| Get an account | Gets one account. |
| Create a paper account | Creates a paper account on a paper host. It trades the live market of the venue the paper host models, through the same host operations as a real account. If the outcome is unclear, check List accounts before retrying. |
| Deposit into a paper account | Credits the paper account and returns the resulting wallet. If the outcome is unclear, check ListTransactions before retrying. |
| Withdraw from a paper account | Debits the paper account's available balance and returns the resulting wallet, to set up scenarios such as a low balance. Funds held by open orders or position margin cannot be withdrawn; above the available balance, it fails with 422 InsufficientFunds and changes nothing. It posts a Withdrawal transaction. If the outcome is unclear, check ListTransactions before retrying. |
| Set paper fee tier | Selects the paper account's fee tier and returns the resulting fee settings. Existing orders keep their fee terms. |
| Get paper fee settings, Get effective paper fee rates | (unchanged) |

"Boundary" in the current List closed orders text is replaced by "time".
