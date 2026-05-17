from __future__ import annotations

from paper_broker import execute_paper_order, validate_paper_order_intent


class ExplodingBrokerClient:
    def place_order(self, *args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("real broker client was called")


def _intent(**overrides):
    payload = {
        "intent_id": "intent-1",
        "candidate_id": "c1",
        "mode": "PAPER",
        "symbol": "NIFTY26MAY25500CE",
        "tradingsymbol": "NIFTY26MAY25500CE",
        "transaction_type": "BUY",
        "quantity": 25,
        "order_type": "LIMIT",
        "product": "MIS",
        "price": 100.5,
        "trigger_price": None,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "requires_broker_adapter": False,
    }
    payload.update(overrides)
    return payload


def test_paper_broker_accepts_valid_paper_intent_without_real_broker_call():
    result = execute_paper_order(intent=_intent(), ts_epoch=123.0)

    assert result.accepted is True
    assert result.paper_only is True
    assert result.is_order_action is False
    assert result.broker_api_called is False
    assert result.real_order_id is None
    assert result.blockers == []
    assert result.ack is not None
    ack = result.ack.to_dict()
    assert ack["synthetic_order_id"].startswith("paper-")
    assert ack["intent_id"] == "intent-1"
    assert ack["candidate_id"] == "c1"
    assert ack["status"] == "PAPER_ACCEPTED"
    assert ack["mode"] == "PAPER"
    assert ack["paper_only"] is True
    assert ack["is_order_action"] is False
    assert ack["broker_api_called"] is False
    assert ack["real_order_id"] is None


def test_paper_broker_blocks_real_broker_client_even_if_client_is_not_called():
    result = execute_paper_order(intent=_intent(), broker_client=ExplodingBrokerClient())

    assert result.accepted is False
    assert "REAL_BROKER_CLIENT_FORBIDDEN_IN_PAPER" in result.blockers
    assert result.ack is None
    assert result.broker_api_called is False


def test_paper_broker_blocks_non_paper_intent():
    result = execute_paper_order(intent=_intent(mode="LIVE"))

    assert result.accepted is False
    assert "PAPER_MODE_REQUIRED" in result.blockers


def test_paper_broker_blocks_missing_intent():
    blockers, warnings = validate_paper_order_intent(intent=None)

    assert "ORDER_INTENT_REQUIRED" in blockers
    assert warnings == []


def test_paper_broker_blocks_unsafe_intent_flags():
    result = execute_paper_order(
        intent=_intent(
            is_order_action=True,
            broker_api_called=True,
            real_order_id="real-1",
            requires_broker_adapter=True,
        )
    )

    assert result.accepted is False
    assert "INTENT_ORDER_FLAG_UNSAFE" in result.blockers
    assert "INTENT_BROKER_API_FLAG_UNSAFE" in result.blockers
    assert "INTENT_REAL_ORDER_ID_FORBIDDEN" in result.blockers
    assert "INTENT_REQUIRES_BROKER_ADAPTER_UNSAFE" in result.blockers


def test_paper_broker_blocks_missing_identity_fields():
    result = execute_paper_order(intent=_intent(intent_id="", candidate_id=""))

    assert result.accepted is False
    assert "INTENT_ID_REQUIRED" in result.blockers
    assert "CANDIDATE_ID_REQUIRED" in result.blockers


def test_paper_broker_blocks_invalid_order_fields():
    result = execute_paper_order(
        intent=_intent(
            transaction_type="HOLD",
            quantity=0,
            order_type="BAD",
            product="BAD",
        )
    )

    assert result.accepted is False
    assert "TRANSACTION_TYPE_REQUIRED_OR_UNSUPPORTED" in result.blockers
    assert "POSITIVE_QUANTITY_REQUIRED" in result.blockers
    assert "ORDER_TYPE_REQUIRED_OR_UNSUPPORTED" in result.blockers
    assert "PRODUCT_REQUIRED_OR_UNSUPPORTED" in result.blockers


def test_paper_broker_limit_order_requires_price():
    result = execute_paper_order(intent=_intent(order_type="LIMIT", price=None))

    assert result.accepted is False
    assert "LIMIT_PRICE_REQUIRED" in result.blockers


def test_paper_broker_stop_order_requires_trigger_price():
    result = execute_paper_order(intent=_intent(order_type="SL-M", trigger_price=None))

    assert result.accepted is False
    assert "TRIGGER_PRICE_REQUIRED" in result.blockers


def test_paper_broker_market_order_does_not_require_price():
    result = execute_paper_order(intent=_intent(order_type="MARKET", price=None), ts_epoch=123.0)

    assert result.accepted is True
    assert result.ack is not None
    assert result.ack.price is None
    assert result.ack.order_type == "MARKET"
    assert result.ack.broker_api_called is False
