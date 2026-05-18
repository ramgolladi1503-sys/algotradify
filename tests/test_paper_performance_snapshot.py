from __future__ import annotations

from paper_trading import (
    build_paper_performance_snapshot,
    paper_performance_snapshot_schema_contract,
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


def _position_ledger(*positions, **overrides):
    payload = {
        "schema_version": "1.0",
        "ledger_type": "PAPER_POSITION_LEDGER",
        "positions": {str(position["position_key"]): position for position in positions},
        "order_fills": {},
        "last_event": None,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _mtm(**overrides):
    payload = {
        "schema_version": "1.0",
        "tracker_type": "PAPER_MTM_PNL_TRACKER",
        "valued": True,
        "status": "VALUED",
        "rows": [],
        "summary": {
            "position_count": 1,
            "open_position_count": 1,
            "valued_position_count": 1,
            "missing_mark_count": 0,
            "total_unrealized_pnl": 125.0,
            "gross_notional_value": 1125.0,
            "net_quantity_abs": 10,
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "blockers": [],
        "warnings": [],
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _realized(**overrides):
    payload = {
        "schema_version": "1.0",
        "ledger_type": "PAPER_REALIZED_PNL_LEDGER",
        "events": [],
        "applied_fill_keys": [],
        "summary": {
            "event_count": 2,
            "winning_event_count": 1,
            "losing_event_count": 1,
            "flat_event_count": 0,
            "total_realized_pnl": 75.0,
            "total_realized_quantity": 6,
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _slippage(**overrides):
    payload = {
        "schema_version": "1.0",
        "report_type": "PAPER_SLIPPAGE_FILL_QUALITY",
        "events": [],
        "applied_fill_keys": [],
        "order_fills": {},
        "summary": {
            "event_count": 3,
            "measured_quantity": 10,
            "total_slippage_amount": 8.0,
            "average_slippage_per_unit": 0.8,
            "weighted_average_slippage_bps": 80.0,
            "favorable_event_count": 1,
            "unfavorable_event_count": 2,
            "flat_event_count": 0,
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def test_paper_performance_snapshot_schema_contract_is_safe():
    contract = paper_performance_snapshot_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["snapshot_type"] == "PAPER_PERFORMANCE_SNAPSHOT"
    assert "PAPER_POSITION_LEDGER" in contract["consumes"]
    assert "PAPER_MTM_PNL_TRACKER" in contract["consumes"]
    assert "PAPER_REALIZED_PNL_LEDGER" in contract["consumes"]
    assert "PAPER_SLIPPAGE_FILL_QUALITY" in contract["consumes"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "combined_pnl" in contract["required_summary_keys"]


def test_paper_performance_snapshot_ready_aggregates_all_sources():
    result = build_paper_performance_snapshot(
        position_ledger=_position_ledger(_position()),
        mtm_pnl=_mtm(),
        realized_pnl=_realized(),
        slippage=_slippage(),
        ts_epoch=110.0,
    )
    payload = result.to_dict()
    snapshot = payload["snapshot"]

    assert payload["created"] is True
    assert payload["status"] == "READY"
    assert snapshot["status"] == "READY"
    assert snapshot["summary"]["position_count"] == 1
    assert snapshot["summary"]["open_position_count"] == 1
    assert snapshot["summary"]["total_unrealized_pnl"] == 125.0
    assert snapshot["summary"]["total_realized_pnl"] == 75.0
    assert snapshot["summary"]["combined_pnl"] == 200.0
    assert snapshot["summary"]["gross_notional_value"] == 1125.0
    assert snapshot["summary"]["slippage_event_count"] == 3
    assert snapshot["summary"]["total_slippage_amount"] == 8.0
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert snapshot["is_order_action"] is False
    assert snapshot["broker_api_called"] is False
    assert snapshot["real_order_id"] is None


def test_paper_performance_snapshot_degrades_when_optional_sources_missing():
    result = build_paper_performance_snapshot(
        position_ledger=_position_ledger(_position()),
        mtm_pnl=None,
        realized_pnl=None,
        slippage=None,
        ts_epoch=110.0,
    )
    payload = result.to_dict()
    snapshot = payload["snapshot"]

    assert payload["created"] is True
    assert payload["status"] == "DEGRADED"
    assert snapshot["diagnostics"]["missing_sources"] == ["mtm_pnl", "realized_pnl", "slippage"]
    assert "PAPER_MTM_PNL_TRACKER_MISSING" in payload["warnings"]
    assert snapshot["summary"]["combined_pnl"] == 0.0
    assert snapshot["positions"]["open_position_count"] == 1


def test_paper_performance_snapshot_empty_when_no_positions_or_metrics():
    result = build_paper_performance_snapshot(
        position_ledger=_position_ledger(),
        mtm_pnl=_mtm(summary={}),
        realized_pnl=_realized(summary={}),
        slippage=_slippage(summary={}),
        ts_epoch=110.0,
    )
    payload = result.to_dict()

    assert payload["created"] is True
    assert payload["status"] == "EMPTY"
    assert payload["snapshot"]["summary"]["position_count"] == 0
    assert payload["snapshot"]["summary"]["combined_pnl"] == 0.0
    assert payload["snapshot"]["summary"]["slippage_event_count"] == 0


def test_paper_performance_snapshot_degrades_when_mtm_source_degraded():
    result = build_paper_performance_snapshot(
        position_ledger=_position_ledger(_position()),
        mtm_pnl=_mtm(status="DEGRADED_MISSING_MARK"),
        realized_pnl=_realized(),
        slippage=_slippage(),
        ts_epoch=110.0,
    )
    payload = result.to_dict()

    assert payload["created"] is True
    assert payload["status"] == "DEGRADED"
    assert payload["snapshot"]["diagnostics"]["degraded_sources"] == ["mtm_pnl"]
    assert payload["snapshot"]["source_statuses"]["mtm_pnl"]["status"] == "DEGRADED_MISSING_MARK"


def test_paper_performance_snapshot_blocks_missing_position_ledger():
    result = build_paper_performance_snapshot(
        position_ledger=None,
        mtm_pnl=_mtm(),
        realized_pnl=_realized(),
        slippage=_slippage(),
        ts_epoch=110.0,
    )
    payload = result.to_dict()

    assert payload["created"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_POSITION_LEDGER_REQUIRED" in payload["blockers"]
    assert payload["snapshot"] is None
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["broker_api_called"] is False


def test_paper_performance_snapshot_blocks_unsafe_position_ledger_flags():
    ledger = _position_ledger(_position())
    ledger["broker_api_called"] = True
    ledger["real_order_id"] = "real-123"

    result = build_paper_performance_snapshot(
        position_ledger=ledger,
        mtm_pnl=_mtm(),
        realized_pnl=_realized(),
        slippage=_slippage(),
        ts_epoch=110.0,
    )
    payload = result.to_dict()

    assert payload["created"] is False
    assert "PAPER_POSITION_LEDGER_BROKER_API_CALLED" in payload["blockers"]
    assert "PAPER_POSITION_LEDGER_REAL_ORDER_ID_PRESENT" in payload["blockers"]
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_paper_performance_snapshot_blocks_wrong_optional_source_type():
    bad_slippage = _slippage(report_type="WRONG")

    result = build_paper_performance_snapshot(
        position_ledger=_position_ledger(_position()),
        mtm_pnl=_mtm(),
        realized_pnl=_realized(),
        slippage=bad_slippage,
        ts_epoch=110.0,
    )
    payload = result.to_dict()

    assert payload["created"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_SLIPPAGE_FILL_QUALITY_TYPE_REQUIRED" in payload["blockers"]


def test_paper_performance_snapshot_does_not_expose_order_controls():
    result = build_paper_performance_snapshot(
        position_ledger=_position_ledger(_position()),
        mtm_pnl=_mtm(),
        realized_pnl=_realized(),
        slippage=_slippage(),
        ts_epoch=110.0,
    )
    payload = result.to_dict()
    snapshot = payload["snapshot"]

    forbidden = {"submit", "modify", "cancel", "exit", "place_order", "broker_order_id"}
    assert forbidden.isdisjoint(payload.keys())
    assert forbidden.isdisjoint(snapshot.keys())
    assert forbidden.isdisjoint(snapshot["summary"].keys())
    assert snapshot["read_only"] is True
    assert snapshot["summary"]["read_only"] is True
    assert snapshot["positions"]["read_only"] is True
    assert snapshot["pnl"]["read_only"] is True
    assert snapshot["slippage"]["read_only"] is True


def test_paper_performance_snapshot_keeps_safe_flags_in_nested_blocks():
    result = build_paper_performance_snapshot(
        position_ledger=_position_ledger(_position()),
        mtm_pnl=_mtm(),
        realized_pnl=_realized(),
        slippage=_slippage(),
        ts_epoch=110.0,
    )
    snapshot = result.to_dict()["snapshot"]

    for key in ["summary", "positions", "pnl", "slippage", "diagnostics", "source_statuses"]:
        assert snapshot[key]["paper_only"] is True
        assert snapshot[key]["read_only"] is True
        assert snapshot[key]["is_order_action"] is False
        assert snapshot[key]["broker_api_called"] is False
        assert snapshot[key]["real_order_id"] is None
