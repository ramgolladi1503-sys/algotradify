# Paper Broker Adapter Contract

PR 56 adds a simulation-only PAPER adapter contract.

## Purpose

The adapter consumes a validated pre-broker `OrderIntent` and returns a synthetic paper acknowledgement for local testing and evidence flow.

It is not a live trading adapter.

## Hard boundary

This module is simulation-only.

It must not:

- contact external trading services
- create real exchange-side identifiers
- mutate a live account
- perform live execution lifecycle actions

## Implementation

```text
paper_broker/
  __init__.py
  adapter.py
```

Exports:

```text
PaperBrokerOrderAck
PaperBrokerExecutionResult
execute_paper_order
validate_paper_order_intent
```

## Input requirements

The adapter accepts only intents with:

```text
mode=PAPER
is_order_action=false
broker_api_called=false
real_order_id=null
requires_broker_adapter=false
```

Required fields:

```text
intent_id
candidate_id
transaction_type: BUY | SELL
quantity > 0
order_type: MARKET | LIMIT | SL | SL-M
product: MIS | NRML | CNC
```

Conditional requirements:

```text
LIMIT requires price
SL / SL-M requires trigger_price
```

## Output guarantees

A successful paper acknowledgement contains:

```text
synthetic_order_id=paper-...
status=PAPER_ACCEPTED
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Blockers

The adapter blocks:

```text
REAL_BROKER_CLIENT_FORBIDDEN_IN_PAPER
ORDER_INTENT_REQUIRED
PAPER_MODE_REQUIRED
INTENT_ORDER_FLAG_UNSAFE
INTENT_BROKER_API_FLAG_UNSAFE
INTENT_REAL_ORDER_ID_FORBIDDEN
INTENT_REQUIRES_BROKER_ADAPTER_UNSAFE
INTENT_ID_REQUIRED
CANDIDATE_ID_REQUIRED
TRANSACTION_TYPE_REQUIRED_OR_UNSUPPORTED
POSITIVE_QUANTITY_REQUIRED
ORDER_TYPE_REQUIRED_OR_UNSUPPORTED
PRODUCT_REQUIRED_OR_UNSUPPORTED
LIMIT_PRICE_REQUIRED
TRIGGER_PRICE_REQUIRED
```

## Tests

Added:

```text
tests/test_paper_broker_adapter.py
```

The tests prove:

- valid PAPER intent creates a synthetic acknowledgement
- external client object is rejected
- non-PAPER intent is rejected
- missing intent is rejected
- unsafe intent flags are rejected
- missing identity fields are rejected
- invalid order fields are rejected
- LIMIT requires price
- SL / SL-M requires trigger price
- MARKET does not require price

## Safety boundary

This PR does not add a live adapter, a live execution route, or any account-mutating behavior.
