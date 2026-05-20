# Hermes Handoff — Agent PR 18

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR18",
  "role_id": "hermes_architect",
  "workflow_state": "REVIEWED_BY_GRILL",
  "target_state": "DESIGNED_BY_HERMES",
  "scope_decision": "APPROVED_ARCHITECTURE",
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
    "report aggregation must be deterministic",
    "markdown and json renderers must not mutate state",
    "final governance completion must be evidence-backed"
  ],
  "tests_required": [
    "schema contract test",
    "green report test",
    "section failure tests",
    "renderer stability test"
  ],
  "acceptance_gates": [
    "report includes six governance sections",
    "report fails if any section fails",
    "CLI supports json and markdown",
    "no execution behavior added"
  ],
  "required_outputs": [
    "architecture_decision",
    "contract_boundaries",
    "files_to_change",
    "files_not_to_touch",
    "acceptance_gates"
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
  "metadata": {"pr": "18", "scope": "hermes architecture for replay report"}
}
```
