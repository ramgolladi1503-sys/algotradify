# Hermes Handoff — Agent PR 14

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR14",
  "role_id": "hermes_architect",
  "workflow_state": "REVIEWED_BY_GRILL",
  "target_state": "DESIGNED_BY_HERMES",
  "scope_decision": "APPROVED_ARCHITECTURE",
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
    "fenced JSON extraction can be fragile",
    "required role set can drift from role registry",
    "validator can become too broad before PR15 and PR16"
  ],
  "tests_required": [
    "valid required handoffs pass",
    "missing handoff file fails",
    "invalid payload fails",
    "mismatched task id fails",
    "mismatched role id fails",
    "unsafe task id fails"
  ],
  "acceptance_gates": [
    "single task validation only",
    "uses PR13 normalize_agent_handoff_artifact",
    "CLI exits nonzero for invalid evidence",
    "no CI workflow added"
  ],
  "required_outputs": [
    "architecture_decision",
    "contract_boundaries",
    "files_to_change",
    "files_not_to_touch",
    "acceptance_gates"
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
    "scope": "hermes architecture for handoff validator"
  }
}
```
