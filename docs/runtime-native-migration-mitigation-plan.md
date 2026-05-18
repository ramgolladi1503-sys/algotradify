# Runtime Native Migration / Mitigation Plan

## Status

This document is a planning and mitigation artifact only. It does not change runtime behavior, broker behavior, API behavior, frontend behavior, paper-trading behavior, or agent-system behavior.

Current objective: correct algotradify's runtime ownership boundary without disturbing the code already built around paper trading, replay evidence, agent workflow, execution safety, movement opportunity, and Control Tower visibility.

## Why this migration is needed

Algotradify has grown into a large product surface, but the runtime ownership boundary is not honest enough yet.

The current architecture behaves closer to this:

```text
algotradify = Control Tower + APIs + contracts + paper/replay/agent layers + runtime launcher
```

The intended product direction is closer to this:

```text
algotradify = native trading runtime + Control Tower + paper/replay/agent/safety layers
```

That mismatch creates operational confusion.

Examples:

1. A user may believe `python main.py` starts algotradify's own native engine, while the current launcher-style implementation may resolve and delegate to a Tradebot-compatible runtime root.
2. A user may believe algotradify is self-contained, while runtime resolution can still depend on local/external paths such as an embedded/synced runtime or a sibling checkout.

This is not just a naming issue. In a trading system, unclear runtime ownership can lead to wrong assumptions about authentication, token state, execution mode, startup safety, replay evidence, broker readiness, and what code is actually running.

## Why this was missed until late

This was missed because the project kept making safe forward progress around the runtime instead of proving runtime ownership as a hard invariant.

The blunt reasons:

1. Wrapper behavior was treated as acceptable compatibility for too long.
   - The launcher made algotradify appear runnable as long as a compatible runtime existed somewhere.
   - That made the missing native ownership less visible.

2. Most recent PRs did not require the native runtime to be present.
   - Paper replay, evidence contracts, agent task APIs, dry-run exports, schema checks, and frontend panels can pass tests without actually owning the bot engine.
   - Those PRs were useful, but they did not prove that algotradify was self-contained.

3. Tests validated runtime fallback behavior instead of forbidding it.
   - Existing runtime contract tests proved priority across env vars, embedded roots, sibling `../tradebot`, and home `~/tradebot`.
   - That means the tests were reinforcing the wrapper model, not catching it as a product identity problem.

4. The sync script created a false sense of completion.
   - A local sync into `core_bot/` can make a developer machine work.
   - But local sync is not the same as native tracked source in the repo.

5. Product-state docs focused on PR sequence, not architecture invariants.
   - The roadmap tracked completed paper/agent/replay PRs.
   - It did not enforce a binary invariant like `runtime_ownership=NATIVE` or `external_runtime_used=false`.

6. The question was framed as feature execution too often, not foundation verification.
   - The project kept asking what to build next.
   - It did not stop early enough to ask whether the runtime being built around was actually owned by algotradify.

The prevention rule going forward:

```text
Every major product wave must start with architecture invariants that fail if the foundational assumption is false.
```

For this case, the missing invariants were:

```text
- root native runtime must exist
- root `main.py` must be the real runtime boot entrypoint, not a dynamic external launcher
- `core/` must be tracked source
- `config/` must be tracked source
- external runtime fallback must be disabled by default
- Control Tower must display runtime ownership
```

## Why not rewrite `main.py` from scratch

Rewriting the runtime entrypoint from memory is the wrong fix.

Tradebot's existing `main.py` contains safety-critical startup behavior that must not be casually reimplemented:

- runtime guard import side effects
- config loading
- execution mode alignment
- runtime boot safety
- runtime directory initialization
- event log integrity repair
- Kite startup credential validation
- LIVE/PAPER instance locking
- database readiness guard
- startup security enforcement
- trade log initialization
- stale risk halt auto-clear
- readiness gate handling
- orchestrator startup
- reconciliation daemon lifecycle
- broker truth reconciliation lifecycle

A manual rewrite risks accidentally deleting or weakening these controls.

Two concrete failure examples:

1. If instance locking is missed, two LIVE/PAPER bot processes may run at the same time against the same broker session.
2. If startup credential validation or readiness gates are weakened, the bot may start with invalid auth, stale market data, unsafe config, or blocked risk state.

The safer correction is to promote the proven Tradebot runtime into algotradify as native tracked source and then wire algotradify around it.

## Why normal feature PRs should pause

Normal product PRs should pause until runtime ownership is corrected because more paper/replay/dashboard/agent features will otherwise keep building around an unclear engine boundary.

Continuing feature work before this correction causes three problems:

1. Tests may continue passing while the product is still not self-contained.
2. UI/API layers may display runtime evidence without proving which runtime source owns the evidence.
3. Future broker/auth/startup work may get bolted onto a wrapper path instead of the actual native bot runtime.

This is a foundation correction, not architecture polish.

## What must be protected

The migration must not disturb the valuable algotradify layers already built.

Protected areas:

```text
api/
frontend/
paper_trading/
agent_system/
execution_safety/
execution_readiness/
movement_engine/
top_selector/
replay/evidence contracts
tests/
docs/
```

These areas contain safety-oriented contracts and read-only/paper-only behavior. The migration must preserve those contracts.

Examples of protected behavior:

1. Paper/replay outputs must remain paper-only, read-only, non-order actions, and broker-call-free.
2. Agent task APIs must remain patch-review/intake/query only and must not become runtime execution, broker action, paper order trigger, live config mutation, or auto-merge behavior.

## Target architecture

The target is root-native runtime ownership:

```text
algotradify/
  main.py                  # native trading runtime boot entrypoint
  run_live.sh              # native LIVE startup/auth command
  run_algotradify.sh       # safe operator boot command for SIM/PAPER/UI
  core/                    # native Tradebot runtime core
  config/                  # native runtime config
  strategies/              # native strategies
  dashboard/               # optional Streamlit dashboard
  scripts/                 # curated scripts, not blind overwrite
  api/                     # existing FastAPI Control Tower backend
  frontend/                # existing React Control Tower
  paper_trading/           # existing paper truth/replay foundation
  agent_system/            # existing safe agent workflow
  RUNTIME_SOURCE_MANIFEST.json
```

The product should default to native runtime ownership:

```text
runtime_ownership=NATIVE
external_runtime_used=false
runtime_root=<algotradify repo root>
artifact_root=<algotradify repo root>/.runtime
```

External runtime usage should become explicit dev-only behavior, not a silent default.

## Non-goals

This migration must not do the following:

- no live execution enablement by default
- no broker order placement changes
- no UI order buttons
- no strategy expansion
- no ML/ranker expansion
- no paper/replay feature expansion
- no agent scope expansion
- no silent fallback hiding broken runtime state
- no import of `.env`, tokens, runtime files, logs, databases, or secrets
- no broad cleanup unrelated to runtime ownership

## Runtime Correction PR Wave

### PR 1 — Runtime Ownership Audit

Purpose: document and test the current truth before changing behavior.

Files:

```text
docs/runtime-ownership-audit.md
scripts/audit_runtime_ownership.py
tests/test_runtime_ownership_audit.py
PROJECT_STATE.md
```

Implementation:

- detect whether root runtime is native or wrapper-style
- detect whether `core/` and `config/` exist at root
- detect whether external fallback paths are enabled
- report whether normal feature PRs should pause

Acceptance:

```bash
python scripts/audit_runtime_ownership.py --json
python -m pytest tests/test_runtime_ownership_audit.py -q
```

Merge blocker: any runtime behavior change.

### PR 2 — Tradebot Source Import Manifest and Collision Report

Purpose: plan the import before copying source.

Files:

```text
scripts/plan_tradebot_native_import.py
docs/tradebot-native-import-plan.md
runtime_source_manifest.schema.json
tests/test_tradebot_native_import_plan.py
```

Implementation:

- validate source Tradebot checkout
- list files and directories planned for import
- exclude secrets, runtime files, logs, databases, tokens, and large local data
- list collisions with existing algotradify-owned paths
- require explicit decisions for every collision

Acceptance:

```bash
python scripts/plan_tradebot_native_import.py --source ../tradebot --target . --json
python -m pytest tests/test_tradebot_native_import_plan.py -q
```

Merge blocker: import plan claims safe import while unresolved collisions remain.

### PR 3 — Native Runtime Source Import

Purpose: bring Tradebot runtime source into algotradify as tracked source.

Files/directories to import:

```text
core/
config/
strategies/
dashboard/
ml/
models/
rl/
fixtures/
RUNTIME_SOURCE_MANIFEST.json
docs/native-runtime-source-import.md
tests/test_native_runtime_source_import.py
```

Do not replace root `main.py` yet. If needed, import Tradebot's runtime entrypoint temporarily as a staged snapshot such as:

```text
runtime_native/tradebot_main.py
```

Acceptance:

```bash
git ls-files core | head
git ls-files config | head
git ls-files strategies | head
git ls-files dashboard/streamlit_app.py
git ls-files RUNTIME_SOURCE_MANIFEST.json
python -m pytest tests/test_native_runtime_source_import.py -q
```

Merge blocker: this PR modifies `api/`, `frontend/`, `paper_trading/`, or `agent_system/`.

### PR 4 — Native Runtime Contract and Preflight Hardening

Purpose: make algotradify prefer and validate its own native runtime.

Files:

```text
runtime_contract.py
scripts/preflight_runtime.py
tests/test_runtime_contract.py
tests/test_native_runtime_contract.py
docs/native-runtime-contract.md
```

New default:

```text
runtime_root = algotradify repo root
artifact_root = algotradify/.runtime
```

Strict mode:

```bash
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true
```

Expected preflight fields:

```json
{
  "runtime_ownership": "NATIVE",
  "external_runtime_used": false,
  "native_required": true
}
```

Acceptance:

```bash
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true python scripts/preflight_runtime.py --json
python -m pytest tests/test_runtime_contract.py tests/test_native_runtime_contract.py -q
```

Merge blocker: preflight silently falls back to `../tradebot` or `~/tradebot` in strict mode.

### PR 5 — Root Native `main.py` Promotion

Purpose: replace the wrapper-style root `main.py` with the real native runtime boot flow, adapted minimally for algotradify.

Files:

```text
main.py
runtime_contract.py
tests/test_native_main_boot_contract.py
tests/test_runtime_contract.py
docs/native-main-boot.md
```

Implementation rules:

- use Tradebot's real startup flow as the base
- preserve runtime boot safety
- preserve Kite startup credential validation
- preserve LIVE/PAPER instance locking
- preserve DB readiness
- preserve startup security
- preserve readiness gate behavior
- preserve orchestrator startup
- preserve reconciliation lifecycle
- add only minimal algotradify runtime ownership markers/events

Acceptance:

```bash
grep -R "spec_from_file_location" main.py || true
python -m pytest tests/test_native_main_boot_contract.py tests/test_runtime_contract.py -q
```

Expected: no dynamic external `main.py` loading remains.

Merge blocker: `main.py` still dynamically loads another repo's runtime entrypoint.

### PR 6 — Native `run_live.sh` and Operator Boot Commands

Purpose: bring operational startup into algotradify and add a safe default boot command.

Files:

```text
run_live.sh
run_algotradify.sh
scripts/start_control_tower.py
scripts/operator_boot.py
tests/test_operator_boot_scripts.py
docs/operator-boot.md
```

Commands after this PR:

```bash
./run_algotradify.sh --mode SIM --ui
./run_algotradify.sh --mode PAPER --ui
./run_live.sh --login-only
./run_live.sh --validate-only
./run_live.sh
```

Rules:

- safe operator boot defaults to SIM, not LIVE
- LIVE startup remains explicit
- login-only exits before `main.py`
- validate-only exits before `main.py`
- `DRY_RUN=true` blocks live startup

Acceptance:

```bash
./run_algotradify.sh --mode SIM --validate-only
./run_live.sh --help
python -m pytest tests/test_operator_boot_scripts.py -q
```

Merge blocker: safe operator command defaults to LIVE.

### PR 7 — API and Control Tower Runtime Ownership Wiring

Purpose: make backend and UI show that algotradify is native and self-contained.

Files:

```text
api/server.py
api/schemas.py
frontend/main.jsx
frontend/controlTowerCards.jsx
tests/test_runtime_ownership_api.py
tests/test_control_tower_ui.py
docs/control-tower-native-runtime.md
```

New endpoint:

```text
GET /runtime/ownership
```

Response shape:

```json
{
  "runtime_ownership": "NATIVE",
  "runtime_root": "<repo-root>",
  "artifact_root": "<repo-root>/.runtime",
  "external_runtime_used": false,
  "source_manifest_present": true,
  "read_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null
}
```

Acceptance:

```bash
curl http://localhost:8000/runtime/ownership
python -m pytest tests/test_runtime_ownership_api.py tests/test_control_tower_ui.py -q
npm --prefix frontend run build
```

Merge blocker: UI says native while backend says external, or the endpoint lacks safe flags.

### PR 8 — Broker Auth Visibility and Startup UX

Purpose: expose broker auth status safely without adding broker order behavior.

Files:

```text
api/broker_auth_status.py
api/server.py
frontend/brokerAuthCard.jsx
frontend/main.jsx
tests/test_broker_auth_status_api.py
tests/test_broker_auth_card_ui.py
docs/broker-auth-visibility.md
```

Endpoint:

```text
GET /broker/auth/status
```

Response shape:

```json
{
  "broker": "kite",
  "mode": "SIM",
  "authenticated": false,
  "token_found": false,
  "token_path": ".runtime/kite_access_token",
  "token_age_seconds": null,
  "requires_login": true,
  "login_command": "./run_live.sh --login-only",
  "validate_command": "./run_live.sh --validate-only",
  "read_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null
}
```

Rules:

- no broker order action
- no UI-triggered login in this PR
- no LIVE startup button
- no broker API call in SIM unless explicitly safe and tested

Acceptance:

```bash
curl http://localhost:8000/broker/auth/status
python -m pytest tests/test_broker_auth_status_api.py tests/test_broker_auth_card_ui.py -q
npm --prefix frontend run build
```

Merge blocker: this endpoint places orders, mutates broker state, or introduces UI execution controls.

### PR 9 — Compatibility Cleanup and External Runtime Deprecation

Purpose: prevent the wrapper-era mistake from returning.

Files:

```text
runtime_contract.py
runner/live_wrapper.py
docs/runtime-compatibility.md
tests/test_runtime_contract.py
tests/test_legacy_runtime_wrapper.py
README.md
```

Policy:

```text
Default product mode: NATIVE only
External runtime: dev-only with explicit ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true
```

Acceptance:

```bash
python -m pytest tests/test_runtime_contract.py tests/test_legacy_runtime_wrapper.py -q
```

Merge blocker: `../tradebot` or `~/tradebot` is silently used without explicit env opt-in.

### PR 10 — Full Regression Gate and Migration Lock

Purpose: lock the corrected architecture so future PRs cannot accidentally revert to wrapper mode.

Files:

```text
.github/workflows/portfolio-ci.yml
tests/test_architecture_invariants.py
tests/test_no_external_runtime_fallback.py
tests/test_no_broker_live_leakage.py
docs/native-runtime-migration-acceptance.md
PROJECT_STATE.md
```

CI must fail if:

- root `main.py` dynamically loads external runtime `main.py`
- `core/` is missing
- `config/` is missing
- `RUNTIME_SOURCE_MANIFEST.json` is missing
- external runtime fallback is enabled by default
- `/runtime/ownership` is missing
- broker auth status lacks safe flags
- UI lacks runtime ownership visibility

Acceptance:

```bash
python -m pytest tests/test_architecture_invariants.py -q
python -m pytest tests/test_no_external_runtime_fallback.py -q
python -m pytest tests/test_no_broker_live_leakage.py -q
python -m pytest tests/test_runtime_contract.py -q
python -m pytest tests/test_agent_tasks_api.py tests/test_agent_tasks_query_api.py -q
python -m pytest tests/test_paper_replay_dataset.py -q
npm --prefix frontend run build
```

Merge blocker: CI does not prevent regression back to wrapper mode.

## Final order

Do the correction wave exactly in this order:

```text
1. Runtime Ownership Audit
2. Tradebot Source Import Manifest and Collision Report
3. Native Runtime Source Import
4. Native Runtime Contract and Preflight Hardening
5. Root Native main.py Promotion
6. Native run_live / Operator Boot Commands
7. API and Control Tower Runtime Ownership Wiring
8. Broker Auth Visibility and Startup UX
9. Compatibility Cleanup and External Runtime Deprecation
10. Full Regression Gate and Migration Lock
```

Do not combine the source import, root `main.py` promotion, run scripts, and UI changes into one PR. That would create a review and rollback nightmare.

## Reject conditions for the whole wave

Reject any PR in this wave if it does one of these:

- rewrites Tradebot `main.py` from scratch
- deletes existing algotradify paper/agent/replay code
- silently falls back to `../tradebot`
- imports secrets, `.env`, tokens, logs, DBs, or runtime files
- adds broker order buttons
- makes LIVE the default startup mode
- weakens tests to pass migration
- hides failed preflight with fallback logic
- mixes source import and runtime behavior replacement in one PR

## End-state acceptance

The migration is done only when all of this is true:

```text
runtime_ownership=NATIVE
external_runtime_fallback=disabled_by_default
native_tradebot_source=tracked
root main.py=real runtime boot
run_live.sh=owned by algotradify
safe operator boot command exists
Control Tower displays runtime ownership
Broker auth visibility exists without broker actions
architecture invariant tests prevent regression
normal product PRs can resume
```

## Hard truth

The mistake was not building too much. The mistake was building around an unclear runtime ownership boundary.

This mitigation fixes that boundary without throwing away the heavy product work already completed.
