# Runtime Ownership Audit

## Purpose

This document supports Runtime Correction PR 1 — Runtime Ownership Audit.

The goal is to make algotradify's current runtime ownership state explicit before any source import, `main.py` replacement, run-script migration, API wiring, auth visibility, or compatibility cleanup begins.

This PR is audit-only.

## Why this exists

Algotradify has built useful product layers around the runtime, but the runtime ownership boundary is still not strict enough.

The current implementation can behave as a runtime launcher/bridge instead of a fully native runtime owner. That means the product can appear operational while still relying on an embedded or external Tradebot-compatible runtime.

That ambiguity must be corrected before continuing normal product PRs.

## What the audit checks

`scripts/audit_runtime_ownership.py` checks only source files and path markers.

It reports:

- whether root `main.py` exists
- whether root `main.py` looks like a wrapper/launcher
- whether root `core/` exists
- whether root `config/` exists
- whether root `strategies/` exists
- whether `core_bot` contains a runtime-like shape
- whether external runtime fallback markers exist
- whether normal feature PRs should pause
- safe flags proving this is read-only/audit-only

## What the audit does not do

The audit does not:

- start the bot
- import runtime modules
- create runtime directories
- call broker APIs
- validate Kite credentials
- modify runtime files
- modify API/frontend/paper/agent behavior
- import Tradebot source
- replace root `main.py`

## Expected current result

Before the native migration is complete, the expected posture is:

```text
runtime_ownership=WRAPPER_OR_EXTERNAL_COMPATIBLE
normal_feature_prs_should_pause=true
safe_to_continue_feature_prs=false
```

If the audit later reports `NATIVE`, that must be backed by tests proving:

```text
root main.py is native runtime boot
root core/ is present
root config/ is present
external runtime fallback is disabled by default
```

## Commands

```bash
python scripts/audit_runtime_ownership.py --json
python -m pytest tests/test_runtime_ownership_audit.py -q
```

## Safety boundary

This audit is intentionally read-only:

```json
{
  "read_only": true,
  "audit_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null,
  "live_mode_touched": false
}
```

## Why normal feature PRs should pause

Normal feature PRs should pause while runtime ownership is unresolved because additional product layers may keep passing tests without proving which runtime code is actually running.

Two concrete risks:

1. A Control Tower panel can display runtime evidence while the source of that evidence is still external or ambiguous.
2. Auth/startup work can be bolted onto wrapper behavior instead of the real native bot runtime.

This PR does not fix those issues. It only makes them visible.

## Acceptance proof

Runtime Correction PR 1 is acceptable only if:

- the audit script exists
- the audit tests exist
- the audit is read-only
- wrapper/external-compatible posture is detected correctly
- native posture is detected correctly in test fixtures
- no runtime behavior changes are introduced

## Next PR

Runtime Correction PR 2 — Tradebot Source Import Manifest and Collision Report.
