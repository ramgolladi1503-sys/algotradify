# Grill Handoff — Agent PR 16

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR16",
  "role_id": "grill_reviewer",
  "workflow_state": "SCOPED_BY_SCOPE_OWNER",
  "target_state": "REVIEWED_BY_GRILL",
  "scope_decision": "APPROVED_WITH_STRICT_SCOPE",
  "files_allowed": [
    "agent_system/changed_file_auditor.py",
    "agent_system/__init__.py",
    "scripts/audit_agent_changed_files.py",
    "tests/test_agent_changed_file_auditor.py",
    ".github/workflows/agent-architecture-ci.yml",
    "docs/agent-changed-file-scope-auditor.md",
    "docs/pr-handoffs/",
    "PROJECT_STATE.md"
  ],
  "files_forbidden": [
    "api/",
    "frontend/",
    "dashboard/",
    "paper_trading/",
    "broker_contract/",
    "execution_safety/",
    "execution_readiness/",
    "strategies/",
    "movement_engine/",
    "top_selector/",
    "main.py",
    "run_live.sh",
    "runtime_contract.py"
  ],
  "risks_found": [
    "auditor can be too weak if it only checks one role",
    "auditor can be too broad if it enforces PR template before PR17",
    "forbidden file matches must override allowed matches"
  ],
  "tests_required": [
    "outside-approved-scope test",
    "forbidden-file test",
    "high-risk-without-approval test",
    "missing-scope-handoff test"
  ],
  "acceptance_gates": [
    "requires scope owner, Hermes, and GSD allow match",
    "blocks if any scope role forbids file",
    "preserves safe flags",
    "does not create PR template gate"
  ],
  "required_outputs": [
    "risks_found",
    "fake_progress_checks",
    "scope_drift_checks",
    "reject_conditions"
  ],
  "verdict": "APPROVED",
  "blockers": [],
  "warnings": [],
  "safe_flags": {
    "read_only": true,
    "is_order_action": false,
    "broker_api_called": false,
    "live_mode_touched": false,
    "allowed_for_live_execution": false,
    "real_order_id": null,
    "allowed_for_runtime_wiring": false,
    "allowed_for_broker_api": false
  },
  "metadata": {
    "pr": "16",
    "scope": "grill review for changed-file auditor"
  }
}
```
