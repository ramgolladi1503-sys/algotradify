# Execution Safety Response Contract

PR 54 freezes the response-shape contract for `/execution-safety`.

## Why this exists

PR 51 hardened the execution-mode contract.
PR 52 added strict API mode parsing.
PR 53 wired that parser into `/execution-safety`.

The next risk is quieter: a future change could accidentally remove safety-critical response fields while tests still pass.

This contract prevents that.

## Contract module

```text
api/execution_safety_response_contract.py
```

Exports:

```text
execution_safety_response_schema_contract
validate_execution_safety_response_contract
```

## Required response keys

`/execution-safety` must keep these keys:

```text
execution_permitted
mode
status
blockers
warnings
audit
requires_manual_approval
simulated_order_allowed
paper_order_allowed
broker_api_allowed
real_order_allowed
is_order_action
execution_mode_api_parse
top_executable
readiness_records_checked
safety_visibility_only
```

## Required parser metadata

`execution_mode_api_parse` must keep:

```text
mode
raw_mode
invalid_mode
supported_modes
blockers
warnings
is_order_action
```

## Safety rules

Global immutable rule:

```text
is_order_action=false
```

Invalid-mode rule:

When `execution_mode_api_parse.invalid_mode=true`, the response must keep:

```text
execution_permitted=false
simulated_order_allowed=false
paper_order_allowed=false
broker_api_allowed=false
real_order_allowed=false
```

## Why broker flags are not globally forced false

A future production LIVE path may legitimately expose `broker_api_allowed=true` after all LIVE readiness gates pass.

So the contract is deliberately mode-aware:

- always forbid `is_order_action=true`
- forbid broker/real-order allowance only for invalid-mode responses
- keep required fields stable for every response

## Tests

Added:

```text
tests/test_execution_safety_response_contract.py
```

The tests prove:

- schema contract lists safety-critical keys
- default blocked `/execution-safety` response validates
- invalid-mode `/execution-safety` response validates
- missing parser fields are detected
- unsafe invalid-mode flags are detected

## Safety boundary

This PR does not add:

- broker adapters
- real order endpoints
- order buttons
- broker API calls
- real orders in tests
- replay/control-tower polish
