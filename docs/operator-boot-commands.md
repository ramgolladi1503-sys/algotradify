# Operator Boot Commands

## Purpose

Runtime Correction PR 6 adds native operator boot commands after root `main.py` was promoted to the native runtime entrypoint.

This PR is about operator startup ergonomics and safety. It does not add broker order behavior, auth API endpoints, dashboard controls, frontend behavior, or paper/agent internals.

## Commands

### Native runtime preflight

```bash
python scripts/operator_boot.py preflight
```

Runs native runtime preflight with:

```text
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true
```

### SIM startup

```bash
python scripts/operator_boot.py sim
```

Starts native `main.py` with:

```text
EXECUTION_MODE=SIM
TRADING_MODE=SIM
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true
```

### PAPER startup

```bash
python scripts/operator_boot.py paper
```

Starts native `main.py` with:

```text
EXECUTION_MODE=PAPER
TRADING_MODE=PAPER
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true
```

### API-only operator UI backend

```bash
python scripts/operator_boot.py ui-api --host 127.0.0.1 --port 8000
```

Starts the FastAPI backend only. This does not start the trading runtime.

### LIVE startup

```bash
./run_live.sh --start --i-understand-live-risk
```

Root `run_live.sh` is explicitly LIVE-only and guarded. It never starts LIVE by default.

Useful validation/login commands:

```bash
./run_live.sh --validate-only
./run_live.sh --login-only
```

## Safety rules

`./run_live.sh` requires an explicit action:

```text
--validate-only
--login-only
--start --i-understand-live-risk
```

It rejects ambiguous startup:

```text
./run_live.sh
```

It rejects LIVE startup when:

```text
DRY_RUN=true
```

It only forces these after live gates pass:

```text
EXECUTION_MODE=LIVE
TRADING_MODE=LIVE
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true
```

## What this PR deliberately does not do

- no broker order behavior
- no auth API endpoint
- no frontend/dashboard control
- no agent/paper internals
- no strategy provider changes
- no ML ranker changes
- no LIVE default behavior

## Acceptance proof

```bash
python -m pytest tests/test_operator_boot_commands.py -q
bash run_live.sh --help
python scripts/operator_boot.py --help
python scripts/operator_boot.py preflight
```

The tests prove:

- live start requires explicit confirmation
- root `run_live.sh` is guarded
- SIM/PAPER/UI commands do not force LIVE
- preflight uses native runtime mode
- no UI/API feature behavior is added by `run_live.sh`
