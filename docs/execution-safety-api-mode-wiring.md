# Execution Safety API Mode Wiring

PR 53 wires the strict execution-mode API parser into `/execution-safety`.

## Purpose

PR 51 hardened the core execution-mode contract.

PR 52 added strict API/query parsing.

PR 53 connects that parser to the actual execution-safety API response so the live endpoint no longer keeps the old unsafe behavior.

## Fixed behavior

Before this PR, `api.server._execution_safety_policy_from_request` treated every mode except `LIVE` as `PAPER`.

That meant values like:

```text
mode=REAL
mode=PRODUCTION
mode=anything
```

could silently become paper-mode behavior.

That is not acceptable for a real trading production roadmap.

## New API behavior

`/execution-safety` now uses:

```text
api.execution_mode_policy.execution_safety_policy_from_query
```

Response now includes:

```text
execution_mode_api_parse
```

The parse payload includes:

```text
mode
raw_mode
invalid_mode
supported_modes
blockers
warnings
is_order_action
```

## Rules

1. Missing mode defaults to `SIM`.
2. Invalid mode is forced to `SIM`.
3. Invalid mode adds `INVALID_EXECUTION_MODE` to blockers.
4. Invalid mode adds `EXECUTION_MODE_FORCED_TO_SIM` to warnings.
5. Paper preview requires explicit `mode=PAPER`.
6. LIVE still requires explicit LIVE readiness flags.
7. Invalid mode never permits execution.
8. Invalid mode clears all order-allowance flags.
9. API response remains visibility-only with `is_order_action=false`.

## Tests

Updated:

```text
tests/test_execution_safety_api.py
```

The tests prove:

- default API mode is SIM
- paper preview requires explicit `mode=PAPER`
- invalid mode never falls back to PAPER
- invalid mode blocks execution even when all other evidence is valid
- LIVE requires explicit readiness flags
- kill switch still blocks valid preview

## Safety boundary

This PR does not add:

- broker adapters
- real order endpoints
- order buttons
- broker API calls
- real orders in tests
- replay/control-tower polish
