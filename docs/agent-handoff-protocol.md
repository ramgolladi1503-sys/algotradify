# Independent Stage Handoff Protocol

This protocol makes the Grill / GSD / Hermes workflow explicit and auditable.

It does not create autonomous agents inside the trading system. It creates hard handoff artifacts that separate scope review, implementation, and post-code review.

## Roles

### Stage 1 — Grill

Allowed:

- Read repo state, scope bible, roadmap, and prior PRs.
- Produce a scope decision.
- Define files to change and files not to touch.
- Define failure cases, negative tests, acceptance proof, and merge blockers.

Forbidden:

- No code changes.
- No commits.
- No branch mutation.
- No test rewriting.

Output artifact:

```text
docs/pr-handoffs/PR-<number>-grill.md
```

### Stage 2 — GSD Builder

Allowed:

- Implement only the approved Grill scope.
- Add behavior tests and negative tests.
- Update docs and exports only when scoped.
- Open the PR.

Forbidden:

- No changing the approved scope without a new Grill update.
- No unrelated refactors.
- No broker, LIVE, API, UI, runtime, strategy, or ML/ranker work unless explicitly scoped.

Output artifact:

```text
docs/pr-handoffs/PR-<number>-gsd.md
```

### Stage 3 — Hermes Reviewer

Allowed:

- Review the actual PR diff against the Grill scope.
- Identify scope creep, missing tests, safety leakage, and merge blockers.
- Record state update after merge.

Forbidden:

- No product code implementation.
- No silent approval.
- No trade decisions.
- No broker credentials or order actions.

Output artifact:

```text
docs/pr-handoffs/PR-<number>-hermes.md
```

## Required handoff chain

Every non-trivial product PR must reference all three artifacts in the PR body:

```text
Grill artifact: docs/pr-handoffs/PR-<number>-grill.md
GSD artifact: docs/pr-handoffs/PR-<number>-gsd.md
Hermes artifact: docs/pr-handoffs/PR-<number>-hermes.md
```

## Independence declaration

The PR body must include:

```text
Grill independent: yes
GSD followed Grill scope: yes
Hermes reviewed final diff: yes
```

This is not cryptographic enforcement. It is an auditable separation contract. Human review still owns judgment.

## Reject PR if

- Grill artifact is missing.
- GSD artifact is missing.
- Hermes artifact is missing.
- Builder changed files outside Grill scope.
- Hermes review is written before implementation exists.
- Hermes says forbidden layers changed.
- The PR body does not link all three artifacts.
- Runtime, broker, API, UI, strategy, or ML/ranker work appears outside scope.

## Why this exists

A single ChatGPT pass can fake discipline. Separate handoff artifacts make each stage visible and reviewable.

The point is not bureaucracy. The point is to stop PR-loop drift and prevent one agent from silently approving its own bad scope.
