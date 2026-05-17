# Movement Candidate Ranker v1

PR 66 adds a read-only ranker for movement candidates.

This is not an execution layer. It does not create order intents, call brokers, submit orders, expose dashboard controls, or choose trades for live execution. It only ranks candidates that already passed the no-trade/conflict filter.

## Files

```text
movement_engine/ranker.py
tests/test_movement_ranker.py
docs/movement-candidate-ranker.md
```

## Contract

Core function:

```python
rank_movement_candidates(candidates)
```

It returns `MovementRankResult` with:

```text
ranked_candidates
rank_records
exclusions
summary
warnings
diagnostics
is_order_action=false
```

## Rankable candidates

A candidate is rankable only when:

```text
status in RAW_CANDIDATE, VALIDATED_CANDIDATE, RANKED_OPPORTUNITY
no_trade_filter.decision == ALLOW_CANDIDATE
direction != NO_TRADE
status != BLOCKED_CANDIDATE
status != NO_TRADE
```

The ranker intentionally requires no-trade filter evidence. A raw provider candidate that has not passed the no-trade layer is excluded.

## Exclusions

Exclusion reasons:

```text
BLOCKED_CANDIDATE
NO_TRADE
NOT_ALLOWED_BY_NO_TRADE_FILTER
UNRANKABLE_STATUS
```

Exclusions are evidence and diagnostics only. They are not order actions.

## Ranking score

The v1 weighted score uses existing candidate fields:

```text
raw_score                  18%
confidence_score           18%
option_confirmation_score  20%
liquidity_score            14%
freshness_score            12%
volatility_score            8%
regime_alignment_score     10%
```

These weights are intentionally simple. They are contract-safe and deterministic, not a profitability claim.

## Tie breakers

When candidates have the same rank score, deterministic tie-breakers are applied:

```text
higher option_confirmation_score
higher liquidity_score
higher freshness_score
higher regime_alignment_score
strategy_id ascending
candidate_id ascending
```

This prevents unstable rank order between test runs or UI refreshes.

## Ranked candidate output

Ranked candidates are returned with:

```text
status = RANKED_OPPORTUNITY
```

Rank evidence is attached under:

```text
movement_ranker
```

The original candidate evidence is preserved.

## Summary

`MovementRankSummary` includes:

```text
input_count
ranked_count
excluded_count
blocked_count
no_trade_count
top_candidate_id
is_order_action=false
```

## Safety boundary

This PR does **not** add:

- order intent integration
- broker/order imports
- execution integration
- API routes
- dashboard/UI changes
- replay/control-tower polish
- new strategy providers

Every public result remains:

```text
is_order_action=false
```

## Validation

Focused validation:

```bash
python -m pytest tests/test_movement_ranker.py -q
python -m pytest tests/test_no_trade_filter.py tests/test_option_pressure.py tests/test_candidate_pool.py -q
```

Provider regression validation:

```bash
python -m pytest tests/test_opening_drive_orb_providers.py tests/test_compression_trend_providers.py tests/test_vwap_trap_providers.py -q
```

## Honest limitation

The ranker orders candidates. It does not decide whether a trade should be placed.

The next correct step is a read-only Movement Opportunity Pipeline that wires:

```text
registry -> candidate pool -> option pressure -> no-trade filter -> ranker
```

After that, expose a read-only API. Do not jump to execution yet.
