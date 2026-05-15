# CI Test Suite Map

Algotradify uses focused GitHub Actions lanes instead of relying on one opaque test command.

## Lanes

### Portfolio CI

Broad repository gate. Validates required portfolio files, README sections, and the full curated test set.

### Core Unit CI

Runs pure backend unit tests for:

- runtime contract
- runtime preflight
- strategy registry
- candidate truth
- opportunity layer
- broker contract resolver/readiness
- market readiness
- execution readiness
- evidence wiring
- trade quality
- top executable selector

### Lifecycle and Safety CI

Runs lifecycle and safety tests for:

- fill lifecycle
- outcome replay
- execution safety
- approval audit
- approval creation

### API Contract CI

Runs endpoint, schema, and websocket contract tests.

### Dry-Run Execution CI

Runs the dry-run adapter and dry-run API mount tests.

### Frontend Contract CI

Runs static Control Tower contract tests, including dry-run visibility and append-safety checks.

## Why this split exists

The repo previously used a large hardcoded pytest list inside Portfolio CI. That worked, but failures were harder to read. The new lanes make failures easier to diagnose without removing the broad portfolio gate.

## Important boundary

These CI lanes are offline/safe tests. They do not require broker secrets, market sessions, or live execution connectivity.
