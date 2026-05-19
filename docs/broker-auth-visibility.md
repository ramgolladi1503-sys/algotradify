# Broker Auth Visibility and Startup UX

## Purpose

Runtime Correction PR 8 adds broker auth visibility and startup guidance without creating any auth mutation surface.

This PR is local-only visibility. It does not call broker APIs, run login from API/dashboard, mutate tokens, expose raw tokens, expose API secrets, create orders, change live mode, or start runtime workers.

## API

```http
GET /broker/auth/visibility
```

Contract:

```text
broker_auth_visibility_v1
```

The API checks local files/environment only:

```text
.runtime/kite_access_token
KITE_API_KEY
KITE_API_SECRET
KITE_ACCESS_TOKEN
```

## Safe fields

The payload may expose:

```text
api_key_present
api_key_tail4
api_secret_present
token_file_present
token_file_length
token_file_tail4
token_file_usable_shape
env_token_present
env_token_length
env_token_tail4
env_token_usable_shape
can_validate_locally
can_attempt_login_locally
login_required
operator_commands
blockers
warnings
```

The payload must always include:

```text
read_only=true
auth_visibility_only=true
is_order_action=false
broker_api_called=false
profile_probe_called=false
token_mutated=false
raw_token_exposed=false
api_secret_exposed=false
real_order_id=null
live_mode_touched=false
```

## Operator guidance

The payload includes command guidance only:

```bash
./run_live.sh --login-only
./run_live.sh --validate-only
./run_live.sh --start --i-understand-live-risk
python scripts/operator_boot.py sim
python scripts/operator_boot.py paper
python scripts/operator_boot.py ui-api --host 127.0.0.1 --port 8000
```

These are displayed as text/guidance. The API and dashboard do not execute them.

## Control Tower panel helper

The panel helper lives at:

```text
dashboard/auth_visibility_panel.py
```

It normalizes the API payload into a display-only model:

```text
read_only_panel=true
allowed_actions=[]
forbidden_actions=[login_mutation, token_write, token_display, broker_profile_probe, submit_order, modify_order, cancel_order, toggle_live]
```

## What this PR deliberately does not do

- no broker API calls
- no profile probe
- no API login endpoint
- no token write endpoint
- no raw token display
- no API secret display
- no dashboard buttons
- no order actions
- no live toggle
- no runtime worker start

## Acceptance proof

```bash
python -m pytest tests/test_auth_visibility_api.py tests/test_auth_visibility_panel.py -q
```

The tests prove:

- local-only sanitized visibility
- no raw token exposure
- no API secret exposure
- no broker/profile probes
- no token mutation
- GET-only route
- no mutation verbs in route paths
- panel exposes no allowed actions
