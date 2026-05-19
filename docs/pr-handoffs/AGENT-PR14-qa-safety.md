# QA/Safety Handoff — Agent PR 14

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR14",
  "role_id": "qa_safety_reviewer",
  "workflow_state": "IMPLEMENTED_BY_GSD",
  "target_state": "REVIEWED_BY_QA_SAFETY",
  "scope_decision": "REVIEWED_SAFE_WITHIN_SCOPE",
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
    "validator must remain read-only",
    "validator must not inspect runtime or broker files",
    "validator must not become merge approval logic"
  ],
  "tests_required": [
    "unsafe safe flags fail",
    "task mismatch fails",
    "role mismatch fails",
    "missing file fails",
    "unknown role fails"
  ],
  "acceptance_gates": [
    "safe flags preserved",
    "no runtime imports added",
    "no protected product files touched",
    "report remains non-executing"
  ],
  "required_outputs": [
    "test_strength_review",
    "safety_boundary_review",
    "changed_file_review",
    "broker_live_order_boundary_review"
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
    "scope": "qa safety review for handoff validator"
  }
}
```
