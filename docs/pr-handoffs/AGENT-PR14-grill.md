# Grill Handoff — Agent PR 14

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR14",
  "role_id": "grill_reviewer",
  "workflow_state": "SCOPED_BY_SCOPE_OWNER",
  "target_state": "REVIEWED_BY_GRILL",
  "scope_decision": "APPROVED_WITH_STRICT_SCOPE",
  "files_allowed": [
    "agent_system/handoff_validator.py",
    "agent_system/__init__.py",
    "scripts/validate_agent_handoffs.py",
    "tests/test_agent_handoff_validator.py",
    "docs/agent-handoff-evidence-validator.md",
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
    "runtime_contract.py",
    ".github/workflows/"
  ],
  "risks_found": [
    "validator could accept malformed evidence",
    "validator could accidentally become a CI gate in PR14",
    "validator could rely on weak markdown-only evidence"
  ],
  "tests_required": [
    "missing files fail",
    "invalid payload fails",
    "task id mismatch fails",
    "role id mismatch fails",
    "missing JSON payload fails"
  ],
  "acceptance_gates": [
    "file-level validation exists",
    "validator uses PR13 artifact contract",
    "no GitHub Actions workflow is added",
    "no changed-file auditing is added"
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
    "pr": "14",
    "scope": "grill review for handoff validator"
  }
}
```
