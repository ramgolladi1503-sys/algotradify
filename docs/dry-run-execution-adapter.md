# Dry-Run Execution Adapter

PR 24 adds a local simulation adapter for execution evidence.

## Purpose

The adapter turns an already selected high-quality candidate into local evidence that can be reviewed and replayed. It is intentionally separated from any external execution path.

## Inputs consumed

The adapter consumes three existing contract outputs:

1. top executable selection
2. execution safety decision
3. approval audit summary

It can also attach the matching execution-readiness snapshot for traceability.

## Output artifacts

When the adapter succeeds, it creates:

- `DryRunOrderIntent`
- `DryRunLifecycleEvent`
- replay-compatible outcome event

Every created object exposes:

```json
{
  "dry_run_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null
}
```

## Validation blockers

The adapter blocks creation when:

- no selected candidate exists
- selected candidate has an unsafe action flag
- execution safety is missing
- execution safety is not permitted
- execution safety action flag is unsafe
- approval evidence is missing
- approval status is not approved
- approval action flag is unsafe
- candidate id is missing
- approval candidate id does not match selected candidate id
- approval safety snapshot is unsafe

## Persistence

The adapter is preview-first. Calling `build_dry_run_execution(...)` writes nothing.

Calling `append_dry_run_execution(...)` writes append-only JSONL evidence under the supplied runtime root:

- `logs/dry_run_order_intents.jsonl`
- `logs/dry_run_lifecycle.jsonl`
- `logs/outcome_replay.jsonl`

No existing artifact is overwritten.

## Safety boundary

This PR adds local evidence only. It does not add external execution connectivity, mutation controls, or a real execution adapter.

## Current limitation

The backend adapter and unit tests are implemented. API route wiring is intentionally left as a follow-up if the server file update is blocked by the repository write connector. The expected endpoint remains:

```text
GET /dry-run-execution
```

with preview behavior by default and append-only persistence only when explicitly requested.
