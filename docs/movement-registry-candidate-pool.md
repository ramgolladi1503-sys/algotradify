# Movement Registry and Candidate Pool Shell

PR 60 adds the first executable-safe shell around the movement opportunity engine. It is intentionally boring: providers can be registered, provider output can be collected, provider failures become diagnostics, and raw candidates can be normalized into a stable candidate pool.

This PR does **not** add movement strategies, ranking, broker integration, execution integration, API routes, dashboard panels, or order controls.

## Safety boundary

The registry and pool are read-only candidate infrastructure.

They must not:

- call broker APIs
- import broker modules
- build order intents
- submit, modify, cancel, or exit orders
- mutate runtime execution state
- produce `is_order_action=true`

Every public result object returns `is_order_action=false`.

## Files

```text
movement_engine/registry.py
movement_engine/candidate_pool.py
tests/test_movement_registry.py
tests/test_candidate_pool.py
docs/movement-registry-candidate-pool.md
```

## Registry contract

`MovementStrategyRegistry` is a provider shell.

A provider is a callable that receives `StrategyContext` and returns one of:

- a single `StrategyCandidate`
- a mapping shaped like a movement candidate
- an iterable of candidates/mappings
- `None`

The registry preserves provider registration order. It does not rank candidates and it does not execute anything.

### Registration behavior

`register_provider(strategy_id, provider)` returns `MovementProviderRegistrationResult`.

Blockers:

- `STRATEGY_ID_REQUIRED`
- `PROVIDER_MUST_BE_CALLABLE`
- `DUPLICATE_STRATEGY_PROVIDER`

Invalid registration returns a blocked result instead of partially registering unsafe provider state.

### Provider runtime behavior

`run(context)` returns `MovementRegistryRunResult`.

Provider exceptions are converted into diagnostics:

```text
PROVIDER_EXCEPTION:<strategy_id>
```

Invalid item types are converted into diagnostics:

```text
INVALID_PROVIDER_OUTPUT:<strategy_id>
```

The registry does not crash because one provider is broken. That is non-negotiable. A movement engine with 10+ future providers cannot let one bad provider kill the full opportunity scan.

## Candidate pool contract

`build_candidate_pool(...)` validates, hard-blocks, dedupes, and summarizes registry/provider output.

It returns `CandidatePoolResult` containing:

- `candidates`
- `summary`
- `warnings`
- `diagnostics`
- `is_order_action=false`

### Summary fields

`CandidatePoolSummary` includes stable counts:

- `input_count`
- `candidate_count`
- `raw_count`
- `valid_count`
- `blocked_count`
- `no_trade_count`
- `is_order_action=false`

`valid_count` includes executable-like candidate statuses only:

- `VALIDATED_CANDIDATE`
- `RANKED_OPPORTUNITY`

This is not permission to trade. It is only a candidate-pool status count.

## Hard blockers

The pool applies these hard blockers:

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

If a candidate has any of these blockers, the pool prevents validated or ranked status from surviving.

Example:

```text
status=VALIDATED_CANDIDATE + blockers=["WIDE_SPREAD"]
-> status=BLOCKED_CANDIDATE
```

`NO_TRADE` candidates with `NO_TRADE_CHOP` stay `NO_TRADE` when their direction is already `NO_TRADE`.

## Deduplication

Duplicate `candidate_id` values are collapsed deterministically.

Preference order:

1. `RANKED_OPPORTUNITY`
2. `VALIDATED_CANDIDATE`
3. `RAW_CANDIDATE`
4. `BLOCKED_CANDIDATE`
5. `NO_TRADE`

When status is tied, higher `raw_score` wins. Remaining ties use stable identity fields.

Duplicate collapse emits:

```text
DUPLICATE_CANDIDATE_DEDUPED
```

## Evidence preservation

Valid candidates keep their `evidence` dictionary unchanged.

Invalid mapping output is converted to a blocked candidate with validation evidence under:

```text
pool_validation_blockers
invalid_provider_payload
```

Hard-blocked candidates preserve original evidence and add:

```text
pool_hard_blockers
pool_blocked
```

## Why there are no strategies in this PR

Adding strategies before the registry and pool would recreate signal chaos. PR 60 only creates the shell that future strategies must obey.

Future PRs can add providers like opening drive, ORB retest, compression breakout, VWAP reclaim, failed-breakout trap, exhaustion, and event volatility. Those providers should plug into this shell instead of bypassing it.

## Validation

Focused validation:

```bash
python -m pytest tests/test_movement_registry.py tests/test_candidate_pool.py -q
python -m pytest tests/test_movement_contract.py tests/test_movement_regime.py -q
```

Safety validation:

```bash
python -m pytest tests/test_order_intent_contract.py tests/test_paper_broker_adapter.py tests/test_execution_safety.py -q
```

## Honest limitation

This PR still does not produce trade opportunities. It only makes future movement strategy output safer, diagnosable, deduped, and summary-ready.
