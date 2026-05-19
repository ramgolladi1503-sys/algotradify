# Runtime Correction PR 6 — Grill Review

## Scope under review

Runtime Correction PR 6 — Native run_live / Operator Boot Commands.

This PR may add guarded operator startup commands only.

## Hard challenge

The dangerous mistake is creating a convenient command that starts LIVE accidentally.

Root `run_live.sh` must not start anything by default. LIVE startup must require explicit confirmation.

## Required proof

The PR must prove:

1. `./run_live.sh` requires exactly one action
2. LIVE startup requires `--start --i-understand-live-risk`
3. `DRY_RUN=true` blocks LIVE startup
4. `python scripts/operator_boot.py sim` uses SIM mode
5. `python scripts/operator_boot.py paper` uses PAPER mode
6. `python scripts/operator_boot.py ui-api` starts API only
7. no frontend/dashboard controls are added
8. no broker order behavior is added

## Rejection conditions

Reject this PR if any of these happen:

- `./run_live.sh` starts LIVE without explicit confirmation
- LIVE becomes the default anywhere
- API/frontend/dashboard controls are added
- broker order behavior is added
- auth API endpoints are added
- paper/agent internals are modified
- strategy provider behavior changes

## Grill verdict

Approved only as guarded operator boot command PR.
