# Native Runtime Contract and Preflight Hardening

## Purpose

Runtime Correction PR 4 hardens algotradify's native runtime contract after Tradebot source has been imported as tracked source.

This PR does not promote root `main.py`, does not promote root `run_live.sh`, and does not change API/frontend/paper/agent behavior.

## Why this PR exists

Runtime Correction PR 3 imported native runtime source under root runtime directories, but root `main.py` is still a wrapper/launcher and external runtime fallback still exists.

If PR 4 blindly changed normal runtime resolution to repo root, current root `main.py` would load itself recursively because it still delegates to resolved runtime `main.py`.

Therefore PR 4 adds strict native preflight proof without changing normal runtime boot behavior yet.

## New native contract fields

`run_preflight()` now reports:

```text
runtime_ownership
native_required
native_source_present
native_main_promoted
external_runtime_allowed
external_runtime_used
```

Expected PR 4 ownership state:

```text
runtime_ownership=NATIVE_SOURCE_IMPORTED_PENDING_MAIN_PROMOTION
native_source_present=true
native_main_promoted=false
```

## Strict native mode

Strict native mode is enabled with:

```bash
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true
```

In strict native mode:

- repo root is selected only if native source markers are present
- external fallbacks are disabled
- missing native markers fail closed
- root `main.py` promotion is reported as WARN until PR 5

## External fallback opt-out

External fallbacks can be disabled without requiring native mode:

```bash
ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=false
```

This prevents silent fallback to sibling/home Tradebot roots.

## Native source markers

A repo root counts as native source imported when all are present:

```text
core/
config/
RUNTIME_SOURCE_MANIFEST.json
runtime_native/tradebot_main.py
```

## Artifact root behavior

When strict native mode selects the repo root, runtime artifacts resolve to:

```text
<repo>/.runtime
```

## What this PR deliberately does not do

- no root `main.py` promotion
- no root `run_live.sh` promotion
- no API route changes
- no frontend changes
- no broker calls
- no auth flow
- no live execution
- no dashboard controls

## Acceptance proof

```bash
python -m pytest tests/test_runtime_contract.py tests/test_native_runtime_contract.py -q
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true python scripts/preflight_runtime.py --json --no-create-runtime-dirs
```

Expected:

```text
native_source_present=true
native_main_promoted=false
external_runtime_used=false
runtime_ownership=NATIVE_SOURCE_IMPORTED_PENDING_MAIN_PROMOTION
```

The preflight may remain WARN because root `main.py` promotion is intentionally deferred to Runtime Correction PR 5.
