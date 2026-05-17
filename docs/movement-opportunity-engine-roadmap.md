# Movement Opportunity Engine Roadmap

This roadmap points to the detailed build scope in:

```text
docs/movement-opportunity-engine-bible.md
```

## Current position

Completed safety and execution foundation:

```text
PR 51 — Execution Mode Contract Hardening
PR 52 — Strict Execution Mode API Contract
PR 53 — Wire Strict Execution Mode Parser into Execution Safety API
PR 54 — Execution Safety Response Schema Contract
PR 55 — Pre-Broker Order Intent Contract
PR 56 — Paper Broker Adapter Contract
```

## Planned movement-opportunity chain

```text
PR 57 — Movement Opportunity Engine Bible
PR 58 — Movement Candidate Contract
PR 59 — Movement Regime Classifier v1
PR 60 — Movement Registry and Candidate Pool Shell
PR 61 — Opening Drive and ORB Retest
PR 62 — Compression Breakout and Trend Pullback
PR 63 — VWAP Reclaim and Failed Breakout Trap
PR 64 — Exhaustion and Mean Reversion Extension
PR 65 — Event Volatility and Late-Day Momentum
PR 66 — Option Pressure Confirmation
PR 67 — No-Trade Engine
PR 68 — Opportunity Ranker v1
PR 69 — Movement Evidence and API Read Model
PR 70 — Dashboard Separation
```

## Build rule

Do not add strategies directly into execution.

Every strategy must first produce a candidate. Candidate pool, confirmation, blockers, no-trade, ranker, execution safety, and order intent decide what happens next.

## Safety rule

Fallback quote data, stale option LTP, missing depth, and wide spread must never become executable truth.

## Next PR

PR 58 must be contract-only:

```text
movement_engine/contract.py
movement_engine/context.py
tests/test_movement_contract.py
docs/movement-candidate-contract.md
```

No strategy behavior changes.
No broker/order changes.
No dashboard changes.
