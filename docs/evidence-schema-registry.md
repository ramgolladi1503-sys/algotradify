# Evidence Schema Registry

PR 37 introduces a central evidence schema registry.

The registry lives at:

```text
api/evidence_schema_registry.py
```

## Purpose

The registry makes evidence contracts discoverable and stable instead of scattered across route code, UI assumptions, and tests.

It is not an execution layer.

It does not:

- call broker APIs
- create real orders
- add submit/modify/cancel/exit controls
- change frontend behavior
- change dry-run export behavior

## Registered schema contracts

The registry currently includes:

- `dry_run_export_bundle`
- `dry_run_execution_payload`
- `execution_safety_decision`
- `approval_evidence`
- `readiness_snapshot`
- `lifecycle_event`
- `outcome_replay_event`

Each schema contract exposes:

- `schema_id`
- `evidence_type`
- `schema_version`
- `compatible_schema_versions`
- `required_keys`
- `safe_flags`
- `description`

## Source of truth rule

For dry-run export bundles, the registry must match the route-level export contract from:

```text
dry_run_export_schema_contract()
```

The test suite verifies this so the registry cannot drift from the actual export bundle contract.

## Safety boundary

Evidence schemas may document safe flags such as:

```json
{
  "dry_run_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null,
  "export_preview_only": true
}
```

These flags are contract metadata. They do not authorize execution.

## Compatibility rule

Compatible changes:

- adding optional nested fields
- expanding warnings or blockers
- improving descriptions
- adding a new schema entry without changing existing schema IDs

Breaking changes:

- removing or renaming required keys
- changing safe flag semantics
- changing schema IDs
- changing schema version without migration tests
- weakening no-order/no-broker guarantees

## Tests

Registry tests live in:

```text
tests/test_evidence_schema_registry.py
```

They verify:

- expected schema IDs exist
- schema contracts are discoverable
- schema versions remain stable
- dry-run export registry contract matches the route contract
- safe flags preserve no-order boundaries
- unknown schema IDs fail clearly
