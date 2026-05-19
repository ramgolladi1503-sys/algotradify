# Scope Owner Handoff — Agent PR 14

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR14",
  "role_id": "scope_owner",
  "workflow_state": "REQUESTED",
  "target_state": "SCOPED_BY_SCOPE_OWNER",
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
    "validator accidentally becomes CI gate",
    "validator accidentally audits changed files",
    "validator accepts incomplete handoff evidence"
  ],
  "tests_required": [
    "missing handoff file fails",
    "invalid payload fails",
    "task mismatch fails",
    "role mismatch fails",
    "unsafe safe flags fail",
    "subset validation works"
  ],
  "acceptance_gates": [
    "repo-local validator only",
    "no CI workflow added",
    "no changed-file auditor added",
    "safe flags preserved"
  ],
  "required_outputs": [
    "task_boundary",
    "files_allowed",
    "files_forbidden",
    "non_goals",
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
    "scope": "handoff evidence validator only"
  }
}
```
