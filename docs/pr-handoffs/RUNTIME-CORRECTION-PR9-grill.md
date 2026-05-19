# Runtime Correction PR 9 — Grill Review

## Scope under review

Runtime Correction PR 9 — Compatibility Cleanup and External Runtime Deprecation.

This PR may deprecate external runtime fallback and disable silent external fallback by default.

## Hard challenge

The dangerous mistake is breaking emergency compatibility without proof or silently keeping fallback behavior alive.

The correct middle ground:

- native repo root is default
- external fallback is disabled by default
- external fallback remains available only through explicit temporary opt-in
- preflight and ownership visibility clearly report deprecation

## Required proof

The PR must prove:

1. external fallback is disabled by default
2. configured external env roots are ignored by default
3. native repo root remains default when native markers exist
4. strict native mode still blocks external fallback
5. explicit `ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true` keeps temporary compatibility
6. preflight reports external fallback deprecation metadata
7. runtime ownership API exposes deprecation fields
8. no root startup/operator/API/auth/order behavior is expanded

## Rejection conditions

Reject this PR if any of these happen:

- root `main.py` changes
- root `run_live.sh` changes
- operator boot commands change
- broker/auth/order behavior is added
- dashboard action controls are added
- paper/agent internals are changed
- external fallback still works silently by default
- explicit external opt-in is removed before PR 10
- LIVE becomes default

## Grill verdict

Approved only as external runtime deprecation with explicit temporary compatibility opt-in.
