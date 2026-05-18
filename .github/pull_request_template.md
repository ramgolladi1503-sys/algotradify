## Summary

Product PR:
GitHub PR:
Scope:

## Proposed design

## Files changed

## Files not touched

## Safety boundary

- [ ] No real broker execution
- [ ] No LIVE orders
- [ ] No broker credentials
- [ ] No dashboard/UI unless scoped
- [ ] No unrelated cleanup
- [ ] No silent fallback hiding broken data
- [ ] paper_only / read_only / is_order_action / broker_api_called / real_order_id safety fields preserved where relevant

## Tests added

## Negative tests

## Test commands

Focused:

```bash
python -m pytest ...
```

Adjacent regression:

```bash
python -m pytest ...
```

## Acceptance proof

## Regression risks

## Self-review

- What can break?
- What is under-tested?
- What would a strict reviewer reject?
- What was intentionally not touched?
