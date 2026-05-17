# Replay Contract Health Badge

PR 50 adds a read-only replay contract health badge to the Control Tower.

## Goal

Surface the replay contract documentation, tests, and fixtures directly in the Control Tower without adding a backend health endpoint.

This builds on:

- PR 49: Replay Contract Documentation Index

## UI surface

The badge is rendered in:

```text
frontend/main.jsx
```

Component:

```text
ReplayContractHealthBadge
```

Static registry:

```text
REPLAY_CONTRACT_HEALTH
```

## What it shows

The badge displays:

- contract status
- replay contract index document
- read-only flag
- doc count
- test count
- fixture count
- static registry source
- replay contract docs
- replay contract tests
- replay fixture files

## Why it is static

The badge intentionally uses a frontend static registry.

Portfolio CI proves the listed files exist.

This avoids adding backend filesystem reads or a new health endpoint just to show documentation coverage.

## Safety boundary

This is a read-only UI documentation-health surface.

It does not add:

- backend route behavior
- broker API calls
- real order placement
- order-management UI
- approval controls
- JSONL append behavior
- runtime mutation
- live or paper execution adapters

## Tests

Relevant test file:

```text
tests/test_replay_contract_health_badge.py
```

The tests verify:

- badge title and static registry exist
- replay docs/tests/fixtures are listed
- badge is read-only
- no forbidden execution labels are introduced
- replay contract index doc exists
