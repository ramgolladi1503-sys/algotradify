# Runtime Ownership API and Control Tower Visibility

## Purpose

Runtime Correction PR 7 exposes native runtime ownership status through a read-only API and a read-only Control Tower panel helper.

This PR is visibility-only. It does not start the runtime, call broker APIs, create orders, mutate runtime mode, add auth endpoints, or add dashboard action controls.

## API

```http
GET /runtime/ownership
```

Contract:

```text
runtime_ownership_status_v1
```

Key fields:

```text
runtime_ownership
native_source_present
native_main_promoted
native_required
external_runtime_allowed
external_runtime_used
runtime_root
runtime_artifact_root
can_start_native_runtime
warnings
blockers
read_only
audit_only
is_order_action
broker_api_called
real_order_id
live_mode_touched
```

Expected healthy native state after PR 5/6:

```text
runtime_ownership=NATIVE
native_source_present=true
native_main_promoted=true
external_runtime_used=false
can_start_native_runtime=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
live_mode_touched=false
```

## Control Tower panel helper

The panel helper lives at:

```text
dashboard/runtime_ownership_panel.py
```

It normalizes the API payload into a display-only model with:

```text
read_only_panel=true
allowed_actions=[]
forbidden_actions=[submit_order, modify_order, cancel_order, exit_position, broker_call, toggle_live, write_runtime_state]
```

## Safety boundary

This PR must not:

- add broker order behavior
- add auth API endpoints
- add dashboard action controls
- mutate runtime state
- start runtime workers
- change paper/agent internals
- make LIVE the default

## Acceptance proof

```bash
python -m pytest tests/test_runtime_ownership_api.py tests/test_runtime_ownership_panel.py -q
```

The tests prove:

- the API payload is read-only
- safe flags are fixed
- the route is GET-only
- the route exposes no order verbs
- the panel exposes no actions
- the panel advertises forbidden action categories explicitly
