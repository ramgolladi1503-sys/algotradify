# Option Pressure Confirmation Layer

PR 64 adds a read-only option-pressure confirmation layer for movement candidates.

This is not a strategy provider and it is not an execution layer. Its job is to reduce raw candidate noise by checking whether CE/PE option evidence actually supports the candidate direction.

## Files

```text
movement_engine/option_pressure.py
tests/test_option_pressure.py
docs/option-pressure-confirmation.md
```

## Contract

The core function is:

```python
confirm_option_pressure(context, direction)
```

It returns `OptionPressureConfirmationResult` with:

```text
direction
status
confirmed
pressure_score
ce_pressure_score
pe_pressure_score
premium_bias
spread_quality_score
depth_quality_score
freshness_score
blockers
warnings
evidence
is_order_action=false
```

The result is read-only evidence. It must not submit, modify, cancel, or exit orders.

## Status values

```text
CONFIRMED
WEAK_CONFIRMATION
CONFLICTING_PRESSURE
BLOCKED
NOT_APPLICABLE
```

### CONFIRMED

The selected direction has enough option-side pressure, spread quality, depth quality, and freshness.

Example:

```text
BUY_CALL + CE premium expansion > PE pressure + good CE spread/depth + fresh quote
-> CONFIRMED
```

### WEAK_CONFIRMATION

The direction is not contradicted, but pressure is not strong enough.

Example:

```text
BUY_CALL + CE premium only slightly stronger + mediocre spread/depth
-> WEAK_CONFIRMATION
```

This is a warning, not a pool hard-blocker by itself.

### CONFLICTING_PRESSURE

The selected candidate direction conflicts with option pressure.

Example:

```text
BUY_CALL candidate + PE pressure strongly dominates CE pressure
-> CONFLICTING_PRESSURE
-> adds CONFLICTING_OPTION_PRESSURE
-> adds CONFLICTING_TRAP_SIGNAL for candidate-pool hard blocking
```

### BLOCKED

Required option evidence is unsafe or missing.

Blockers include:

```text
STALE_OPTION_LTP
FALLBACK_QUOTE_ONLY
UNRESOLVED_CONTRACT
WIDE_SPREAD
MISSING_DEPTH
CONTEXT_REQUIRED
```

### NOT_APPLICABLE

Used for `NO_TRADE` direction.

## Candidate attachment

Use:

```python
attach_option_pressure_confirmation(candidate, context)
```

This returns a new `StrategyCandidate` with confirmation evidence attached under:

```text
option_pressure_confirmation
```

It also updates:

```text
option_confirmation_score
liquidity_score
freshness_score
blockers
warnings
evidence
```

The candidate remains `is_order_action=false`.

## Batch helper

Use:

```python
attach_option_pressure_to_candidates(candidates, context)
```

It returns a tuple of enriched candidates.

## Interaction with candidate pool

The option-pressure layer does not directly decide execution.

It adds blockers/warnings and then the existing candidate pool enforces hard blockers.

Example:

```text
candidate direction = BUY_CALL
option pressure = CONFLICTING_PRESSURE
candidate gets CONFLICTING_TRAP_SIGNAL
candidate pool converts it to BLOCKED_CANDIDATE
```

## Safety boundary

This PR does **not** add:

- new movement strategies
- ranking
- no-trade engine
- order intent integration
- broker/order imports
- execution integration
- API routes
- dashboard/UI changes
- replay/control-tower polish

## Validation

Focused validation:

```bash
python -m pytest tests/test_option_pressure.py -q
python -m pytest tests/test_candidate_pool.py tests/test_movement_contract.py -q
```

Provider regression validation:

```bash
python -m pytest tests/test_opening_drive_orb_providers.py tests/test_compression_trend_providers.py tests/test_vwap_trap_providers.py -q
```

## Honest limitation

This layer confirms option-side pressure. It does not rank candidates, choose trades, or prove profitability.

The correct next steps are:

```text
PR 65 — No-Trade and Conflict Filter
PR 66 — Movement Candidate Ranker v1
PR 67 — Read-only Movement Opportunity API
```
