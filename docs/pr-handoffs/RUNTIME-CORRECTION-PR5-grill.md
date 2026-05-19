# Runtime Correction PR 5 — Grill Review

## Scope under review

Runtime Correction PR 5 — Root Native `main.py` Promotion.

This PR may replace root `main.py` with the native runtime boot flow and update runtime contract/tests/docs accordingly.

## Hard challenge

The dangerous mistake is deleting safety-critical boot behavior while removing the wrapper.

PR 5 must not rewrite a simplified entrypoint. It must preserve native Tradebot startup controls:

- runtime guard import side effects
- config loading
- runtime mode/config alignment
- runtime directory initialization
- event log validation/repair
- Kite startup credential validation
- LIVE/PAPER instance locking
- database readiness guard
- startup security enforcement
- trade log initialization
- stale risk halt auto-clear
- readiness gate handling
- orchestrator startup
- reconciliation daemon lifecycle
- broker truth reconciler lifecycle

## Required proof

The PR must prove:

1. root `main.py` no longer uses dynamic external loader markers
2. root `main.py` preserves safety-critical startup imports and calls
3. runtime ownership becomes `NATIVE`
4. default runtime resolution prefers repo root after promotion
5. root `run_live.sh` is still not promoted
6. API/frontend/paper/agent layers are untouched

## Rejection conditions

Reject this PR if any of these happen:

- root `run_live.sh` is promoted
- API/frontend/paper/agent behavior changes
- broker order behavior is added
- auth endpoints are added
- LIVE becomes default
- startup auth/security/readiness/lock checks are removed
- dynamic external loader remains in root `main.py`

## Grill verdict

Approved only as root native main promotion with safety-preserving tests.
