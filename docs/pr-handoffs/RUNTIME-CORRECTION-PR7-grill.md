# Runtime Correction PR 7 — Grill Review

## Scope under review

Runtime Correction PR 7 — API and Control Tower Runtime Ownership Wiring.

This PR may expose runtime ownership visibility only.

## Hard challenge

The dangerous mistake is turning runtime ownership visibility into runtime control.

This PR must not add start/stop buttons, broker calls, order controls, auth endpoints, live toggles, or runtime state mutation.

## Required proof

The PR must prove:

1. `/runtime/ownership` is GET-only
2. payload is read-only and audit-only
3. payload has `is_order_action=false`
4. payload has `broker_api_called=false`
5. payload has `real_order_id=null`
6. payload has `live_mode_touched=false`
7. Control Tower panel exposes `allowed_actions=[]`
8. forbidden action categories are explicitly listed
9. no API/frontend/paper/agent behavior is mutated

## Rejection conditions

Reject this PR if any of these happen:

- broker order behavior is added
- auth API endpoint is added
- dashboard action control is added
- live toggle is added
- runtime state mutation is added
- runtime worker is started
- paper/agent internals are changed
- LIVE becomes default

## Grill verdict

Approved only as read-only runtime ownership visibility.
