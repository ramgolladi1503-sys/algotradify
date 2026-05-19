# QA/Safety Handoff — Agent PR 18

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR18",
  "role_id": "qa_safety_reviewer",
  "workflow_state": "IMPLEMENTED_BY_GSD",
  "target_state": "REVIEWED_BY_QA_SAFETY",
  "scope_decision": "REVIEWED_SAFE_WITHIN_SCOPE",
  "files_allowed": [
    "agent_system/architecture_replay.py",
    "agent_system/__init__.py",
    "scripts/architecture_replay_report.py",
    "tests/test_agent_architecture_replay.py",
    ".github/workflows/agent-architecture-ci.yml",
    "docs/agent-architecture-replay-report.md",
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
    "report must stay read-only",
    "report must preserve safe flags",
    "report must not add product behavior"
  ],
  "tests_required": [
    "safe flag preservation test",
    "section failure tests",
    "renderer stability test",
    "governance CI inclusion test"
  ],
  "acceptance_gates": [
    "read-only report",
    "no product behavior",
    "no runtime behavior",
    "no hidden section failures"
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
  "metadata": {"pr": "18", "scope": "qa safety review for architecture replay report"}
}
```
