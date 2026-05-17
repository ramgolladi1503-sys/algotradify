# Read-only Movement Opportunity Pipeline

PR 67 adds the first end-to-end movement opportunity pipeline.

The pipeline connects the existing movement layers into one read-only result:

```text
StrategyContext
-> MovementStrategyRegistry
-> CandidatePool
-> OptionPressureConfirmation
-> NoTradeFilter
-> MovementRanker
-> MovementOpportunityPipelineResult
```

## Files

```text
movement_engine/pipeline.py
tests/test_movement_pipeline.py
docs/movement-opportunity-pipeline.md
```

## Core API

```python
run_movement_opportunity_pipeline(context)
```

Optional custom registry:

```python
run_movement_opportunity_pipeline(context, registry=custom_registry)
```

Default registry:

```python
build_default_movement_registry()
```

The default registry registers:

```text
OPENING_DRIVE
ORB_RETEST
COMPRESSION_BREAKOUT
TREND_PULLBACK
VWAP_RECLAIM
FAILED_BREAKOUT_TRAP
```

## Pipeline result

`MovementOpportunityPipelineResult` includes:

```text
summary
registry_result
candidate_pool_result
option_enriched_candidates
no_trade_filter_result
rank_result
warnings
diagnostics
read_only=true
is_order_action=false
```

## Summary

`MovementOpportunityPipelineSummary` includes:

```text
schema_version
provider_count
registry_candidate_count
pooled_candidate_count
option_enriched_count
allowed_count
blocked_count
no_trade_count
ranked_count
excluded_count
diagnostic_count
warning_count
top_candidate_id
read_only=true
is_order_action=false
```

## Stage responsibilities

### Registry

Collects provider candidates and captures provider failures as diagnostics.

### Candidate pool

Validates candidate contracts, dedupes candidates, and applies pool-level hard blockers.

### Option pressure

Adds CE/PE pressure confirmation evidence to each candidate.

### No-trade filter

Converts unsafe candidates into `BLOCKED_CANDIDATE` or explicit `NO_TRADE` candidates.

### Ranker

Ranks only allowed candidates and excludes blocked, no-trade, and not-filtered candidates.

## Safety boundary

This PR only builds the read-only opportunity pipeline. It does not add API routes, dashboard screens, broker adapters, or execution wiring. Every public pipeline output keeps:

```text
read_only=true
is_order_action=false
```

## Evidence preservation

Ranked candidates should preserve evidence across all stages:

```text
raw provider evidence
option_pressure_confirmation
no_trade_filter
movement_ranker
```

## Validation

Focused validation:

```bash
python -m pytest tests/test_movement_pipeline.py -q
```

Full movement validation:

```bash
python -m pytest \
  tests/test_movement_registry.py \
  tests/test_candidate_pool.py \
  tests/test_movement_contract.py \
  tests/test_movement_regime.py \
  tests/test_option_pressure.py \
  tests/test_no_trade_filter.py \
  tests/test_movement_ranker.py \
  tests/test_movement_pipeline.py \
  tests/test_opening_drive_orb_providers.py \
  tests/test_compression_trend_providers.py \
  tests/test_vwap_trap_providers.py \
  -q
```

## Honest limitation

This pipeline produces ranked read-only movement opportunities. It still does not choose trades. The next correct step is a read-only API around this pipeline.
