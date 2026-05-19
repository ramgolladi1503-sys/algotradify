# QA/Safety Handoff — Agent PR 17

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR17",
  "role_id": "qa_safety_reviewer",
  "workflow_state": "IMPLEMENTED_BY_GSD",
  "target_state": "REVIEWED_BY_QA_SAFETY",
  "scope_decision": "REVIEWED_SAFE_WITHIN_SCOPE",
  "files_allowed": [
    "agent_system/pr_gate.py",
    "agent_system/__init__.py",
    "scripts/agent_pr_gate.py",
    "tests/test_agent_pr_gate.py",
    ".github/pull_request_template.md",
    ".github/workflows/agent-architecture-ci.yml",
    "docs/agent-pr-developer-gate.md",
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
    "local gate must stay read-only",
    "template checks must not hide missing evidence",
    "architecture report must remain PR18 scope"
  ],
  "tests_required": [
    "invalid body block test",
    "missing evidence block test",
    "changed file block test",
    "safe flag preservation test"
  ],
  "acceptance_gates": [
    "read-only gate report",
    "no execution behavior",
    "no architecture replay report",
    "no product behavior"
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
  "metadata": {"pr": "17", "scope": "qa safety review for local developer gate"}
}
```
