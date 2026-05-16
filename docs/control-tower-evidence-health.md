# Control Tower Evidence Health Panel

PR 40 adds a read-only evidence health endpoint and Control Tower panel.

## Endpoint

```text
GET /evidence-health?limit=20
```

The endpoint is mounted through the existing dry-run route installer and uses the evidence integrity validators from:

```text
api/evidence_integrity.py
```

## Purpose

The endpoint validates evidence payloads against the evidence schema registry and returns a compact integrity summary for operators.

It reports:

- `status`
- `evidence_health_only`
- `dry_run_only`
- `is_order_action`
- `broker_api_called`
- `real_order_id`
- `schema_count`
- `valid_count`
- `invalid_count`
- `warning_count`
- `missing_key_count`
- `safe_flag_violation_count`
- per-schema integrity `results`

Each schema result includes:

- `valid`
- `schema_id`
- `missing_keys`
- `safe_flag_violations`
- `warnings`

## Control Tower panel

The frontend fetches:

```text
/evidence-health?limit=20
```

The Control Tower renders this as:

```text
Evidence Health Panel
```

The panel shows:

- safe boundary flags
- schema counts
- invalid evidence counts
- missing keys
- safe flag violations
- warnings
- per-schema details

## Safety boundary

This is read-only evidence health.

It does not:

- call broker APIs
- place real orders
- submit/modify/cancel/exit orders
- approve orders
- append JSONL artifacts
- expose execution controls
- change live/paper execution behavior

The endpoint always exposes the no-order boundary:

```json
{
  "evidence_health_only": true,
  "dry_run_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null
}
```

## Tests

Relevant tests:

```text
tests/test_evidence_health_api.py
tests/test_dry_run_execution_api_direct_mount.py
tests/test_control_tower_ui.py
```

They verify:

- `/evidence-health` exists
- endpoint writes no JSONL files
- endpoint exposes safe flags
- degraded integrity is reported when evidence is missing
- safe flag violations are counted
- Control Tower fetches `/evidence-health?limit=20`
- Control Tower exposes no execution controls
