# No-Trade and Conflict Filter

PR 65 adds a read-only filter layer that decides whether movement candidates should remain allowed, become blocked, or become explicit no-trade candidates.

This is not a ranker and not an execution layer. Its job is to make the bot capable of saying “do nothing” before ranking or broker integration exists.

## Files

```text
movement_engine/no_trade_filter.py
tests/test_no_trade_filter.py
docs/no-trade-conflict-filter.md
```

## Contract

Core functions:

```python
apply_no_trade_filter(candidate)
apply_no_trade_filter_to_candidates(candidates)
```

`apply_no_trade_filter(candidate)` returns:

```text
(filtered_candidate, NoTradeFilterResult)
```

`apply_no_trade_filter_to_candidates(candidates)` returns `NoTradeFilterBatchResult` with:

```text
candidates
results
summary
warnings
diagnostics
is_order_action=false
```

## Decisions

```text
ALLOW_CANDIDATE
BLOCK_CANDIDATE
NO_TRADE
```

### ALLOW_CANDIDATE

The candidate remains a candidate proposal. It is still not executable.

Example:

```text
RAW_CANDIDATE + confirmed option pressure + no hard blocker
-> ALLOW_CANDIDATE
```

### BLOCK_CANDIDATE

The candidate becomes `BLOCKED_CANDIDATE`.

Examples:

```text
candidate + CONFLICTING_OPTION_PRESSURE
-> BLOCK_CANDIDATE

candidate + MARKET_CLOSED
-> BLOCK_CANDIDATE

candidate + stale/fallback/wide-spread/missing-depth option evidence
-> BLOCK_CANDIDATE
```

### NO_TRADE

The candidate becomes explicit `NO_TRADE` with `direction=NO_TRADE`.

Example:

```text
candidate.direction = NO_TRADE
-> NO_TRADE
```

## Hard no-trade blockers

```text
MARKET_CLOSED
STALE_OPTION_LTP
FALLBACK_QUOTE_ONLY
UNRESOLVED_CONTRACT
WIDE_SPREAD
MISSING_DEPTH
CONFLICTING_TRAP_SIGNAL
NO_TRADE_CHOP
EXECUTION_SAFETY_NOT_PERMITTED
```

## Weak confirmation handling

Weak confirmation is not always a hard block.

Allowed example:

```text
WEAK_CONFIRMATION + clean liquidity + clean freshness + acceptable regime
-> ALLOW_CANDIDATE with warning
```

Blocked example:

```text
WEAK_CONFIRMATION + poor liquidity/freshness/regime or hard blocker
-> BLOCK_CANDIDATE
```

This prevents over-filtering clean but early setups while still blocking weak signals in bad context.

## Evidence

The filter attaches evidence under:

```text
no_trade_filter
```

It preserves existing evidence such as:

```text
option_pressure_confirmation
provider
strategy_family
raw provider evidence
```

All filter diagnostics include:

```text
is_order_action=false
```

## Interaction with option pressure

The filter consumes option-pressure evidence produced by PR 64.

Important statuses:

```text
CONFIRMED
WEAK_CONFIRMATION
CONFLICTING_PRESSURE
BLOCKED
NOT_APPLICABLE
```

Rules:

```text
CONFLICTING_PRESSURE -> BLOCK_CANDIDATE
BLOCKED -> BLOCK_CANDIDATE
NOT_APPLICABLE on trade direction -> BLOCK_CANDIDATE
WEAK_CONFIRMATION + bad context -> BLOCK_CANDIDATE
WEAK_CONFIRMATION + clean context -> ALLOW_CANDIDATE with warning
```

## Safety boundary

This PR does **not** add:

- new movement strategies
- ranking
- order intent integration
- broker/order imports
- execution integration
- API routes
- dashboard/UI changes
- replay/control-tower polish

Every public result and candidate output remains `is_order_action=false`.

## Validation

Focused validation:

```bash
python -m pytest tests/test_no_trade_filter.py -q
python -m pytest tests/test_option_pressure.py tests/test_candidate_pool.py tests/test_movement_contract.py -q
```

Provider regression validation:

```bash
python -m pytest tests/test_opening_drive_orb_providers.py tests/test_compression_trend_providers.py tests/test_vwap_trap_providers.py -q
```

## Honest limitation

This layer filters candidates. It still does not rank them, choose trades, call brokers, or prove profitability.

The correct next step is:

```text
PR 66 — Movement Candidate Ranker v1
```
