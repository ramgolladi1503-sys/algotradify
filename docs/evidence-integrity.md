# Runtime Evidence Integrity Checks

PR 39 adds pure validation helpers for checking evidence payloads against the evidence schema registry.

The helpers live at:

```text
api/evidence_integrity.py
```

## Purpose

Evidence integrity checks catch broken evidence before it contaminates replay, export, analytics, or Control Tower display.

They validate:

- required keys
- safe flags
- schema version compatibility warnings
- evidence type mismatch warnings

They return structured results and do not mutate runtime state.

## Public helpers

```text
validate_evidence_payload(schema_id, payload)
validate_evidence_payload_against_schema(schema, payload)
validate_many_evidence_payloads(items)
```

The result object is:

```text
EvidenceIntegrityResult
```

It exposes:

- `valid`
- `schema_id`
- `missing_keys`
- `safe_flag_violations`
- `warnings`

## Example result

```json
{
  "valid": false,
  "schema_id": "dry_run_export_bundle",
  "missing_keys": ["dry_run_intent"],
  "safe_flag_violations": [
    {
      "key": "broker_api_called",
      "expected": false,
      "actual": true
    }
  ],
  "warnings": []
}
```

## Safety boundary

Integrity checks are not execution permission.

They do not:

- call broker APIs
- create real orders
- submit/modify/cancel/exit orders
- approve orders
- mutate files
- append JSONL artifacts
- change frontend behavior
- change backend route behavior

They are pure validation helpers.

## Warning semantics

Warnings do not currently make `valid=false`.

Examples:

- incompatible `schema_version`
- mismatched `bundle_type` or `evidence_type`

Missing required keys and safe flag violations make `valid=false`.

## Tests

Tests live in:

```text
tests/test_evidence_integrity.py
```

They cover:

- valid export bundle
- missing keys
- unsafe flag violations
- incompatible schema version warnings
- wrong evidence type warnings
- non-dict payloads
- batch validation
- unknown schema ID handling
