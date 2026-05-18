# Agent Workflow Discipline

This document defines how to use Grill Me, GSD, Hermes-style memory, Codex, ChatGPT, Cursor, Claude Code, Gemini CLI, or similar agents on algotradify without damaging the product.

## Correct order

/grill-me
  -> scope pressure test

GSD or coding agent
  -> one-phase implementation

Hermes or project memory
  -> record merged state and lessons

## Grill stage

Use before coding.

Purpose:

- Kill ambiguity
- Expose scope creep
- Define files to change
- Define files not to touch
- Define negative tests
- Define acceptance proof

Example prompt:

Grill this PR scope before coding.

Project: algotradify
Current PR: PR XX — <name>

Rules:
- Do not code.
- Inspect repo context if needed.
- Ask what is ambiguous.
- Define files to change.
- Define files not to touch.
- Define negative tests.
- Define acceptance proof.
- Reject scope creep.

## GSD / coding-agent stage

Use only after scope is clear.

Rules:

- Implement one PR only.
- Do not touch unrelated files.
- Do not change broker/live behavior.
- Add focused tests.
- Add negative tests.
- Run focused test command.
- Prepare PR summary.

## Hermes / memory stage

Use after merge or rejection.

Record:

- Latest merged PR
- Files changed
- Tests passed
- Tests failed
- Risks left
- Next PR only
- What not to touch

## Forbidden uses

Do not use agents for:

- live trading decisions
- broker credential handling
- order placement
- bypassing safety gates
- broad refactors
- strategy expansion before paper truth is proven
- dashboard work before the roadmap allows it
- ML/ranker work before expectancy is proven

## Safe branch rule

Never work on main.

Use:

```bash
git checkout main
git pull origin main
git checkout -b feature/<specific-pr-name>
```

## Acceptance proof rule

Every PR must show:

- focused test command
- adjacent regression command
- safety proof
- negative test coverage
- what was intentionally not touched
