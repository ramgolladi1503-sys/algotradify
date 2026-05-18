# Algotradify Agent Operating Contract

This repository is a trading-system safety project. Treat every agent-assisted change as production-risk work, even when the change is paper-only or documentation-only.

The goal is not to create more PRs. The goal is to create fewer, stronger PRs that improve stability, safety, paper/live readiness, or profitability validation.

## Non-negotiable rules

- Never work directly on `main`.
- Never use broker credentials in agent sessions.
- Never place real orders from tests, scripts, docs examples, or agent workflows.
- Never introduce LIVE behavior unless the PR explicitly scopes LIVE behavior and proves readiness gates.
- Never let SIM or PAPER paths call real broker placement APIs.
- Never hide broken data with silent fallback.
- Never add dashboard/UI work unless the PR explicitly requires it.
- Never do unrelated cleanup, renaming, formatting, or architecture polish.
- Never add weak tests that only assert object shape.
- Every PR must include acceptance proof.

## Required workflow

Every non-trivial PR must pass through three stages.

### 1. Grill stage: kill ambiguity before code

Use `/grill-me` or an equivalent review prompt before implementation.

The output must answer:

1. What exact problem does this PR solve?
2. What files should change?
3. What files must not change?
4. What unsafe behavior must fail closed?
5. What tests prove behavior, not just shape?
6. What merge blockers would make this PR unacceptable?

If the answer is vague, do not code.

### 2. GSD stage: execute one scoped phase only

Use GSD, Codex, Cursor, Claude Code, Gemini CLI, Windsurf, or another coding agent only after the grilled scope is clear.

Execution rules:

- One PR scope only.
- One branch only.
- No opportunistic refactors.
- No extra abstractions unless required by the scoped behavior.
- No broker imports in read-only, paper-only, or test-only layers.
- Preserve backward-compatible evidence and log schemas unless the scope explicitly changes them.
- Add focused tests plus adjacent regression tests where relevant.

### 3. State stage: record continuity after the PR

After each PR is merged or rejected, update project state.

Record:

- Latest merged Product PR and GitHub PR.
- Files changed.
- Tests added.
- Commands that passed.
- Commands that failed.
- Risks left behind.
- What must not be touched next.
- The next PR only.

Hermes or any long-memory project agent may maintain this state, but it must not decide trades, handle secrets, place orders, or bypass safety gates.

## Required implementation output

Before changing code, the agent must provide:

```text
Proposed design:
Files to change:
Files not to touch:
Safety boundary:
Negative tests:
Acceptance proof:
Regression risks:
