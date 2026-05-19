# Runtime Correction PR 4 — Grill Review

## Scope under review

Runtime Correction PR 4 — Native Runtime Contract and Preflight Hardening.

This PR may harden runtime contract/preflight behavior only. It must not promote root `main.py`, promote root `run_live.sh`, change API/frontend/paper/agent behavior, or add auth/live/broker behavior.

## Hard challenge

The dangerous mistake would be switching normal runtime boot resolution to repo root while root `main.py` is still a wrapper. That can cause recursive self-loading.

Therefore PR 4 must support strict native preflight proof, but preserve normal wrapper boot behavior until Runtime Correction PR 5.

## Required proof

The PR must prove:

1. native source markers are detected
2. ownership is `NATIVE_SOURCE_IMPORTED_PENDING_MAIN_PROMOTION` while root `main.py` remains wrapper
3. ownership becomes `NATIVE` only after a promoted native-style root `main.py` fixture
4. strict native mode selects repo root only when native markers exist
5. strict native mode blocks env/sibling/home external fallbacks
6. missing native markers fail closed in strict native mode
7. runtime artifact root resolves to repo `.runtime` for strict native source
8. default behavior remains wrapper-compatible until PR 5

## Rejection conditions

Reject this PR if any of these happen:

- root `main.py` is replaced
- root `run_live.sh` is promoted
- API/frontend/paper/agent code is changed
- broker calls are added
- auth behavior is added
- LIVE behavior is added
- normal runtime boot points at repo root before PR 5
- strict native mode still allows external env roots
- tests hide WARN state as PASS before main promotion

## Grill verdict

Approved only as preflight/native-contract hardening.
