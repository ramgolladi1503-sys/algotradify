# Hermes Handoff — Agent PR 17

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR17",
  "role_id": "hermes_architect",
  "workflow_state": "REVIEWED_BY_GRILL",
  "target_state": "DESIGNED_BY_HERMES",
  "scope_decision": "APPROVED_ARCHITECTURE",
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
    "local gate must not replace CI gate",
    "template validation must be deterministic",
    "PR18 architecture replay must remain separate"
  ],
  "tests_required": [
    "schema contract test",
    "template validation tests",
    "gate integration tests",
    "changed-file block test"
  ],
  "acceptance_gates": [
    "template added",
    "local gate CLI added",
    "PR gate tests added",
    "no architecture replay report added"
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
  "metadata": {"pr": "17", "scope": "hermes architecture for local developer gate"}
}
```
