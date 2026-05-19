# External Runtime Deprecation

## Purpose

Runtime Correction PR 9 deprecates external Tradebot-compatible runtime fallback and disables silent external fallback by default.

Algotradify is now expected to run as a native runtime owner after the previous correction PRs imported source, promoted root `main.py`, added guarded operator commands, and exposed runtime/auth visibility.

## New default

External runtime fallback is disabled by default.

```text
ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME unset -> external fallback disabled
ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=false -> external fallback disabled
ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true -> temporary explicit compatibility opt-in
```

## Native runtime default

When native source markers exist, runtime resolution prefers the repo root:

```text
main.py
core/
config/
RUNTIME_SOURCE_MANIFEST.json
runtime_native/tradebot_main.py
```

Expected preflight posture:

```text
runtime_ownership=NATIVE
external_runtime_allowed=false
external_runtime_deprecated=true
external_runtime_used=false
```

## Temporary explicit compatibility

External compatibility is still available only as an explicit opt-in:

```bash
ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true
```

This is temporary compatibility. It is not the default and should not be used for normal operation.

When explicit fallback is used, preflight reports a warning:

```text
external_runtime_fallback.deprecated = WARN
```

## What this PR deliberately does not do

- no root `main.py` changes
- no root `run_live.sh` changes
- no operator command changes
- no broker/auth/order behavior
- no dashboard action controls
- no paper/agent internals
- no live default change
- no removal of explicit external opt-in before PR 10

## Acceptance proof

```bash
python -m pytest tests/test_runtime_contract.py tests/test_native_runtime_contract.py tests/test_runtime_ownership_api.py -q
```

The tests prove:

- external fallback is disabled by default
- configured external env roots are ignored by default
- native repo root remains default
- explicit external opt-in still works as temporary compatibility
- preflight exposes external fallback deprecation metadata
- runtime ownership API exposes deprecation fields
