# Native Runtime Source Import

Runtime Correction PR 3 imports Tradebot runtime source into algotradify as tracked source without changing runtime behavior.

This PR does not replace root `main.py`, does not promote root `run_live.sh`, does not modify `runtime_contract.py`, and does not wire API/frontend/paper/agent behavior.

Imported paths:

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

Deferred paths:

- root main.py replacement: Runtime Correction PR 5
- root run_live.sh promotion: Runtime Correction PR 6
- existing strategies/ files preserved; only missing files imported

Safety:

- no broker calls
- no live behavior
- no runtime behavior changes
- no secrets/tokens/logs/runtime artifacts imported
