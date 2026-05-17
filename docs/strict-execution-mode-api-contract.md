# Strict Execution Mode API Contract

PR 52 hardens execution-mode parsing for API-facing policy construction.

## Problem

After PR 51, the core execution-safety contract supports strict modes:

```text
SIM
PAPER
LIVE
```

But the API parsing behavior still had a dangerous pattern: an unknown mode could silently collapse into `PAPER` behavior.

That is not acceptable for a production-grade trading bot roadmap.

## Contract

The API parser must follow these rules:

1. Missing `mode` defaults to `SIM`.
2. Blank `mode` defaults to `SIM`.
3. Supported values are only:
   - `SIM`
   - `PAPER`
   - `LIVE`
4. Mode parsing is case-insensitive.
5. Unknown modes never fall back to `PAPER` or `LIVE`.
6. Unknown modes are forced to `SIM` and marked with:
   - blocker: `INVALID_EXECUTION_MODE`
   - warning: `EXECUTION_MODE_FORCED_TO_SIM`
7. Missing mode is marked with:
   - warning: `EXECUTION_MODE_DEFAULTED_TO_SIM`
8. Parser result is visibility-only and always emits `is_order_action=false`.

## Implementation

Added module:

```text
api/execution_mode_policy.py
```

Key functions:

```text
parse_execution_mode_from_query
execution_safety_policy_from_query
```

## LIVE readiness flags

The API policy parser maps LIVE readiness flags explicitly:

```text
live_broker_ready
live_risk_ready
live_kill_switch_ready
real_broker_order_adapter_enabled
```

These default to `false`; they are never implicitly enabled.

## Tests

Added tests:

```text
tests/test_execution_mode_api_contract.py
```

The tests prove:

- missing mode defaults to SIM
- valid SIM/PAPER/LIVE values are accepted
- unknown mode is rejected and forced to SIM
- invalid mode metadata is preserved
- LIVE readiness flags are explicit
- LIVE readiness flags are never implicitly enabled

## Safety boundary

This PR does not add:

- broker adapters
- real order endpoints
- order buttons
- broker API calls
- real orders in tests
- replay/control-tower polish

## Follow-up

The next safe step is wiring `api.server._execution_safety_policy_from_request` to this parser helper and exposing the parser metadata in `/execution-safety` responses.
