# Paper engine review (`execution-host-paper`)

**Status (2026-10-26):** review of the paper trading engine at the locked commit `ddf3a5e`, for positioning and docs
accuracy. Internal note: it names internals, thresholds and limits that must not go into the public docs as written.
Paths are under `.upstream/plurex/execution-host-paper/src/main/kotlin/io/plurex/paper/` unless stated.

Sections: 1, what the engine does; 2, the gaps; 3, issues to raise with plurex; 4, what our docs must change.

## 1. What the engine does

### Markets and the API

- **Every account is a real host account in shape.** Paper hosts publish their own capabilities, markets and order
  rules, and serve the same host operations and streams. Order queries, cancels, fills and the order stream are always
  supported, whatever the model host offers (`PaperHostCapabilities.kt`).
- **Broader than the live host in places:**
  - `GetOrder`/`GetOrders` by clientOrderId, including the global variants VALR lacks;
  - `ListFills` `ByOrderId`, which VALR lacks;
  - all `ListClosedOrders` variants;
  - fill details on the order stream (VALR live has none);
  - GTC/IOC/FOK on limit and trigger-limit orders, IOC/FOK on market and trigger-market orders;
  - Get position mode on VALR perps.
- **Markets come from the model host and the venue together.** Spot, linear perps and inverse perps keep the model
  host's order rules unchanged: increments, minimums and value floors. Futures and options are dropped.
- **Order options follow the model host.** Post-only, reduce-only and position effect come from the host; reduce-only
  and position effect are off on spot. Spot market orders take sizing by size or notional; perps take size only.

### Matching (`core/matching`)

- **Taking liquidity.** A marketable order walks the live visible book level by level, only to its limit price for a
  limit order. It fills as taker in one fill at the volume-weighted average price, so slippage and price improvement
  are real. IOC, FOK and post-only are modelled: post-only is cancelled, never slid.
- **Resting orders and queue position.**
  - An order joins the queue behind the visible size at its price.
  - Public trades at its price, from the side that hits it, work through that queue.
  - A shrinking visible size at its price moves it forward.
  - Trades through its price fill it directly, and so does a book that moves through its price.
  - Resting fills are maker fills at the order's own limit price.
  - An account's own orders share liquidity in price-time priority.
- **Partial fills** follow real public trade sizes.
- **Recovery.** Replayed or re-sent trades are never applied twice, and an order ignores trades from before it was
  created.

### Trigger orders (`core/triggers`)

- **Conditions:** `RefPriceGTE` or `RefPriceLTE`, as the model host allows per side.
- **Reference prices:** last trade (every public trade), best bid or ask (every top-of-book change), and mark or index
  (the venue's streamed observations).
- **Fallback:** where paper can't evaluate a reference, it substitutes in the capabilities (mark and index for each
  other, then last trade), never silently.
- **Firing:** an already-met condition fires at once; after a data gap, a trigger fires on the first fresh value
  instead of an invented crossing.
- **After firing,** the order enters matching as a plain limit or market order with the same options.
- **Funds** are held from submission.

### Wallets, collateral and positions (`core/wallet`, `core/collateral`, `core/exposure`)

- **Wallets.** One wallet per asset, with available, held and locked amounts. Spot orders hold quote or base; perp
  orders take collateral and turn it into position locks on fill. Deposits and withdrawals work for any asset.
  Withdrawals draw on available only.
- **One weighted collateral pool per host, spanning every perp**, modelled on the host's account type:

  | | bybit-paper (unified, valued in USD) | valr-paper (cross, valued in USDC) |
  | --- | --- | --- |
  | Assets and weights | USDC 1.0, USDT 1.0, BTC 0.98, ETH 0.98 | USDC 1.0, USDT 1.0, ZAR 1.0, BTC 0.95, ETH 0.925 |
  | Valuation prices | BTC and ETH at their perp index price; inverse debts at the contract's index price | BTC and ETH at last traded price; ZAR via USDT/ZAR spot |
  | Perps covered | Linear and inverse | Linear |

  - Collateral is drawn in a fixed asset order.
  - Debts and realised losses reduce capacity at full value.
  - Prices refresh about every second, and new perp risk is refused when they are stale.
- **Positions:**
  - Linear and inverse PnL formulas, with a harmonic average entry price for inverse.
  - Realised PnL settles into the settlement asset on every closing fill, as a `Settlement` transaction.
  - Unrealised PnL is valued at the mark price in margin states.
- **Position modes.** Netting and hedging work where the model market offers both. Switching needs a flat market.
  Hedging legs are independent. Reduce-only is checked against close capacity that other pending orders haven't
  already claimed.
- **Margin states and market state** report total and available collateral and initial margin (holds plus locks) per
  pool.

### Fees (`core/fees`, `providers/`)

- **Tiers are modelled on each host's schedule:**
  - VALR tiers 1, 2 and 7 use VALR's own tier numbers, with separate rates for fiat-quoted spot, stablecoin pairs,
    crypto spot and perps. Tier 7 has a maker rebate on fiat pairs. The rates were checked against VALR's published
    article.
  - Bybit has one "Standard" tier: spot and perp rates as configured, not verified against Bybit's published page.
- **Maker or taker** follows the fill's role.
- **Fee asset:** spot fees are in the quote asset; perp fees are in the settlement asset.
- **Rounding** is to the asset's precision.
- **A tier is chosen per account,** at creation or later. Rates are frozen per order when it is submitted, so a
  waiting trigger order keeps its original rates.

### Funding (`core/funding`)

- **Applies to:** linear and inverse perpetuals whose venue publishes finalised funding history.
- **Funding times are inferred from the venue's own recent history,** so they follow real 1h, 4h or 8h schedules.
- **Rate:** the venue's finalised rate for that time only, never the indicative one.
- **Position value:** taken at the close of the venue's one-minute mark-price candle ending at the funding time.
- **Who pays:** a positive rate debits longs and credits shorts. Hedge legs are charged separately. The position
  held immediately before the funding time pays the full period.
- **Missed times:** reconciliation pays funding times it missed when the position next changes.
- **Restarts:** accepted funding obligations survive restarts and retry until they resolve.
- **Unknown inputs:** funding that can't be priced or rated is skipped, never guessed.

### Transactions (`core/transaction`)

- **Types:** `Deposit`, `Withdrawal`, `TradingFee` (fee or rebate), `Settlement` (perp realised PnL) and
  `FundingPayment`.
- **IDs and links:** IDs are deterministic and match the stream. Postings link to the instrument and order, fill
  postings also to the fill, and fee and PnL postings from the same trade share a `groupId`.

## 2. The gaps

**Not modelled (by design):**

| Area | What is missing |
| --- | --- |
| Leverage | No leverage control. Margin is 1:1 notional. |
| Margin | No maintenance margin, liquidation, ADL, borrowing, interest, isolated margin or collateral tiers. |
| Order entry | No latency. Resting fills and triggers are evaluated on a short tick against the latest data. |
| Order types | No amend, OCO or bracket orders. |
| Liquidity | No hidden or iceberg liquidity. |
| Venue limits | No price bands, maximum order size or market-order slippage protection. A market order can sweep the whole visible book. |
| Own orders | No self-trade prevention. An account's own orders never interact. |
| Market impact | Paper orders never deplete the real book for later orders. |
| Fees | No volume-based tier progression. |
| Positions | ListPositions has no unrealised PnL, liquidation price or margin. |

**Not supported, where the owner's "full support" claim goes too far:**

- **Get and Set leverage** are `NotSupported`, as expected.
- **No transaction stream on bybit-paper.** The transaction list and stream copy the model host's capabilities, and
  Bybit has no transaction stream. This contradicts the module's own AGENTS.md "Phase 0" contract, which says paper
  supports every engine query and stream whatever the host offers.
- **Set position mode** only works where the model market offers both modes (Bybit USDT linear perps).

## 3. Issues to raise with plurex

These are code findings, verified in source at `ddf3a5e`, ordered by impact on realism.

1. **A crossing GTC limit order can take the same liquidity twice.** A marketable GTC limit order larger than the
   visible depth takes that depth as taker, and its remainder rests. On the next tick, `fillFromBook`
   (`core/matching/aggregate/PaperMatchingAggregateDecider.kt:199`) rebuilds the opposite levels from the same book
   snapshot. They are still at or through the resting price, so it fills the remainder again as maker, at the limit
   price and the maker rate. Large crossing limit orders fill more, and more cheaply, than live.
2. **Linear average entry price is rounded to 2 decimals** (HALF_UP) every time a position is increased
   (`core/contracts/PerpetualContractMath.kt`, `roundScale = 2`). Entry price and realised PnL are visibly wrong on
   low-priced contracts, for example anything under $1.
3. **Fees are not reserved at admission.** A full-balance spot buy is accepted and then leaves the quote wallet
   negative by the fee. A spot market buy is reserved at best ask × size, so a deeper sweep also overdraws.
   `design/PaperExchangeExecutionFlow.md` says reservation covers "Principal + Fees". Either fix the code or the doc.
4. **Trigger orders don't re-check funds or collateral when they fire.** AGENTS.md says they "reacquire their claim
   before submission"; in code, `RefreshClaim` is never sent. A worse fill than the reservation overdraws.
5. **Transaction stream and list follow the model host,** contrary to the Phase 0 contract in AGENTS.md (see section 2).
   Decide which is intended.
6. **A full-size reduce-only stop-loss and take-profit can't coexist in netting mode.** The waiting trigger claims close
   capacity at placement, so the second order is rejected with `REDUCE_ONLY_PENDING_EXHAUSTION`, and there is no OCO.
   This is a common live pattern, so worth deciding on.
7. **The funding schedule is read once per market,** in `FundingScheduleTick.initializeSchedules`. An interval change
   mid-position keeps timers at the old times until a restart or the next position change. This is inferred, not
   tested.
8. **Funding history must be regular.** If the venue's recent history is irregular, for example just after an interval
   change, no funding is paid until four evenly spaced records exist. There is no configured fallback for Bybit or
   VALR.
9. **Markets are a snapshot taken at warm-up.** New listings and changed order rules appear only after a paper host
   restart, and delisted venue markets stay listed.
10. **Get fee settings always returns `fractionDigits: null`** on tier rates, but paper always rounds. The spec text
    "null when fees are not rounded" is misleading.
11. **Smaller issues:**
    - After firing, `Order.triggerPrice` reports the observed firing value, not the configured trigger price.
    - `setMarketPositionMode` in the header is always `PerMarket`, even when no market can switch.
    - The clientOrderId duplicate check is not atomic under concurrent submits.
    - `design/PaperExchangeExecutionFlow.md` is stale on reservation flow and price-time priority.

## 4. What our docs must change

### Wrong or overstated today

| Page | Claim | What the code does |
| --- | --- | --- |
| `paper/overview` table and `paper/going-live` | "Reduce-only larger than the position left to close: rejected, not trimmed" | True in netting mode only. In hedging mode a `Close` order is trimmed to what is left. |
| `paper/overview` | "Unrealised losses reduce what you can open" | Unrealised losses reduce capacity only once a position's loss exceeds what is locked against it. What reduces capacity is holds, locks, realised losses, fees, funding and debts. |
| `paper/overview`, `paper/going-live` | "Closing is never blocked" | A pure close is never blocked. A netting order that flips the position is rejected entirely if its opening part can't be backed. |
| `paper/overview` | Spot: "an order the balance cannot cover returns InsufficientFunds" | Only the principal is checked. Fees aren't held, and a market buy is held at the best ask. |
| `paper/overview` | Stop-loss and take-profit pairing | A full-size pair can't both be placed in netting mode. |
| `paper/overview` | Triggers fire "when they cross"; things "act instantly" | Triggers fire when the price reaches or passes the trigger price. Resting fills and triggers are evaluated on a short tick, and cancels are asynchronous. |
| `paper/overview` | Queue: "public trades at that price work through the queue ahead" | Only trades from the side that hits you count, and shrinking visible size also moves you forward. |
| `paper/going-live` | "Both account streams" stay the same | bybit-paper has no transaction stream. |
| `paper/fees-and-funding` | "`fractionDigits` null means fees are not rounded", and the example shows `8` | Get fee settings returns `null` on tier rates, and paper always rounds. Only Get effective fee rates reports the precision. |

### Worth adding (realism we undersell)

- **Collateral modelling:** weighted multi-asset collateral per host, the valuation asset, a single cross pool across
  perps, and unrealised PnL at mark in margin states. Decide whether to publish the weights or describe them as "the
  model host's collateral assets and weights". They are not reported by the API, so publishing them would hard-code
  facts.
- **Fee tiers that follow the host's real schedule,** including instrument groups and rebates; and rates frozen per
  order.
- **Funding:** times follow the venue's real schedule; the position value comes from the mark price at the funding
  time; and the full period is paid with no pro-rating.
- **Queue realism:** price-time sharing between your own orders, and fills when the book moves through your price.
- **Order outcomes:** partly filled orders are `LIVE`; post-only, IOC and FOK outcomes come back as a cancelled order,
  not an error.
- **Paper's extra capabilities** compared with the live host (the list in section 1).
- **Market snapshot:** markets and order rules are captured when the paper host starts.

### Keep out of the public docs

- Continuity, restarts and feed outages: non-functional, improved internally (decided 2026-10-26).
- Absent host API features such as amend: they arrive on paper when hosts gain them.

- The 10-resting-orders-per-market cap and the deposit ceiling (pending pricing).
- Tick intervals, staleness ages, rounding scales and funding thresholds.
- Internal state and claim names.
