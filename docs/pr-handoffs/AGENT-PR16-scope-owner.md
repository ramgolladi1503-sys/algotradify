# Scope Owner Handoff — Agent PR 16

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR16",
  "role_id": "scope_owner",
  "workflow_state": "REQUESTED",
  "target_state": "SCOPED_BY_SCOPE_OWNER",
  "scope_decision": "APPROVED_WITH_STRICT_SCOPE",
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
    "auditor could become PR template gate before PR17",
    "auditor could become architecture report before PR18",
    "high-risk paths need explicit human approval"
  ],
  "tests_required": [
    "allowed files pass with approval",
    "outside scope blocks",
    "forbidden path blocks",
    "high-risk path requires approval",
    "missing handoff scope blocks"
  ],
  "acceptance_gates": [
    "changed-file auditor only",
    "CLI added",
    "governance CI includes auditor tests only",
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
    "pr": "16",
    "scope": "changed-file scope auditor only"
  }
}
```
