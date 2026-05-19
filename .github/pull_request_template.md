## Summary

<!-- Explain what this PR changes and why. -->

## Agent handoff evidence

Grill artifact: `docs/pr-handoffs/<TASK-ID>-grill.md`
GSD artifact: `docs/pr-handoffs/<TASK-ID>-gsd.md`
Hermes artifact: `docs/pr-handoffs/<TASK-ID>-hermes.md`

Additional role artifacts required by the architecture gate:

```text
docs/pr-handoffs/<TASK-ID>-scope-owner.md
docs/pr-handoffs/<TASK-ID>-qa-safety.md
docs/pr-handoffs/<TASK-ID>-evidence.md
```

Grill independent: yes
GSD followed Grill scope: yes
Hermes reviewed final diff: yes

## Pre-code scope review

Proposed PR:

Why this PR is next:

Files to change:

```text

```

Files not to touch:

```text

```

Safety boundary:

Negative tests:

```text

```

Regression risks:

```text

```

## Proposed design

```text

```

## Files changed

```text

```

## Files not touched

```text

```

## Safety boundary

- [ ] No unscoped product behavior
- [ ] No unscoped runtime behavior
- [ ] No unscoped dashboard behavior
- [ ] No unscoped strategy/ranker/profitability work
- [ ] Safe flags preserved where relevant

## Tests added

```text

```

## Test commands

Focused:

```bash

```

Adjacent regression:

```bash

```

## Acceptance proof

```text

```

## Post-code review

Changed files match approved scope: yes

Forbidden files touched: no

Safety boundary preserved: yes

Behavior tests added:

Negative tests added:

Focused test command:

Adjacent regression command:

CI status:

Remaining risks:

Reject before merge if:

## Next PR after merge

```text

```
