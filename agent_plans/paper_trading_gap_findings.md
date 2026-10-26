# Paper trading: gap findings for plurex (`execution-host-paper`)

**From:** the docs review of the paper engine at `ddf3a5e`, 2026-10-26. Every finding was read in source; two were
re-checked by hand: findings 1 and 5. Paths are under
`execution-host-paper/src/main/kotlin/io/plurex/paper/` unless stated.

**The docs now assume these are fixed.** The public paper pages describe the engine as it should behave once these
findings are resolved. The last section lists the doc statements that depend on each fix. Until then, those statements
are ahead of the code.

Leverage, and the margin features that come with it (maintenance margin, liquidation), are a known gap and stay out of
scope. The docs say paper trades perpetuals at 1× with no leverage control.

## Realism bugs

### 1. A crossing GTC limit order takes the same liquidity twice

A marketable GTC limit order larger than the visible depth fills that depth as taker and rests the remainder. On the
next matching tick, `fillFromBook` (`core/matching/aggregate/PaperMatchingAggregateDecider.kt:199`) rebuilds the
opposite levels from the book snapshot. The levels the order just took are still there, at or through its price, so
the remainder fills again against them, as maker, at the limit price and the maker rate.

- **Effect:** large crossing limit orders fill more, and more cheaply, than they would live.
- **Fix:** remember liquidity this order has already taken until the venue's book changes at those levels, or don't
  book-fill a remainder from levels at or better than its own taker sweep.

### 2. Linear average entry price is rounded to 2 decimals

`perpetualAverageEntryPrice` (`core/contracts/PerpetualContractMath.kt`, `roundScale = 2`, HALF_UP) runs every time a
linear position is increased, in `DerivativeNettingEvolver` and `DerivativeHedgingEvolver`.

- **Effect:** entry price and realised PnL are wrong on low-priced contracts, for example anything under $1.
- **Fix:** keep full precision, or round to the market's price increment at most.

### 3. Fees are not reserved, and spot market buys reserve at the best ask

`ExposureStateSpotDecider.handleRegister` and `computeRegistrationInfo` reserve price × size only. A spot market buy
reserves best ask × size. Perp opening orders reserve the settlement value of the opening part, without fees.

- **Effect:** a buy that uses the whole quote balance is accepted, then leaves the wallet negative by the fee. A
  market buy that sweeps beyond the best ask also overdraws.
- **Design doc conflict:** `design/PaperExchangeExecutionFlow.md` (around line 43) says the reservation covers
  "Principal + Fees".
- **Fix:** reserve the fee at the order's taker rate, and reserve a market buy at the price of walking the book for
  its size.

### 4. Trigger orders don't re-check funds or collateral when they fire

AGENTS.md says trigger orders "reassemble a fresh price/account context and reacquire their claim before submission".
In code, `RefreshClaim` is never sent, and `HandleTriggerFired` (`core/order/aggregate/PaperOrderAggregateDecider.kt`)
goes straight to matching with the claim taken at placement. That claim was sized at the trigger or limit price.

- **Effect:** a trigger market order that fills worse than its trigger price overdraws instead of being checked.
- **Fix:** implement the refresh AGENTS.md describes.

### 5. A full-size stop-loss and take-profit can't coexist on a netting market

A waiting reduce-only trigger takes close capacity when it is placed
(`ExposureStateDerivativeNettingDecider.validateReduceOnlyRegistration`). So the second of two full-size reduce-only
triggers, for example a stop-loss and a take-profit, is rejected with `REDUCE_ONLY_PENDING_EXHAUSTION`.

- **Effect:** the most common protective pattern on a live venue can't be placed on paper.
- **Fix:** let waiting reduce-only triggers share close capacity, and check it when one fires.

### 6. The funding schedule is not refreshed

`FundingScheduleTick.initializeSchedules` reads a market's schedule once and doesn't refresh it while positions stay
open. This is inferred from the code, not tested.

- **Effect:** if the venue changes the interval mid-position, timers keep firing at the old times. Those resolve as
  `InvalidBoundary`, and the new funding times are missed until the position next changes or the host restarts.
- **Fix:** re-infer the schedule periodically, or after an `InvalidBoundary`.

### 7. No funding while the venue's funding history is irregular

`core/funding/FundingScheduleInference.kt` needs four evenly spaced finalised funding times. Bybit and VALR set no
configured fallback schedule.

- **Effect:** just after a venue changes a market's interval, paper pays no funding until four regular records exist.
- **Fix:** infer from the most recent regular run, or add per-provider fallback schedules.

### 8. Paper markets are a snapshot taken at warm-up

`marketSource.install` in `PaperHost.runLifecycle` runs once.

- **Effect:** new model-host listings and changed order rules appear only after a paper host restart, and markets the
  venue no longer lists stay listed.
- **Fix:** refresh markets on the same schedule as the model host's.

## Provider gaps

### 9. No transaction stream on bybit-paper

`AccountTransactionsCapabilities.toPaperCapabilities` (`PaperHostCapabilities.kt:255`) copies the model host's support,
and Bybit declares `subscribeToAccountTransactions = NotSupported`
(`execution-providers/.../bybit/host/account/BybitAccountTransactions.kt`). The paper engine implements the stream
anyway.

- **Contract conflict:** this contradicts the module's AGENTS.md "Phase 0" contract, which says paper declares support
  for engine queries **and streams** whatever the target host supports.
- **Fix:** declare transaction history and the stream `Supported` on every paper host.

### 10. Set position mode only where the model market offers both modes

This is correct as a model of the host, so it is not a bug. However, `buildPaperHost` calls `toPaperCapabilities()`
without the market list, so the header's `setMarketPositionMode` is always `PerMarket`. It should be `NotSupported`
when no market can switch.

## Smaller issues

11. **`fractionDigits` on fee tiers.** Get fee settings always returns `fractionDigits: null` on tier rates, because
    catalogue rates are never resolved, yet paper always rounds fees. The spec text "null when fees are not rounded" is
    misleading. Say instead that `null` means the precision depends on the instrument's fee asset, and that Get
    effective fee rates reports it.
12. **`Order.triggerPrice` after firing** reports the observed firing value, not the configured trigger price
    (`adapters/orders/PaperOrders.kt` `toOrder`). Keep the configured price; the firing value belongs on the fill, if
    anywhere.
13. **The clientOrderId duplicate check is not atomic** under concurrent submits (`requireClientOrderIdFree`). Two
    simultaneous submits with the same ID can both pass.
14. **Bybit fee tier unverified.** `providers/bybit/BybitPaperFeeProfile.kt` says its rates could not be checked against
    Bybit's page. Verify them, and add Bybit's published tiers beyond "Standard", as VALR has.
15. **Stale design doc.** `design/PaperExchangeExecutionFlow.md` still describes `ReserveBalance` /
    `ConfirmFundsReserved` and a price-time-priority engine. The code uses collateral claims and matches each account
    against the real book.

## Realism improvements

### 16. Report a sweep as one fill per price level

A marketable order that takes several levels is reported as one TAKER fill at the volume-weighted average price
(`acceptMarketOrder` / `acceptLimitOrder` in `core/matching/aggregate/PaperMatchingAggregateDecider.kt`). Live venues
report one execution per level, or per resting order matched.

- **Why it matters:** a strategy's fill handling, fee accounting and reconciliation should meet on paper the same shape
  of data it meets live. With one averaged fill, code that aggregates several fills per order is never exercised before
  going live, and per-fill prices and fees can't be compared with live.
- **Proposal:** emit one fill per price level taken, at that level's price and size, each with its own fee. The order's
  `sizeTraded` and `averagePrice` follow from the fills.
- **Things to settle:**
  - **Fees:** each fill is rounded to the fee asset's precision separately, as now, so many small fills can round
    differently from one large fill. That matches how live venues charge per execution.
  - **Transactions:** there is one `TradingFee`, and on perps one `Settlement`, per fill. Decide whether all fills from
    one sweep share a `groupId`, or each fill has its own as today (one per trade).
  - **Stream:** one `FillApplied` per fill, in price order, with the order's state after each.
  - **Notional market orders on spot:** split the spent quote across levels in the same way.
- **Docs:** if adopted, `paper/overview` "What is not modelled" loses its "Fills per level" bullet, and the "Taking
  liquidity" section and the flowchart say "one fill per level" instead of "one fill at the average price".
  `paper/going-live` "Execution realism" loses its sentence on averaged sweeps.

## Decide and document

These are behaviours, not bugs, but the docs need a stable answer:

- **Reduce-only sizing differs by mode.** In netting mode an oversized reduce-only order is rejected; in hedging mode a
  `Close` order is trimmed to the leg. Confirm both are intended. The docs describe both.
- **Unrealised loss and capacity.** Unrealised loss reduces available collateral only once it exceeds a position's
  locked backing. The docs now say exactly this.
- **Flip orders.** A netting order that reverses a position is rejected entirely if its opening part can't be backed,
  closing part included. The docs say this. An alternative is to fill the close and cancel the rest.
- **Stale collateral prices** reject perp orders that add risk, and margin and market state return `503`. Spot has no
  equivalent check. The docs leave continuity and feed outages out, treating them as non-functional.

## Doc statements that depend on these fixes

| Docs page | Statement | Depends on |
| --- | --- | --- |
| `paper/overview` "What paper simulates", "The same API as a real account" | Every host operation and both account streams, leverage the one exception | 9 |
| `paper/fees-and-funding` "Read it all back" | Paper hosts offer both transaction history and the transaction stream (example shows `Supported`) | 9 |
| `paper/going-live` "Capabilities paper offers…", "Transaction history and stream" | A paper host always offers the transaction stream | 9 |
| `paper/overview` "Wallets" (spot) | An order the balance cannot cover returns `422 InsufficientFunds` | 3 |
| `paper/overview` "Trigger orders" | Reduce-only trigger orders on perpetuals make stop-loss and take-profit orders | 5 |
| `paper/overview` "Trigger orders" | Funds are held from submission (implies they are sufficient when the trigger fires) | 4 |
| `paper/overview` "Taking liquidity" / "Resting orders" | A GTC remainder rests and fills from new trades and book changes | 1 |
| `paper/fees-and-funding` "Perpetual funding" | Funding times follow the venue's own schedule | 6, 7 |
| `paper/overview` "Paper hosts" | Paper markets take the model host's order rules | 8 |
| `paper/fees-and-funding` "Reading the rates" | Get fee settings leaves `fractionDigits` `null` because precision depends on the fee asset | 11 (spec wording) |
| `paper/fees-and-funding` "Trading fees" | Tiers are named and numbered like the exchange's where it publishes them | 14 (Bybit) |
