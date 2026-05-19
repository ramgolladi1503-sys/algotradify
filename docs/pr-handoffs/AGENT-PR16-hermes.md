# Hermes Handoff — Agent PR 16

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR16",
  "role_id": "hermes_architect",
  "workflow_state": "REVIEWED_BY_GRILL",
  "target_state": "DESIGNED_BY_HERMES",
  "scope_decision": "APPROVED_ARCHITECTURE",
  "files_allowed": [
    "agent_system/changed_file_auditor.py",
    "agent_system/__init__.py",
    "scripts/audit_agent_changed_files.py",
    "tests/test_agent_changed_file_auditor.py",
    ".github/workflows/agent-architecture-ci.yml",
    "docs/agent-changed-file-scope-auditor.md",
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
    "scope matching must be deterministic",
    "auditor must not depend on git state in PR16",
    "high-risk approval must be explicit input"
  ],
  "tests_required": [
    "path normalization tests",
    "allowed-by-all-roles test",
    "forbidden-by-any-role test",
    "json-safe report test"
  ],
  "acceptance_gates": [
    "changed files are compared with approved handoff scope",
    "unsafe paths fail closed",
    "missing changed files fail closed",
    "no architecture report added"
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
    "pr": "16",
    "scope": "hermes architecture for changed-file auditor"
  }
}
```
