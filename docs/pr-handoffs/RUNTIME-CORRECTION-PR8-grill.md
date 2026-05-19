# Runtime Correction PR 8 — Grill Review

## Scope under review

Runtime Correction PR 8 — Broker Auth Visibility and Startup UX.

This PR may expose local-only broker auth visibility and operator startup guidance.

## Hard challenge

The dangerous mistake is turning auth visibility into auth mutation.

This PR must not run login from the API/dashboard, call Kite/broker APIs, probe profiles, mutate token files, expose raw token values, expose API secrets, add order controls, or toggle live mode.

## Required proof

The PR must prove:

1. `/broker/auth/visibility` is GET-only
2. payload is local-files/env-only
3. payload has `broker_api_called=false`
4. payload has `profile_probe_called=false`
5. payload has `token_mutated=false`
6. payload has `raw_token_exposed=false`
7. payload has `api_secret_exposed=false`
8. payload has `is_order_action=false`
9. panel exposes `allowed_actions=[]`
10. panel lists forbidden mutation/action categories

## Rejection conditions

Reject this PR if any of these happen:

- broker API/profile probe is called
- auth/login endpoint is added
- token write/refresh/logout endpoint is added
- raw token or API secret is exposed
- dashboard action button/control is added
- broker order behavior is added
- runtime worker is started
- LIVE becomes default

## Grill verdict

Approved only as local-only read-only broker auth visibility and startup guidance.
