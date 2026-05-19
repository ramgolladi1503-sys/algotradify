# Hermes Handoff — Agent PR 15

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR15",
  "role_id": "hermes_architect",
  "workflow_state": "REVIEWED_BY_GRILL",
  "target_state": "DESIGNED_BY_HERMES",
  "scope_decision": "APPROVED_ARCHITECTURE",
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
    "architecture gate may be confused with full architecture audit",
    "workflow task id parsing must fail closed",
    "CI must stay focused on governance contracts only"
  ],
  "tests_required": [
    "schema contract exposes required checks",
    "task id parsing accepts PR title",
    "missing handoff evidence blocks",
    "invalid handoff evidence blocks"
  ],
  "acceptance_gates": [
    "workflow file added",
    "gate runner added",
    "governance test set runs",
    "no changed-file auditor included"
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
  "metadata": {
    "pr": "15",
    "scope": "hermes architecture for ci gate"
  }
}
```
