# Scope Owner Handoff — Agent PR 17

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR17",
  "role_id": "scope_owner",
  "workflow_state": "REQUESTED",
  "target_state": "SCOPED_BY_SCOPE_OWNER",
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
    "local gate could become PR18 audit report early",
    "template could miss required evidence sections",
    "changed-file audit could be bypassed locally"
  ],
  "tests_required": [
    "valid body passes",
    "invalid body blocks",
    "missing handoff evidence blocks",
    "changed file outside scope blocks",
    "json-safe report test"
  ],
  "acceptance_gates": [
    "PR template updated",
    "local gate added",
    "CLI added",
    "no architecture replay report added"
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
  "metadata": {"pr": "17", "scope": "pr template and local developer gate only"}
}
```
