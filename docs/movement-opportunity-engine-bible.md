# Movement Opportunity Engine Bible

## Status

This document defines the algotradify implementation plan for adding a movement-opportunity engine after the execution safety, order-intent, and paper-broker contract chain.

Current completed foundation:

```text
PR 51 — Execution Mode Contract Hardening
PR 52 — Strict Execution Mode API Contract
PR 53 — Wire Strict Execution Mode Parser into Execution Safety API
PR 54 — Execution Safety Response Schema Contract
PR 55 — Pre-Broker Order Intent Contract
PR 56 — Paper Broker Adapter Contract
```

## Brutal premise

Adding 10+ strategies directly into existing strategy files will make the bot noisier, not smarter.

The correct architecture is:

```text
market data -> movement candidates -> candidate pool -> blockers -> ranker -> evidence -> safety/order-intent/paper path
```

Not:

```text
strategy emits row -> pretend it is executable
```

## Target architecture

```text
MarketSnapshot
  -> MovementRegimeClassifier
  -> MovementStrategyRegistry
  -> StrategyCandidate[]
  -> OptionConfirmationLayer
  -> LiquidityFreshnessBlockerLayer
  -> CandidatePool
  -> NoTradeEngine
  -> OpportunityRanker
  -> Evidence/API/UI
  -> Existing execution safety
  -> OrderIntent
  -> PaperBroker / later LIVE guard
```

## Non-goals

The movement engine must not:

- call broker APIs;
- create real orders;
- weaken execution safety;
- bypass order-intent validation;
- treat fallback quotes as executable truth;
- hide stale option LTP;
- turn raw candidates into executable rows;
- modify submit/modify/cancel/exit flows;
- add dashboard execution buttons.

## Core rule

Every movement strategy returns a candidate, not a trade.

Candidate states:

```text
RAW_CANDIDATE
VALIDATED_CANDIDATE
BLOCKED_CANDIDATE
RANKED_OPPORTUNITY
NO_TRADE
```

Only later layers can decide whether something becomes:

```text
ADVISORY_ONLY
QUEUE_ONLY
PAPER_ELIGIBLE
LIVE_ELIGIBLE
NO_TRADE
```

## Candidate contract direction

Add:

```text
movement_engine/contract.py
```

Required candidate fields:

```text
schema_version
candidate_id
strategy_id
movement_type
symbol
direction
status
raw_score
confidence_score
price_structure_score
option_confirmation_score
liquidity_score
freshness_score
volatility_score
regime_alignment_score
entry_trigger
invalid_if
rank_reason
blockers
warnings
evidence
is_order_action=false
```

Valid directions:

```text
BUY_CALL
BUY_PUT
NO_TRADE
```

## Strategy context direction

Every strategy receives one shared context shape.

Add:

```text
movement_engine/context.py
```

Fields:

```text
symbol
ts_epoch
spot_ltp
vwap
day_high
day_low
orb_high
orb_low
prev_day_high
prev_day_low
atr
atr_short
atr_long
range_width_pct
volume_z
volatility_state
regime_hint
option_ce_ltp
option_pe_ltp
ce_premium_change
pe_premium_change
ce_spread_pct
pe_spread_pct
ce_depth
pe_depth
option_ltp_age_sec
quote_source
time_of_day
minutes_since_open
minutes_to_close
expiry_context
```

Missing fields must not crash strategies. Missing evidence must become blockers or warnings.

## Movement strategy pack

Build in pairs, not all at once:

```text
Opening Drive
Opening Range Breakout Retest
Compression Breakout
Trend Pullback Continuation
VWAP Reclaim / Rejection
Failed Breakout / Trap
Exhaustion Reversal
Mean Reversion Extension
Event / Volatility Expansion
Late-Day Momentum
Option Pressure Confirmation
No-Trade Chop Detector
```

## Hard blockers

These prevent executable status:

```text
STALE_OPTION_LTP
WIDE_SPREAD
MISSING_DEPTH
FALLBACK_QUOTE_ONLY
UNRESOLVED_CONTRACT
CONFLICTING_TRAP_SIGNAL
NO_TRADE_CHOP
MARKET_CLOSED
EXECUTION_SAFETY_NOT_PERMITTED
```

## Soft blockers

These reduce ranking but may preserve advisory status:

```text
BIAS_CONFLICT
LATE_ENTRY
NEAR_RESISTANCE
NEAR_SUPPORT
LOW_VOLUME_CONFIRMATION
WEAK_OPTION_CONFIRMATION
LOW_VOLATILITY
MIXED_REGIME
EXPIRY_DECAY_RISK
```

## Ranking formula v1

Start deterministic. Do not add ML yet.

```text
rank_score =
  0.25 * price_structure_score
+ 0.25 * option_confirmation_score
+ 0.20 * liquidity_score
+ 0.15 * freshness_score
+ 0.10 * volatility_score
+ 0.05 * regime_alignment_score
- blocker_penalties
```

Rules:

- stale option LTP cannot be executable;
- fallback quote cannot be executable;
- wide spread cannot be executable;
- no-trade candidate can suppress weak candidates;
- rank reason must explain the score.

## Evidence output

Future evidence should include:

```text
candidate_count
validated_candidate_count
blocked_candidate_count
ranked_opportunity_count
no_trade_reason
strategy_activation_counts
strategy_suppression_counts
top_rank_reasons
top_blockers
fallback_candidate_count
stale_candidate_count
wide_spread_candidate_count
```

## Dashboard direction

Later UI must separate:

```text
Top Ranked Opportunities
Validated Candidates
Blocked Candidates
Raw Strategy Candidates
No-Trade Explanation
Diagnostics / Evidence
```

Raw candidates must never be displayed as executable opportunities.

## Immediate build sequence

```text
PR 57 — Movement Opportunity Engine Bible
PR 58 — Movement Candidate Contract
PR 59 — Movement Regime Classifier v1
PR 60 — Movement Registry and Candidate Pool Shell
PR 61 — Opening Drive and ORB Retest
PR 62 — Compression Breakout and Trend Pullback
PR 63 — VWAP Reclaim and Failed Breakout Trap
PR 64 — Exhaustion and Mean Reversion Extension
PR 65 — Event Volatility and Late-Day Momentum
PR 66 — Option Pressure Confirmation
PR 67 — No-Trade Engine
PR 68 — Opportunity Ranker v1
PR 69 — Movement Evidence and API Read Model
PR 70 — Dashboard Separation
```

## Do-not-break rules

For PR 58 through PR 60:

- do not edit existing strategy behavior;
- do not connect movement candidates to execution;
- do not touch broker adapters;
- do not touch paper/live order flow;
- do not change execution safety;
- do not add UI execution controls.

## Final operating principle

Build truth first, then ranking, then evidence, then UI, then execution eligibility.

Do not chase trades. Build a candidate-quality engine.
