# Runtime Correction PR 6 — Hermes Review

## Final diff review target

Runtime Correction PR 6 must stay limited to guarded operator boot commands.

## Expected changed files

```text
run_live.sh
scripts/operator_boot.py
tests/test_operator_boot_commands.py
docs/operator-boot-commands.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR6-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR6-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR6-hermes.md
PROJECT_STATE.md
```

## Review checklist

- [ ] `./run_live.sh` requires exactly one action
- [ ] LIVE startup requires `--start --i-understand-live-risk`
- [ ] `DRY_RUN=true` blocks LIVE startup
- [ ] `run_live.sh --validate-only` does not start runtime
- [ ] `run_live.sh --login-only` does not start runtime
- [ ] `scripts/operator_boot.py sim` uses SIM mode
- [ ] `scripts/operator_boot.py paper` uses PAPER mode
- [ ] `scripts/operator_boot.py ui-api` starts API only
- [ ] No API/frontend/dashboard behavior is changed
- [ ] No broker order behavior is added
- [ ] No auth API endpoint is added
- [ ] No paper/agent internals are changed

## Final reviewer warning

Do not approve if this PR becomes an auth/API/UI/live-trading feature PR. It is only the operator boot command layer.

## Hermes verdict

Accept only if commands are guarded, explicit, test-covered, and scope-limited.
