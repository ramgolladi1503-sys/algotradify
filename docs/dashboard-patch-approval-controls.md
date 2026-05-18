# Dashboard Patch Approval Controls

Status: Agent PR 10
Scope: frontend patch-review recording controls only

This PR adds dashboard controls that can record a patch-review decision for an existing agent task by calling the PR9 backend endpoints.

## Controls

```text
Record Patch Approval
Record Patch Rejection
```

## API calls

```text
POST /agent/tasks/{work_id}/approval
POST /agent/tasks/{work_id}/rejection
```

## What these controls do

They record a patch-review decision only.

They do not:

```text
run tasks
apply patches
merge code
place orders
modify orders
cancel orders
exit positions
call broker APIs
touch live mode
change live config
auto-merge
```

## Frontend files

```text
frontend/agentTaskPanel.jsx
tests/test_agent_task_panel_ui.py
```

## Safety checks

The panel only exposes patch-review controls for task records where:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

## Known limitation

The frontend component posts to the patch-review API. If the frontend and API are served from different origins, the API CORS policy must allow `POST` for the dashboard origin.

That backend CORS change is intentionally not bundled here because this PR keeps the backend untouched after a failed large-file patch attempt was rolled back.

## Test command

```bash
python -m pytest tests/test_agent_task_panel_ui.py tests/test_agent_tasks_patch_approval_api.py -q
```

## Next step

A tiny follow-up PR may add CORS `POST` support for the existing dashboard origin if browser deployment requires it.
