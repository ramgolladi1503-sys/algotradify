# Grill Handoff — Agent PR 15

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR15",
  "role_id": "grill_reviewer",
  "workflow_state": "SCOPED_BY_SCOPE_OWNER",
  "target_state": "REVIEWED_BY_GRILL",
  "scope_decision": "APPROVED_WITH_STRICT_SCOPE",
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
    "workflow can become noisy if it runs broad tests",
    "gate can be bypassed if PR title has no task id",
    "scope creep into PR16 or PR17 would break locked order"
  ],
  "tests_required": [
    "architecture gate schema test",
    "task id resolution test",
    "missing evidence failure test",
    "invalid evidence failure test"
  ],
  "acceptance_gates": [
    "CI gate validates role registry",
    "CI gate validates workflow state machine",
    "CI gate validates handoff evidence",
    "CI gate excludes changed-file audit"
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
    "pr": "15",
    "scope": "grill review for ci architecture gate"
  }
}
```
