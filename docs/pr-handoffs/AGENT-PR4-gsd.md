# Agent PR 4 — GSD Build Handoff

PR: Agent PR 4 — Local Agent Work CLI

## Implemented scope

Implemented the local-only agent work submission CLI.

## Files changed

```text
scripts/submit_agent_work.py
docs/samples/gsd-agent-work.json
docs/samples/hermes-agent-work.json
docs/samples/grill-agent-work.json
tests/test_submit_agent_work.py
docs/local-agent-work-cli.md
docs/pr-handoffs/AGENT-PR4-grill.md
docs/pr-handoffs/AGENT-PR4-gsd.md
docs/pr-handoffs/AGENT-PR4-hermes.md
```

## Implementation summary

- Added `scripts/submit_agent_work.py`.
- Added local sample payloads for GSD, Hermes, and Grill.
- Added CLI tests for input errors, blocked requests, rejected requests, approved patch-only requests, forbidden paths, and safe output flags.
- Added local CLI documentation.

## Safety boundary preserved

No task store, API, dashboard, mobile screen, webhook, broker call, live config, paper order trigger, runtime worker, or auto-merge behavior was implemented.

## Test command

```bash
python -m pytest tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Known limitation

This CLI writes local evidence but does not create queryable task storage. Agent PR 5 owns task storage.
