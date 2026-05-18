## Summary

Product PR:
GitHub PR:
Scope:

## Agent handoff evidence

Grill artifact:
GSD artifact:
Hermes artifact:

Grill independent: yes
GSD followed Grill scope: yes
Hermes reviewed final diff: yes

## Pre-code scope review

Proposed PR:
Why this PR is next:
Files to change:
Files not to touch:
Safety boundary:
Failure cases:
Negative tests:
Acceptance proof:
Regression risks:
Merge blockers:

## Proposed design

## Files changed

## Files not touched

## Safety boundary

- [ ] No real broker execution
- [ ] No LIVE orders
- [ ] No broker credentials
- [ ] No dashboard/UI unless scoped
- [ ] No unrelated cleanup
- [ ] No silent fallback hiding broken data
- [ ] paper_only / read_only / is_order_action / broker_api_called / real_order_id safety fields preserved where relevant

## Tests added

## Negative tests

## Test commands

Focused:

```bash
python -m pytest ...
```

Adjacent regression:

```bash
python -m pytest ...
```

## Acceptance proof

## Post-code review

Changed files match approved scope:
Forbidden files touched:
Safety boundary preserved:
Behavior tests added:
Negative tests added:
Focused test command:
Adjacent regression command:
CI status:
Remaining risks:
Reject before merge if:

## Regression risks

## Self-review

- What can break?
- What is under-tested?
- What would a strict reviewer reject?
- What was intentionally not touched?
