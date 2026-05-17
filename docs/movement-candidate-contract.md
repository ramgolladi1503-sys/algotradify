# Movement Candidate Contract

PR 58 adds the first implementation layer for the movement opportunity engine.

## Purpose

Movement strategies must produce candidates, not trades.

A movement candidate is a proposal with evidence, scores, blockers, warnings, and explanation. It is not executable truth.

## Implementation

```text
movement_engine/
  __init__.py
  context.py
  contract.py
```

Exports:

```text
StrategyContext
StrategyCandidate
Direction
CandidateStatus
MovementCandidateValidationResult
validate_strategy_candidate
candidate_from_mapping
```

## Candidate directions

```text
BUY_CALL
BUY_PUT
NO_TRADE
```

## Candidate statuses

```text
RAW_CANDIDATE
VALIDATED_CANDIDATE
BLOCKED_CANDIDATE
RANKED_OPPORTUNITY
NO_TRADE
```

## Required candidate fields

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

## Score rules

All score fields must be between `0.0` and `1.0`:

```text
raw_score
confidence_score
price_structure_score
option_confirmation_score
liquidity_score
freshness_score
volatility_score
regime_alignment_score
```

## StrategyContext

`StrategyContext` defines a shared read-only input shape for future movement strategies.

It includes spot, VWAP, ORB, ATR, range, option premium, spread, depth, freshness, time, and expiry fields.

Missing market evidence should not crash strategies. Missing evidence should become blockers or warnings in later strategy PRs.

## Validation blockers

The validator can emit:

```text
CANDIDATE_REQUIRED
INVALID_SCHEMA_VERSION
CANDIDATE_ID_REQUIRED
STRATEGY_ID_REQUIRED
MOVEMENT_TYPE_REQUIRED
SYMBOL_REQUIRED
ENTRY_TRIGGER_REQUIRED
INVALID_IF_REQUIRED
RANK_REASON_REQUIRED
INVALID_DIRECTION
INVALID_STATUS
*_SCORE_REQUIRED
*_SCORE_OUT_OF_RANGE
BLOCKERS_MUST_BE_STRING_LIST
WARNINGS_MUST_BE_STRING_LIST
EVIDENCE_MUST_BE_DICT
CANDIDATE_ORDER_FLAG_UNSAFE
NO_TRADE_STATUS_REQUIRES_NO_TRADE_DIRECTION
```

## Validation warnings

```text
BLOCKED_OR_NO_TRADE_WITHOUT_EXPLANATORY_BLOCKER
```

## Safety boundary

This PR does not add:

- movement strategy behavior
- candidate pool behavior
- ranker behavior
- execution changes
- broker changes
- order changes
- dashboard changes

## Tests

Added:

```text
tests/test_movement_contract.py
```

The tests prove:

- valid candidate serializes and validates
- candidate can round-trip from mapping
- invalid direction fails
- invalid status fails
- score outside 0..1 fails
- missing identity fields fail
- missing reason fields fail
- blockers/warnings must be string lists
- evidence must be dict
- candidate order flag must remain false
- no-trade status requires no-trade direction
- blocked candidates without blockers get warning
- valid no-trade candidate passes
- StrategyContext serializes missing fields safely
