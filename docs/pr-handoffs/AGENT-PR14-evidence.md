# Evidence Handoff — Agent PR 14

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR14",
  "role_id": "evidence_recorder",
  "workflow_state": "REVIEWED_BY_QA_SAFETY",
  "target_state": "EVIDENCE_RECORDED",
  "scope_decision": "EVIDENCE_RECORDED",
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
    "manual test execution not available inside this PR creation path",
    "CI still owns final execution proof",
    "validator evidence should remain separate from PR15 CI gate"
  ],
  "tests_required": [
    "python -m pytest tests/test_agent_handoff_validator.py -q",
    "python -m pytest tests/test_agent_handoff_validator.py tests/test_agent_handoff_contract.py tests/test_agent_workflow_state.py tests/test_agent_role_registry.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q",
    "python scripts/validate_agent_handoffs.py --task-id AGENT-PR14 --json"
  ],
  "acceptance_gates": [
    "handoff files validate",
    "validator tests pass",
    "no CI workflow added",
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
    "test commands listed for CI/local execution"
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
    "pr": "14",
    "scope": "evidence record for handoff validator"
  }
}
```
