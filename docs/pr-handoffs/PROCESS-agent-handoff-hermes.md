# Process PR — Hermes Diff Review and State Handoff

## Role

Reviewer/state recorder only. Review final diff against Grill scope. Do not implement product code.

## Grill artifact reviewed

Path: docs/pr-handoffs/PROCESS-agent-handoff-grill.md

## GSD artifact reviewed

Path: docs/pr-handoffs/PROCESS-agent-handoff-gsd.md

## Final changed files

- .github/pull_request_template.md
- docs/agent-handoff-protocol.md
- docs/pr-handoffs/TEMPLATE-grill.md
- docs/pr-handoffs/TEMPLATE-gsd.md
- docs/pr-handoffs/TEMPLATE-hermes.md
- docs/pr-handoffs/PROCESS-agent-handoff-grill.md
- docs/pr-handoffs/PROCESS-agent-handoff-gsd.md
- docs/pr-handoffs/PROCESS-agent-handoff-hermes.md
- scripts/check_pr_stage_gates.py

## Changed files match approved scope

Yes.

## Forbidden files touched

No.

## Safety boundary preserved

Yes. Process-only. No trading runtime behavior changed.

## Behavior tests added

The PR body checker now requires handoff artifact references and independence declarations.

## Negative tests added

Missing handoff sections/phrases fail the checker.

## Focused test command

```bash
python scripts/check_pr_stage_gates.py /tmp/pr_body.md
```

## Adjacent regression command

Not applicable. Process-only PR.

## CI status

Pending.

## Remaining risks

- This enforces evidence references, not true cryptographic independence.
- Human review still must verify that artifacts are not fake or copied blindly.
- Future PRs will need to create three handoff files before merge.

## Reject before merge if

- Any product/runtime/trading code is changed.
- PR body does not reference all three handoff artifacts.
- Checker does not require independence declarations.

## State update after merge

Latest merged PR: Process PR — independent stage handoff protocol.
Product PR: unchanged; next product PR remains PR 92 — Paper Trading Pipeline Orchestrator after PR 91.
Next PR only: PR 92 after process PR merges.
What not to touch next: broker/live/API/UI/dashboard/strategy/ML unless scoped by roadmap.

## Hermes verdict

Approve.
