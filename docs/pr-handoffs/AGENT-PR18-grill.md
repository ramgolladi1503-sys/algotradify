# Grill Handoff — Agent PR 18

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR18",
  "role_id": "grill_reviewer",
  "workflow_state": "SCOPED_BY_SCOPE_OWNER",
  "target_state": "REVIEWED_BY_GRILL",
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
    "report could become fake green dashboard if failed sections are hidden",
    "report could overreach into non-governance behavior",
    "final PR could skip negative evidence tests"
  ],
  "tests_required": [
    "missing evidence blocks",
    "bad PR body blocks",
    "changed-file scope blocks",
    "renderers stay stable"
  ],
  "acceptance_gates": [
    "all sections are explicit",
    "overall status fails if any section fails",
    "safe flags preserved",
    "no product behavior added"
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
  "metadata": {"pr": "18", "scope": "grill review for architecture replay report"}
}
```
