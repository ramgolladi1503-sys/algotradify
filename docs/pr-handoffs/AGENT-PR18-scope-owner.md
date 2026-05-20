# Scope Owner Handoff — Agent PR 18

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR18",
  "role_id": "scope_owner",
  "workflow_state": "REQUESTED",
  "target_state": "SCOPED_BY_SCOPE_OWNER",
  "scope_decision": "APPROVED_WITH_STRICT_SCOPE",
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
    "report could accidentally become product behavior",
    "report could hide failed sections",
    "final wave completion could be claimed without fail-closed tests"
  ],
  "tests_required": [
    "green replay report test",
    "missing handoff evidence failure test",
    "invalid PR body failure test",
    "changed-file scope failure test",
    "json and markdown renderer test"
  ],
  "acceptance_gates": [
    "architecture replay report added",
    "report aggregates governance layers",
    "report fails when any section fails",
    "no product behavior added"
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
  "metadata": {"pr": "18", "scope": "architecture replay report only"}
}
```
