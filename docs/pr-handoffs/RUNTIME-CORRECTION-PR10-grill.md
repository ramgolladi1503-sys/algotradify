# Runtime Correction PR 10 — Grill Review

## Scope under review

Runtime Correction PR 10 — Full Regression Gate and Migration Lock.

This PR may add a deterministic migration lock checker, tests, docs, and handoff evidence only.

## Hard challenge

The dangerous mistake is treating the final PR as permission to add one more feature.

PR 10 must not add runtime behavior. It must freeze the corrected boundaries:

- native root runtime ownership
- guarded live startup
- safe SIM/PAPER/API-only operator commands
- external fallback deprecated and disabled by default
- runtime/auth visibility read-only
- Control Tower helpers actionless
- no committed runtime/secret artifacts

## Required proof

The PR must prove:

1. migration lock checker passes current repo
2. checker fails when root `main.py` reintroduces dynamic loader markers
3. checker fails when `run_live.sh` loses explicit confirmation gate
4. checker fails when operator boot adds LIVE command
5. checker fails when visibility routes add mutation methods
6. checker fails when known token artifacts are committed
7. checker reports read-only safe flags
8. no protected runtime/auth/order/UI behavior is changed

## Rejection conditions

Reject this PR if any of these happen:

- root `main.py` behavior changes
- root `run_live.sh` behavior changes
- operator boot behavior changes
- broker API/order behavior is added
- auth mutation is added
- dashboard action controls are added
- paper/agent internals are changed
- LIVE becomes default
- checker is weak shape-only and does not fail on injected regressions

## Grill verdict

Approved only as final read-only migration lock and regression gate.
