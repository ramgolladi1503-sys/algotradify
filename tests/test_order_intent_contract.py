from __future__ import annotations

from order_intent import build_order_intent, validate_order_intent_inputs


def _top_executable(**overrides):
    selected = {
        "candidate_id": "c1",
        "symbol": "NIFTY26MAY25500CE",
        "tradingsymbol": "NIFTY26MAY25500CE",
        "instrument_token": "12345",
        "transaction_type": "BUY",
        "quantity": 25,
        "order_type": "LIMIT",
        "product": "MIS",
        "price": 100.5,
        "strategy": "orb_retest",
        "quality_score": 91.0,
        "is_order": False,
    }
    selected.update(overrides)
    return {"status": "SELECTED", "selected": selected, "is_order": False}


def _safety(**overrides):
    payload = {
        "execution_permitted": True,
        "mode": "PAPER",
        "status": "PERMITTED",
        "blockers": [],
        "warnings": [],
        "audit": {
            "policy": {
                "approval_id": "approval-1",
                "operator_id": "operator-1",
                "broker_confirmation_id": "broker-confirm-1",
            }
        },
        "requires_manual_approval": False,
        "simulated_order_allowed": False,
        "paper_order_allowed": True,
        "broker_api_allowed": False,
        "real_order_allowed": False,
        "is_order_action": False,
        "execution_mode_api_parse": {
            "mode": "PAPER",
            "raw_mode": "PAPER",
            "invalid_mode": False,
            "supported_modes": ["SIM", "PAPER", "LIVE"],
            "blockers": [],
            "warnings": [],
            "is_order_action": False,
        },
        "top_executable": {},
        "readiness_records_checked": 1,
        "safety_visibility_only": True,
    }
    payload.update(overrides)
    return payload


def _readiness(**overrides):
    payload = {
        "candidate_id": "c1",
        "execution_allowed": True,
        "status": "ALLOWED",
        "blockers": [],
        "warnings": [],
        "is_order": False,
    }
    payload.update(overrides)
    return payload


def test_order_intent_builds_valid_paper_intent_without_broker_call():
    result = build_order_intent(
        top_executable=_top_executable(),
        execution_safety=_safety(),
        readiness=_readiness(),
        ts_epoch=123.0,
    )

    assert result.created is True
    assert result.is_order_action is False
    assert result.broker_api_called is False
    assert result.real_order_id is None
    assert result.blockers == []
    assert result.intent is not None
    intent = result.intent.to_dict()
    assert intent["intent_id"].startswith("intent-")
    assert intent["candidate_id"] == "c1"
    assert intent["mode"] == "PAPER"
    assert intent["transaction_type"] == "BUY"
    assert intent["quantity"] == 25
    assert intent["order_type"] == "LIMIT"
    assert intent["product"] == "MIS"
    assert intent["price"] == 100.5
    assert intent["approval_id"] == "approval-1"
    assert intent["operator_id"] == "operator-1"
    assert intent["broker_confirmation_id"] == "broker-confirm-1"
    assert intent["is_order_action"] is False
    assert intent["broker_api_called"] is False
    assert intent["real_order_id"] is None
    assert intent["requires_broker_adapter"] is False


def test_order_intent_blocks_without_execution_safety():
    blockers, warnings = validate_order_intent_inputs(
        top_executable=_top_executable(),
        execution_safety=None,
        readiness=_readiness(),
    )

    assert "EXECUTION_SAFETY_REQUIRED" in blockers
    assert warnings == []


def test_order_intent_blocks_when_execution_safety_not_permitted():
    result = build_order_intent(
        top_executable=_top_executable(),
        execution_safety=_safety(execution_permitted=False, status="BLOCKED", blockers=["MANUAL_APPROVAL_REQUIRED"]),
        readiness=_readiness(),
    )

    assert result.created is False
    assert "EXECUTION_SAFETY_NOT_PERMITTED" in result.blockers
    assert result.intent is None
    assert result.is_order_action is False
    assert result.broker_api_called is False


def test_order_intent_blocks_invalid_execution_mode():
    result = build_order_intent(
        top_executable=_top_executable(),
        execution_safety=_safety(
            execution_permitted=False,
            mode="SIM",
            execution_mode_api_parse={
                "mode": "SIM",
                "raw_mode": "REAL",
                "invalid_mode": True,
                "supported_modes": ["SIM", "PAPER", "LIVE"],
                "blockers": ["INVALID_EXECUTION_MODE"],
                "warnings": ["EXECUTION_MODE_FORCED_TO_SIM"],
                "is_order_action": False,
            },
        ),
        readiness=_readiness(),
    )

    assert result.created is False
    assert "EXECUTION_SAFETY_NOT_PERMITTED" in result.blockers
    assert "INVALID_EXECUTION_MODE" in result.blockers


def test_order_intent_blocks_non_live_broker_permission():
    result = build_order_intent(
        top_executable=_top_executable(),
        execution_safety=_safety(broker_api_allowed=True, real_order_allowed=True),
        readiness=_readiness(),
    )

    assert result.created is False
    assert "BROKER_API_ALLOWED_ONLY_IN_LIVE" in result.blockers
    assert "REAL_ORDER_ALLOWED_ONLY_IN_LIVE" in result.blockers


def test_order_intent_blocks_incomplete_order_fields():
    result = build_order_intent(
        top_executable=_top_executable(quantity=0, transaction_type="HOLD", order_type="LIMIT", price=None, product="BAD"),
        execution_safety=_safety(),
        readiness=_readiness(),
    )

    assert result.created is False
    assert "TRANSACTION_TYPE_REQUIRED_OR_UNSUPPORTED" in result.blockers
    assert "POSITIVE_QUANTITY_REQUIRED" in result.blockers
    assert "PRODUCT_REQUIRED_OR_UNSUPPORTED" in result.blockers
    assert "LIMIT_PRICE_REQUIRED" in result.blockers


def test_order_intent_blocks_stop_order_without_trigger_price():
    result = build_order_intent(
        top_executable=_top_executable(order_type="SL-M", trigger_price=None, stop=None, stop_loss=None),
        execution_safety=_safety(),
        readiness=_readiness(),
    )

    assert result.created is False
    assert "TRIGGER_PRICE_REQUIRED" in result.blockers


def test_order_intent_blocks_readiness_candidate_mismatch():
    result = build_order_intent(
        top_executable=_top_executable(),
        execution_safety=_safety(),
        readiness=_readiness(candidate_id="different"),
    )

    assert result.created is False
    assert "READINESS_CANDIDATE_MISMATCH" in result.blockers


def test_order_intent_accepts_live_safety_flags_without_calling_broker():
    result = build_order_intent(
        top_executable=_top_executable(order_type="MARKET", price=None),
        execution_safety=_safety(
            mode="LIVE",
            paper_order_allowed=False,
            broker_api_allowed=True,
            real_order_allowed=True,
            execution_mode_api_parse={
                "mode": "LIVE",
                "raw_mode": "LIVE",
                "invalid_mode": False,
                "supported_modes": ["SIM", "PAPER", "LIVE"],
                "blockers": [],
                "warnings": [],
                "is_order_action": False,
            },
        ),
        readiness=_readiness(),
    )

    assert result.created is True
    assert result.intent is not None
    assert result.intent.mode == "LIVE"
    assert result.intent.broker_api_called is False
    assert result.intent.real_order_id is None
    assert result.intent.is_order_action is False
