# Grill Handoff — Agent PR 17

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR17",
  "role_id": "grill_reviewer",
  "workflow_state": "SCOPED_BY_SCOPE_OWNER",
  "target_state": "REVIEWED_BY_GRILL",
  "scope_decision": "APPROVED_WITH_STRICT_SCOPE",
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
    "template-only enforcement can become theatre",
    "local gate must actually combine body, architecture, and changed-file checks",
    "PR17 must not build PR18 architecture report early"
  ],
  "tests_required": [
    "required sections test",
    "required phrases test",
    "gate green path test",
    "invalid body block test",
    "outside scope block test"
  ],
  "acceptance_gates": [
    "local gate combines three checks",
    "template includes required sections",
    "CI includes PR gate tests",
    "no PR18 report added"
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
  "metadata": {"pr": "17", "scope": "grill review for local developer gate"}
}
```
