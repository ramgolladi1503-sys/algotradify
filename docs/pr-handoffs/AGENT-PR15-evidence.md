# Evidence Handoff — Agent PR 15

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR15",
  "role_id": "evidence_recorder",
  "workflow_state": "REVIEWED_BY_QA_SAFETY",
  "target_state": "EVIDENCE_RECORDED",
  "scope_decision": "EVIDENCE_RECORDED",
  "files_allowed": [
    "agent_system/architecture_gate.py",
    "agent_system/__init__.py",
    "scripts/run_agent_architecture_gate.py",
    "tests/test_agent_architecture_gate.py",
    ".github/workflows/agent-architecture-ci.yml",
    "docs/agent-architecture-ci-gate.md",
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
    "CI execution proof will be produced by GitHub after PR opens",
    "manual local execution is not available inside the repo patching path"
  ],
  "tests_required": [
    "python -m pytest tests/test_agent_architecture_gate.py -q",
    "python -m pytest tests/test_agent_role_registry.py tests/test_agent_workflow_state.py tests/test_agent_handoff_contract.py tests/test_agent_handoff_validator.py tests/test_agent_architecture_gate.py -q",
    "python scripts/run_agent_architecture_gate.py --task-ref AGENT-PR15 --json"
  ],
  "acceptance_gates": [
    "workflow added",
    "gate runner added",
    "handoff evidence validates",
    "no changed-file auditor added"
  ],
  "required_outputs": [
    "commands_run",
    "test_results",
    "acceptance_proof",
    "safety_boundary",
    "reject_conditions"
  ],
  "verdict": "APPROVED_WITH_WARNINGS",
  "blockers": [],
  "warnings": [
    "CI must provide final command execution proof"
  ],
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
    "pr": "15",
    "scope": "evidence record for ci gate"
  }
}
```
