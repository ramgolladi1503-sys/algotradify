# Agent PR Stage Gates

This document converts the agent workflow into mandatory PR gates.

The goal is to force real Grill/GSD/Hermes value without adding runtime code or trading automation.

## Gate order

```text
Pre-code scope review
  -> scoped implementation
  -> post-code PR review
  -> state recording
```

## Gate 1 — Pre-code scope review

Run before implementation.

Required evidence:

```text
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
```

This gate represents the Grill value. It must pressure-test the PR before code exists.

## Gate 2 — Scoped implementation

Run only after Gate 1 is clear.

Rules:

- Implement only the approved PR.
- Touch only approved files unless explicitly justified.
- Add focused and negative tests.
- Preserve safe flags.
- Avoid broker, LIVE, API, UI, runtime, strategy, and ML/ranker work unless explicitly scoped.

This gate represents the GSD value. It turns a clear scope into one implementation phase.

## Gate 3 — Post-code PR review

Run after code is written and before merge.

Required evidence:

```text
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
```

This gate is the actual diff review. It must compare implementation against the approved scope.

## Gate 4 — State recording

Run after merge or rejection.

Required evidence:

```text
Latest merged PR:
Product PR:
Files changed:
Tests added:
Commands passed:
Commands failed:
Risks remaining:
Next PR only:
What not to touch next:
```

This gate represents Hermes value. It records continuity but does not control trading.

## Merge rule

A PR should not merge unless the PR body contains both:

```text
## Pre-code scope review
## Post-code review
```

The stage gate checker enforces this at text level. Human review still owns technical judgment.
