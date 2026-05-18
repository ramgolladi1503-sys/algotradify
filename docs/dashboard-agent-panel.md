# Dashboard Agent Panel

Status: Agent PR 8
Scope: display-only Control Tower panel

This panel shows local agent task query results in the frontend.

## Data source

```text
GET /agent/tasks?limit=20
```

## Frontend files

```text
frontend/agentTaskPanel.jsx
frontend/main.jsx
```

## Displayed information

The panel shows:

```text
contract
source_count
result_count
record_count
work_id
source_agent
action
state
risk_level
created_at
read_only
is_order_action
broker_api_called
live_mode_touched
allowed_for_live_execution
```

## Safety behavior

The panel is view-only. It renders task records and safety flags. It does not change task state, submit backend mutations, or create new server routes.

Expected flags:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

## Test command

```bash
python -m pytest tests/test_agent_task_panel_ui.py tests/test_agent_tasks_query_api.py tests/test_agent_tasks_api.py -q
```

## Next step

Agent PR 9 may add backend patch-review endpoints. UI controls are still out of scope for this panel PR.
