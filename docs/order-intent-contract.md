# Pre-Broker Order Intent Contract

PR 55 adds a validated order-intent layer before any broker adapter exists.

## Why this exists

The trading roadmap now has execution-mode safety and `/execution-safety` response contracts.

The next step is **not** broker placement.

The next step is a clean order-intent contract that proves the system can transform a selected candidate plus safety evidence into a normalized intent without calling a broker.

## Hard rule

This layer does not place orders.

It must not:

- call broker APIs
- submit orders
- modify orders
- cancel orders
- exit positions
- create a real broker order id

## Implementation

```text
order_intent/
  __init__.py
  contract.py
```

Exports:

```text
OrderIntent
OrderIntentBuildResult
build_order_intent
validate_order_intent_inputs
```

## Required inputs

Order intent creation requires:

1. selected top executable candidate
2. execution safety response
3. optional matching readiness record

## Required candidate fields

The selected candidate must provide:

```text
candidate_id
transaction_type: BUY | SELL
quantity > 0
order_type: MARKET | LIMIT | SL | SL-M
product: MIS | NRML | CNC
```

Additional conditional requirements:

```text
LIMIT requires price
SL / SL-M requires trigger_price
```

## Safety validation

The contract blocks intent creation if:

```text
NO_TOP_EXECUTABLE_SELECTED
TOP_EXECUTABLE_ORDER_FLAG_UNSAFE
EXECUTION_SAFETY_REQUIRED
EXECUTION_SAFETY_NOT_PERMITTED
EXECUTION_SAFETY_ORDER_FLAG_UNSAFE
EXECUTION_SAFETY_VISIBILITY_FLAG_REQUIRED
EXECUTION_MODE_UNSUPPORTED
INVALID_EXECUTION_MODE
BROKER_API_ALLOWED_ONLY_IN_LIVE
REAL_ORDER_ALLOWED_ONLY_IN_LIVE
READINESS_NOT_ALLOWED
READINESS_ORDER_FLAG_UNSAFE
READINESS_CANDIDATE_MISMATCH
CANDIDATE_ID_REQUIRED
TRANSACTION_TYPE_REQUIRED_OR_UNSUPPORTED
POSITIVE_QUANTITY_REQUIRED
ORDER_TYPE_REQUIRED_OR_UNSUPPORTED
PRODUCT_REQUIRED_OR_UNSUPPORTED
LIMIT_PRICE_REQUIRED
TRIGGER_PRICE_REQUIRED
```

## Output guarantees

Every `OrderIntent` guarantees:

```text
is_order_action=false
broker_api_called=false
real_order_id=null
requires_broker_adapter=false
```

Even when LIVE safety flags allow broker API, this contract only produces intent data. A later broker adapter PR must consume the intent through a separate guarded boundary.

## Supported modes

```text
SIM
PAPER
LIVE
```

## Supported order fields

```text
transaction_type: BUY, SELL
order_type: MARKET, LIMIT, SL, SL-M
product: MIS, NRML, CNC
```

## Tests

Added:

```text
tests/test_order_intent_contract.py
```

The tests prove:

- valid PAPER intent builds without broker call
- missing safety blocks intent
- blocked safety blocks intent
- invalid execution mode blocks intent
- non-LIVE broker permission is rejected
- incomplete order fields are rejected
- readiness candidate mismatch is rejected
- future LIVE intent can be represented without broker call

## Safety boundary

This PR does not add:

- broker adapters
- real order endpoints
- order buttons
- broker API calls
- real orders in tests
- replay/control-tower polish
