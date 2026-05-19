# GSD Handoff — Agent PR 17

```json
{
  "schema_version": 1,
  "contract": "agent_role_handoff_artifact_v1",
  "task_id": "AGENT-PR17",
  "role_id": "gsd_implementer",
  "workflow_state": "DESIGNED_BY_HERMES",
  "target_state": "IMPLEMENTED_BY_GSD",
  "scope_decision": "IMPLEMENTED_WITHIN_SCOPE",
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
    "local gate can be misread as final audit report",
    "CLI must fail closed when changed files are missing",
    "PR body checks must stay explicit"
  ],
  "tests_required": [
    "green path local gate test",
    "invalid PR body test",
    "missing evidence test",
    "outside scope changed file test",
    "JSON safe report test"
  ],
  "acceptance_gates": [
    "pr_gate core added",
    "agent_pr_gate CLI added",
    "PR template hardened",
    "CI runs PR gate tests"
  ],
  "required_outputs": [
    "patch_summary",
    "changed_files",
    "tests_added",
    "test_commands",
    "implementation_boundary"
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
  "metadata": {"pr": "17", "scope": "gsd implementation for local developer gate"}
}
```
