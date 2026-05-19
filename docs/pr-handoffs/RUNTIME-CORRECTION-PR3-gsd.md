# Runtime Correction PR 3 — GSD Execution Plan

Goal: import native runtime source without wiring behavior.

Allowed:

- core/
- config/
- dashboard/
- ml/
- models/
- rl/
- fixtures/
- strategies/ missing files only
- runtime_native/tradebot_main.py
- runtime_native/tradebot_run_live.sh
- runtime_native/tradebot_requirements.txt
- RUNTIME_SOURCE_MANIFEST.json
- docs/tests/handoffs

Not allowed:

- root main.py replacement
- runtime_contract.py changes
- root run_live.sh promotion
- API/frontend/paper/agent changes
- broker/live behavior
