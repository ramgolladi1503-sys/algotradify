# Runtime Correction PR 3 — Grill Review

Scope: Native Runtime Source Import.

This PR may import Tradebot source as tracked files, but must not change runtime behavior.

Reject if:

- root main.py is replaced
- runtime_contract.py changes
- root run_live.sh is promoted
- API/frontend/paper/agent behavior changes
- secrets/tokens/logs/runtime artifacts are imported
- existing strategies files are overwritten
