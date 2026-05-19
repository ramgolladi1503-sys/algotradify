# Scope Owner Handoff — Agent PR 15

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR15",
  "role_id": "scope_owner",
  "workflow_state": "REQUESTED",
  "target_state": "SCOPED_BY_SCOPE_OWNER",
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
    "CI gate could accidentally include changed-file auditing before PR16",
    "CI gate could enforce PR template before PR17",
    "CI gate could fail if task id resolution is weak"
  ],
  "tests_required": [
    "task id resolution tests",
    "green gate test",
    "missing handoff evidence failure test",
    "invalid handoff evidence failure test",
    "safe flags test"
  ],
  "acceptance_gates": [
    "CI workflow runs governance tests",
    "CI workflow runs architecture gate from PR title",
    "no changed-file auditor added",
    "no PR template gate added"
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
    "pr": "15",
    "scope": "ci architecture gate only"
  }
}
```
