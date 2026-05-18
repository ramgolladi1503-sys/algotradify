from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy

from paper_trading import append_paper_event
from paper_trading.rebuild import rebuild_paper_journal
from paper_trading.reconciliation import (
    paper_state_reconciliation_schema_contract,
    reconcile_paper_state,
)


def _event(event_id="event-1", sequence=1, cycle_id="cycle-1", ts_epoch=100.0, **overrides):
    payload = {
        "schema_version": "1.0",
        "event_id": event_id,
        "cycle_id": cycle_id,
        "event_sequence": sequence,
        "candidate_id": "candidate-1",
        "strategy_id": "orb_retest",
        "paper_order_intent_id": "intent-1",
        "paper_order_id": "order-1",
        "event_type": "PAPER_ORDER_OPENED",
        "ts_epoch": ts_epoch,
        "idempotency_key": f"{cycle_id}:{event_id}",
        "payload": {"source": "test"},
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _rebuild_payload(tmp_path, *events):
    journal_path = tmp_path / "paper-events.jsonl"
    for event in events:
        append_paper_event(journal_path, event)
    return rebuild_paper_journal(journal_path).to_dict()


def _matching_state(tmp_path):
    rebuild = _rebuild_payload(tmp_path, _event("event-1", sequence=1))
    assert rebuild["status"] == "REBUILT"
    return rebuild, deepcopy(rebuild["state"])


def test_schema_contract_exposes_safe_flags():
    contract = paper_state_reconciliation_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["report_type"] == "PAPER_STATE_RECONCILIATION_REPORT"
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert contract["cli_exit_codes"] == {"MATCH": 0, "EMPTY": 0, "DRIFT": 1, "BLOCKED": 2}
    assert "orders" in contract["compared_state_keys"]
    assert "positions" in contract["compared_state_keys"]


def test_empty_rebuilt_state_with_no_observed_state_returns_empty(tmp_path):
    rebuild = rebuild_paper_journal(tmp_path / "missing-events.jsonl").to_dict()

    payload = reconcile_paper_state(rebuild, None).to_dict()

    assert payload["status"] == "EMPTY"
    assert payload["matched"] is True
    assert payload["drift_count"] == 0
    assert payload["warnings"] == ["PAPER_STATE_RECONCILIATION_EMPTY_STATE"]
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_matching_rebuilt_and_observed_states_returns_match(tmp_path):
    rebuild, observed = _matching_state(tmp_path)

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "MATCH"
    assert payload["matched"] is True
    assert payload["drift_count"] == 0
    assert payload["drifts"] == []
    assert payload["summary"]["status"] == "MATCH"


def test_order_status_mismatch_returns_drift(tmp_path):
    rebuild, observed = _matching_state(tmp_path)
    order_key = next(iter(observed["orders"]))
    observed["orders"][order_key]["status"] = "FILLED"

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "DRIFT"
    assert payload["matched"] is False
    assert payload["drift_count"] >= 1
    assert any(drift["path"].endswith("status") for drift in payload["drifts"])


def test_position_quantity_mismatch_returns_drift(tmp_path):
    rebuild = _rebuild_payload(
        tmp_path,
        _event(
            "event-1",
            sequence=1,
            event_type="PAPER_POSITION_OPENED",
            payload={"position_key": "NIFTY", "net_quantity": 10, "average_entry_price": 100.0},
        ),
    )
    observed = deepcopy(rebuild["state"])
    observed["positions"]["NIFTY"]["net_quantity"] = 5

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "DRIFT"
    assert any("net_quantity" in drift["path"] for drift in payload["drifts"])


def test_summary_mismatch_returns_drift(tmp_path):
    rebuild, observed = _matching_state(tmp_path)
    observed["summary"]["event_count"] = 999

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "DRIFT"
    assert any(drift["path"] == "summary.event_count" for drift in payload["drifts"])


def test_applied_event_ids_mismatch_returns_drift(tmp_path):
    rebuild, observed = _matching_state(tmp_path)
    observed["applied_event_ids"] = ["other-event"]

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "DRIFT"
    assert any(drift["path"] == "applied_event_ids" for drift in payload["drifts"])


def test_last_event_mismatch_returns_drift(tmp_path):
    rebuild, observed = _matching_state(tmp_path)
    observed["last_event"] = {"event_id": "other-event"}

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "DRIFT"
    assert any(drift["path"].startswith("last_event") for drift in payload["drifts"])


def test_missing_rebuild_result_blocks():
    payload = reconcile_paper_state(None, None).to_dict()

    assert payload["status"] == "BLOCKED"
    assert payload["matched"] is False
    assert payload["blockers"] == ["PAPER_STATE_RECONCILIATION_REBUILD_RESULT_REQUIRED"]


def test_blocked_rebuild_result_blocks():
    rebuild = {"status": "BLOCKED", "state": {}}

    payload = reconcile_paper_state(rebuild, None).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_STATE_RECONCILIATION_REBUILD_RESULT_BLOCKED" in payload["blockers"]


def test_unsafe_rebuilt_state_flags_block(tmp_path):
    rebuild, _observed = _matching_state(tmp_path)
    rebuild["state"]["broker_api_called"] = True

    payload = reconcile_paper_state(rebuild, None).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_STATE_RECONCILIATION_REBUILT_STATE_UNSAFE_BROKER_API_FLAG" in payload["blockers"]


def test_unsafe_observed_state_flags_block(tmp_path):
    rebuild, observed = _matching_state(tmp_path)
    observed["is_order_action"] = True

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_STATE_RECONCILIATION_OBSERVED_STATE_UNSAFE_ORDER_ACTION_FLAG" in payload["blockers"]


def test_missing_required_state_keys_block(tmp_path):
    rebuild, observed = _matching_state(tmp_path)
    del observed["orders"]

    payload = reconcile_paper_state(rebuild, observed).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_STATE_RECONCILIATION_OBSERVED_STATE_MISSING_ORDERS" in payload["blockers"]


def test_reconciliation_report_has_no_order_controls(tmp_path):
    rebuild, observed = _matching_state(tmp_path)

    payload_text = json.dumps(reconcile_paper_state(rebuild, observed).to_dict()).lower()

    assert "submit" not in payload_text
    assert "modify" not in payload_text
    assert "cancel_order" not in payload_text
    assert "exit_order" not in payload_text
    assert "place_order" not in payload_text


def test_cli_exits_zero_on_match(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    append_paper_event(journal_path, _event("event-1", sequence=1))
    observed_path = tmp_path / "observed.json"
    observed_path.write_text(json.dumps(rebuild_paper_journal(journal_path).to_dict()["state"]), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "scripts/reconcile_paper_state.py", "--journal", str(journal_path), "--observed-state", str(observed_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "MATCH"


def test_cli_exits_zero_on_empty(tmp_path):
    journal_path = tmp_path / "missing-events.jsonl"

    completed = subprocess.run(
        [sys.executable, "scripts/reconcile_paper_state.py", "--journal", str(journal_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "EMPTY"


def test_cli_exits_one_on_drift(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    append_paper_event(journal_path, _event("event-1", sequence=1))
    observed = rebuild_paper_journal(journal_path).to_dict()["state"]
    order_key = next(iter(observed["orders"]))
    observed["orders"][order_key]["status"] = "FILLED"
    observed_path = tmp_path / "observed.json"
    observed_path.write_text(json.dumps(observed), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "scripts/reconcile_paper_state.py", "--journal", str(journal_path), "--observed-state", str(observed_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "DRIFT"


def test_cli_exits_two_on_blocked(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    journal_path.write_text("not-json\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "scripts/reconcile_paper_state.py", "--journal", str(journal_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "BLOCKED"
