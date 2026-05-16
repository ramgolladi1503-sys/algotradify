# Dry-Run Evidence Export Bundle

PR 31 adds a read-only dry-run evidence bundle endpoint.

PR 32 adds a read-only Control Tower preview for that bundle.

PR 36 adds explicit schema-version and compatibility guards for the export bundle contract.

## Endpoint

```text
GET /dry-run-execution/export
```

Supported query params match the dry-run preview endpoint:

- `limit`
- `min_quality_score`
- `now_epoch`

The export endpoint always uses preview behavior. It does not append files.

## Bundle shape

The response includes:

- `bundle_type`
- `schema_version`
- `created`
- `candidate_id`
- `dry_run_order_id`
- `dry_run_only`
- `is_order_action`
- `broker_api_called`
- `real_order_id`
- `status`
- `blockers`
- `warnings`
- `selected_candidate_snapshot`
- `execution_safety_snapshot`
- `approval_snapshot`
- `readiness_snapshot`
- `dry_run_intent`
- `lifecycle_event`
- `outcome_event`
- `export_preview_only`

## Schema versioning and compatibility

Current schema version:

```text
1.0
```

Current bundle type:

```text
DRY_RUN_EVIDENCE_BUNDLE
```

The route exposes these values through code-level constants:

- `DRY_RUN_EXPORT_BUNDLE_TYPE`
- `DRY_RUN_EXPORT_SCHEMA_VERSION`
- `DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS`
- `DRY_RUN_EXPORT_REQUIRED_KEYS`
- `DRY_RUN_EXPORT_SAFE_FLAGS`

The compatibility contract is available through:

```text
dry_run_export_schema_contract()
```

Compatible changes under schema `1.0`:

- adding optional nested fields inside existing snapshot objects
- adding new warning or blocker values
- adding non-breaking values inside `dry_run_intent`, `lifecycle_event`, or `outcome_event`
- improving descriptions, docs, or UI rendering without changing top-level keys

Breaking changes require a new schema version:

- removing or renaming any top-level key
- changing any safe flag semantics
- changing `bundle_type`
- changing `status` meanings for ready or blocked bundles
- changing snapshot field names at the top level
- allowing export preview to append files or perform order actions

The current compatible schema versions list is:

```text
1.0
```

Until a deliberate migration exists, tests must reject accidental schema drift.

## Control Tower Export Preview

The Control Tower frontend fetches:

```text
GET /dry-run-execution/export?limit=20
```

The preview is read-only. It is for operator visibility only and must not become an execution surface.

The frontend must not:

- call the export endpoint with `append=true`
- call broker APIs
- place live or paper orders
- expose submit, modify, cancel, or exit controls
- create server-side files from the preview

The preview displays:

- `bundle_type`
- `status`
- `candidate_id`
- `dry_run_order_id`
- `dry_run_only`
- `is_order_action`
- `broker_api_called`
- `real_order_id`
- `export_preview_only`
- selected, safety, approval, and readiness snapshots
- blockers and warnings

Expected preview flags:

```json
{
  "dry_run_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null,
  "export_preview_only": true
}
```

If any expected flag is unsafe, the UI should warn visually but still remain read-only.

## Safety boundary

The export endpoint is evidence-only.

It does not:

- call broker APIs
- create external execution connectivity
- create submit/modify/cancel/exit controls
- append JSONL artifacts
- place live or paper orders

The endpoint always returns:

```json
{
  "dry_run_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null,
  "export_preview_only": true
}
```

## Tests

Tests verify:

- bundle shape
- schema version remains `1.0`
- bundle type remains `DRY_RUN_EVIDENCE_BUNDLE`
- ready bundle for valid evidence
- blocked bundle for missing evidence
- direct app route mount
- no JSONL files are written by export preview
- schema contract constants match actual bundle output
- safe flags remain enforced by the route and bundle builder
- Control Tower fetches `/dry-run-execution/export?limit=20`
- Control Tower does not request `append=true`
- Control Tower exposes no submit/modify/cancel/exit execution controls for the export preview
- Control Tower displays the export preview safety flags, snapshots, blockers, and warnings
