from __future__ import annotations

from paper_trading import (
    build_paper_mtm_pnl,
    paper_mtm_pnl_schema_contract,
)


def _position(key="12345", **overrides):
    payload = {
        "position_id": f"paper-position-{key}",
        "position_key": key,
        "candidate_id": "c1",
        "symbol": "NIFTY26MAY25500CE",
        "tradingsymbol": "NIFTY26MAY25500CE",
        "instrument_token": 12345,
        "strategy": "orb_retest",
        "net_quantity": 10,
        "side": "LONG",
        "average_entry_price": 100.0,
        "last_fill_price": 100.0,
        "last_update_epoch": 100.0,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _ledger(*positions, **overrides):
    position_map = {str(position["position_key"]): position for position in positions}
    payload = {
        "schema_version": "1.0",
        "ledger_type": "PAPER_POSITION_LEDGER",
        "positions": position_map,
        "order_fills": {},
        "last_event": None,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _marks(**overrides):
    payload = {
        "source": "CONTROLLED_MARK",
        "ts_epoch": 105.0,
        "marks": {
            "12345": {
                "mark_price": 110.0,
                "ts_epoch": 105.0,
                "is_order_action": False,
                "broker_api_called": False,
                "real_order_id": None,
            }
        },
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def test_paper_mtm_pnl_schema_contract_is_safe():
    contract = paper_mtm_pnl_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["tracker_type"] == "PAPER_MTM_PNL_TRACKER"
    assert "PAPER_POSITION_LEDGER" in contract["consumes"]
    assert "CONTROLLED_MARK" in contract["consumes"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "VALUED" in contract["statuses"]
    assert "DEGRADED_MISSING_MARK" in contract["statuses"]
    assert "unrealized_pnl" in contract["required_row_keys"]
    assert "total_unrealized_pnl" in contract["required_summary_keys"]


def test_paper_mtm_pnl_values_long_position_from_controlled_mark():
    result = build_paper_mtm_pnl(
        ledger=_ledger(_position()),
        marks=_marks(),
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is True
    assert payload["status"] == "VALUED"
    assert payload["rows"][0]["row_status"] == "VALUED"
    assert payload["rows"][0]["mark_price"] == 110.0
    assert payload["rows"][0]["unrealized_pnl"] == 100.0
    assert payload["rows"][0]["notional_value"] == 1100.0
    assert payload["summary"]["total_unrealized_pnl"] == 100.0
    assert payload["summary"]["gross_notional_value"] == 1100.0
    assert payload["paper_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["rows"][0]["real_order_id"] is None


def test_paper_mtm_pnl_values_short_position_from_controlled_mark():
    short_position = _position(
        key="54321",
        position_key="54321",
        instrument_token=54321,
        net_quantity=-5,
        side="SHORT",
        average_entry_price=200.0,
        last_fill_price=200.0,
    )
    marks = _marks(
        marks={
            "54321": {
                "mark_price": 180.0,
                "ts_epoch": 105.0,
                "is_order_action": False,
                "broker_api_called": False,
                "real_order_id": None,
            }
        }
    )

    result = build_paper_mtm_pnl(
        ledger=_ledger(short_position),
        marks=marks,
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is True
    assert payload["status"] == "VALUED"
    assert payload["rows"][0]["side"] == "SHORT"
    assert payload["rows"][0]["unrealized_pnl"] == 100.0
    assert payload["rows"][0]["notional_value"] == 900.0
    assert payload["summary"]["net_quantity_abs"] == 5


def test_paper_mtm_pnl_degrades_when_open_position_missing_mark():
    result = build_paper_mtm_pnl(
        ledger=_ledger(_position()),
        marks=_marks(marks={}),
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is False
    assert payload["status"] == "DEGRADED_MISSING_MARK"
    assert payload["rows"][0]["row_status"] == "MISSING_MARK"
    assert payload["rows"][0]["unrealized_pnl"] is None
    assert payload["summary"]["missing_mark_count"] == 1
    assert "MISSING_MARK_FOR_OPEN_POSITION" in payload["warnings"]
    assert payload["broker_api_called"] is False


def test_paper_mtm_pnl_treats_flat_position_as_zero_notional_without_mark():
    flat_position = _position(net_quantity=0, side="FLAT", average_entry_price=None)
    result = build_paper_mtm_pnl(
        ledger=_ledger(flat_position),
        marks=_marks(marks={}),
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is True
    assert payload["status"] == "VALUED"
    assert payload["rows"][0]["row_status"] == "FLAT"
    assert payload["rows"][0]["unrealized_pnl"] == 0.0
    assert payload["summary"]["open_position_count"] == 0
    assert payload["summary"]["total_unrealized_pnl"] == 0.0


def test_paper_mtm_pnl_blocks_stale_controlled_mark():
    result = build_paper_mtm_pnl(
        ledger=_ledger(_position()),
        marks=_marks(ts_epoch=90.0),
        now_epoch=106.0,
        max_mark_age_sec=5.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is False
    assert payload["status"] == "BLOCKED"
    assert "CONTROLLED_MARK_STALE" in payload["blockers"]
    assert payload["summary"]["total_unrealized_pnl"] == 0.0
    assert payload["evidence"]["mark_age_sec"] == 16.0
    assert payload["broker_api_called"] is False


def test_paper_mtm_pnl_blocks_non_controlled_mark_source():
    result = build_paper_mtm_pnl(
        ledger=_ledger(_position()),
        marks=_marks(source="LIVE_BROKER_MARK"),
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is False
    assert payload["status"] == "BLOCKED"
    assert "CONTROLLED_MARK_SOURCE_REQUIRED" in payload["blockers"]
    assert payload["evidence"]["controlled_mark_only"] is True


def test_paper_mtm_pnl_blocks_unsafe_ledger_flags():
    ledger = _ledger(_position())
    ledger["broker_api_called"] = True
    ledger["real_order_id"] = "real-123"

    result = build_paper_mtm_pnl(
        ledger=ledger,
        marks=_marks(),
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_POSITION_LEDGER_BROKER_API_CALLED" in payload["blockers"]
    assert "PAPER_POSITION_LEDGER_REAL_ORDER_ID_PRESENT" in payload["blockers"]
    assert payload["paper_only"] is True
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_paper_mtm_pnl_blocks_unsafe_mark_flags():
    marks = _marks()
    marks["is_order_action"] = True
    marks["real_order_id"] = "real-123"

    result = build_paper_mtm_pnl(
        ledger=_ledger(_position()),
        marks=marks,
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is False
    assert payload["status"] == "BLOCKED"
    assert "CONTROLLED_MARK_ORDER_FLAG_UNSAFE" in payload["blockers"]
    assert "CONTROLLED_MARK_REAL_ORDER_ID_PRESENT" in payload["blockers"]
    assert payload["summary"]["broker_api_called"] is False


def test_paper_mtm_pnl_blocks_unsafe_nested_mark_row():
    marks = _marks()
    marks["marks"]["12345"]["broker_api_called"] = True

    result = build_paper_mtm_pnl(
        ledger=_ledger(_position()),
        marks=marks,
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is False
    assert payload["status"] == "BLOCKED"
    assert "CONTROLLED_MARK_ROW_BROKER_API_CALLED:12345" in payload["blockers"]


def test_paper_mtm_pnl_empty_ledger_is_safe_empty_state():
    result = build_paper_mtm_pnl(
        ledger=_ledger(),
        marks=_marks(marks={}),
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["valued"] is True
    assert payload["status"] == "EMPTY"
    assert payload["rows"] == []
    assert payload["summary"]["position_count"] == 0
    assert "PAPER_POSITION_LEDGER_EMPTY" in payload["warnings"]


def test_paper_mtm_pnl_does_not_emit_realized_pnl_fees_or_slippage():
    result = build_paper_mtm_pnl(
        ledger=_ledger(_position()),
        marks=_marks(),
        now_epoch=106.0,
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert "realized_pnl" not in payload["summary"]
    assert "fees" not in payload["summary"]
    assert "slippage" not in payload["summary"]
    assert "realized_pnl" not in payload["rows"][0]
    assert "fees" not in payload["rows"][0]
    assert "slippage" not in payload["rows"][0]
