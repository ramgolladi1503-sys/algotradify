from __future__ import annotations

import json
import subprocess
import sys

from paper_trading import append_paper_event
from paper_trading.rebuild import (
    PaperJournalRebuildStatus,
    paper_journal_rebuild_schema_contract,
    rebuild_paper_journal,
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
        "event_type": "PAPER_ORDER_ACCEPTED",
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


def test_rebuild_schema_contract_exposes_safe_flags():
    contract = paper_journal_rebuild_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["rebuild_type"] == "PAPER_STATE_REBUILD_CLI"
    assert contract["pipeline"] == ["load_paper_events", "guard_paper_event_ordering", "reduce_paper_events"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert contract["cli_exit_codes"] == {"REBUILT": 0, "EMPTY": 0, "BLOCKED": 2}
    assert "state" in contract["required_result_keys"]
    assert "blockers" in contract["required_result_keys"]


def test_missing_journal_path_is_blocked():
    payload = rebuild_paper_journal(None).to_dict()

    assert payload["status"] == "BLOCKED"
    assert payload["rebuilt"] is False
    assert payload["blockers"] == ["PAPER_JOURNAL_REBUILD_PATH_REQUIRED"]
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_missing_journal_file_rebuilds_empty_safely(tmp_path):
    journal_path = tmp_path / "missing-events.jsonl"

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "EMPTY"
    assert payload["rebuilt"] is True
    assert payload["event_count"] == 0
    assert payload["ordered_event_count"] == 0
    assert payload["state"]["summary"]["event_count"] == 0
    assert payload["warnings"] == ["PAPER_EVENT_ORDERING_EMPTY_EVENT_LIST", "PAPER_REDUCER_EMPTY_EVENT_LIST"]
    assert payload["paper_only"] is True
    assert payload["read_only"] is True


def test_valid_ordered_journal_rebuilds_deterministic_state(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    append_paper_event(journal_path, _event("event-1", sequence=1, event_type="PAPER_ORDER_ACCEPTED"))
    append_paper_event(journal_path, _event("event-2", sequence=2, event_type="PAPER_ORDER_OPENED"))

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "REBUILT"
    assert payload["rebuilt"] is True
    assert payload["event_count"] == 2
    assert payload["ordered_event_count"] == 2
    assert payload["ordering"]["status"] == "VALID"
    assert payload["reducer"]["status"] == "REDUCED"
    assert payload["state"]["summary"]["event_count"] == 2
    assert list(payload["state"]["orders"].values())[-1]["status"] == "OPEN"
    assert payload["state"]["paper_only"] is True
    assert payload["state"]["read_only"] is True


def test_same_journal_rebuilt_twice_returns_same_state(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    append_paper_event(journal_path, _event("event-1", sequence=1, event_type="PAPER_ORDER_ACCEPTED"))
    append_paper_event(journal_path, _event("event-2", sequence=2, event_type="PAPER_ORDER_FILLED"))

    first = rebuild_paper_journal(journal_path).to_dict()
    second = rebuild_paper_journal(journal_path).to_dict()

    assert first["state"] == second["state"]
    assert first["ordering"] == second["ordering"]
    assert first["reducer"] == second["reducer"]


def test_corrupt_jsonl_line_blocks_rebuild(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    journal_path.write_text("not-json\n", encoding="utf-8")

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "BLOCKED"
    assert payload["rebuilt"] is False
    assert "PAPER_JOURNAL_REBUILD_JOURNAL_PAPER_EVENT_JOURNAL_CORRUPT_JSONL_LINE_1" in payload["blockers"]
    assert payload["ordering"] == {}
    assert payload["reducer"] == {}


def test_unsafe_historical_event_blocks_rebuild(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    unsafe_event = _event(broker_api_called=True)
    journal_path.write_text(json.dumps(unsafe_event) + "\n", encoding="utf-8")

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("PAPER_EVENT_UNSAFE_BROKER_API_FLAG" in blocker for blocker in payload["blockers"])


def test_sequence_gap_blocks_rebuild(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    append_paper_event(journal_path, _event("event-1", sequence=1))
    append_paper_event(journal_path, _event("event-2", sequence=3))

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("PAPER_EVENT_SEQUENCE_GAP_OR_REGRESSION" in blocker for blocker in payload["blockers"])


def test_timestamp_regression_blocks_rebuild(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    append_paper_event(journal_path, _event("event-1", sequence=1, ts_epoch=100.0))
    append_paper_event(journal_path, _event("event-2", sequence=2, ts_epoch=99.0))

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("PAPER_EVENT_TS_EPOCH_REGRESSION" in blocker for blocker in payload["blockers"])


def test_duplicate_event_id_blocks_rebuild(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    first = _event("event-1", sequence=1, idempotency_key="key-1")
    duplicate = _event("event-1", sequence=2, idempotency_key="key-2")
    journal_path.write_text(json.dumps(first) + "\n" + json.dumps(duplicate) + "\n", encoding="utf-8")

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("DUPLICATE_EVENT_ID" in blocker for blocker in payload["blockers"])


def test_duplicate_idempotency_key_blocks_rebuild(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    first = _event("event-1", sequence=1, idempotency_key="same-key")
    duplicate = _event("event-2", sequence=2, idempotency_key="same-key")
    journal_path.write_text(json.dumps(first) + "\n" + json.dumps(duplicate) + "\n", encoding="utf-8")

    payload = rebuild_paper_journal(journal_path).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("IDEMPOTENCY_KEY" in blocker for blocker in payload["blockers"])


def test_rebuild_output_has_no_order_controls(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    append_paper_event(journal_path, _event())

    payload_text = json.dumps(rebuild_paper_journal(journal_path).to_dict()).lower()

    assert "submit" not in payload_text
    assert "modify" not in payload_text
    assert "cancel_order" not in payload_text
    assert "exit_order" not in payload_text
    assert "place_order" not in payload_text


def test_cli_json_exits_zero_on_empty_journal(tmp_path):
    journal_path = tmp_path / "missing-events.jsonl"

    completed = subprocess.run(
        [sys.executable, "scripts/rebuild_paper_journal.py", "--journal", str(journal_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "EMPTY"
    assert payload["paper_only"] is True
    assert payload["read_only"] is True


def test_cli_exits_two_on_blocked_journal(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    journal_path.write_text("not-json\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "scripts/rebuild_paper_journal.py", "--journal", str(journal_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "BLOCKED"
    assert payload["blockers"]
