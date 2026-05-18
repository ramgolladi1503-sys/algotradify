from __future__ import annotations

import json

from paper_trading import (
    PaperEvent,
    PaperEventType,
    append_paper_event,
    load_paper_events,
    paper_event_journal_schema_contract,
    validate_paper_event,
)


def _event(**overrides):
    payload = {
        "event_id": "event-1",
        "cycle_id": "cycle-1",
        "event_sequence": 1,
        "candidate_id": "candidate-1",
        "strategy_id": "orb_retest",
        "paper_order_intent_id": "intent-1",
        "paper_order_id": "order-1",
        "event_type": "PAPER_ORDER_INTENT_CREATED",
        "ts_epoch": 100.0,
        "idempotency_key": "cycle-1:intent-1:created",
        "payload": {"source": "test"},
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def test_paper_event_journal_schema_contract_is_safe():
    contract = paper_event_journal_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["journal_type"] == "CANONICAL_PAPER_EVENT_JOURNAL"
    assert contract["append_only"] is True
    assert contract["load_blocks_on_corrupt_rows"] is True
    assert "PAPER_ORDER_FILLED" in contract["event_types"]
    assert "event_id" in contract["required_event_keys"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def test_valid_event_append(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"

    result = append_paper_event(journal_path, _event())
    payload = result.to_dict()

    assert payload["appended"] is True
    assert payload["event_count"] == 1
    assert payload["event"]["event_type"] == "PAPER_ORDER_INTENT_CREATED"
    assert payload["paper_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert journal_path.read_text(encoding="utf-8").count("\n") == 1


def test_dataclass_event_append_normalizes_safely(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    event = PaperEvent(
        event_id="event-1",
        cycle_id="cycle-1",
        event_sequence=1,
        candidate_id="candidate-1",
        strategy_id="orb_retest",
        paper_order_intent_id="intent-1",
        paper_order_id="order-1",
        event_type=PaperEventType.PAPER_ORDER_ACCEPTED,
        ts_epoch=100.0,
        idempotency_key="cycle-1:intent-1:accepted",
        payload={"accepted": True},
    )

    result = append_paper_event(journal_path, event)

    assert result.appended is True
    assert result.event is not None
    assert result.event["event_type"] == "PAPER_ORDER_ACCEPTED"
    assert result.event["paper_only"] is True
    assert result.event["is_order_action"] is False


def test_duplicate_event_id_rejected(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    assert append_paper_event(journal_path, _event()).appended is True

    result = append_paper_event(
        journal_path,
        _event(idempotency_key="cycle-1:other-key", payload={"source": "different"}),
    )

    assert result.appended is False
    assert result.blockers == ["PAPER_EVENT_DUPLICATE_EVENT_ID"]
    assert journal_path.read_text(encoding="utf-8").count("\n") == 1


def test_duplicate_idempotency_key_deterministic_noop(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    event = _event()
    assert append_paper_event(journal_path, event).appended is True

    result = append_paper_event(journal_path, dict(event))

    assert result.appended is False
    assert result.blockers == []
    assert result.warnings == ["PAPER_EVENT_DUPLICATE_IDEMPOTENCY_KEY_NOOP"]
    assert journal_path.read_text(encoding="utf-8").count("\n") == 1


def test_conflicting_idempotency_key_blocked(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    assert append_paper_event(journal_path, _event()).appended is True

    result = append_paper_event(
        journal_path,
        _event(event_id="event-2", payload={"source": "conflict"}),
    )

    assert result.appended is False
    assert result.blockers == ["PAPER_EVENT_CONFLICTING_IDEMPOTENCY_KEY"]
    assert journal_path.read_text(encoding="utf-8").count("\n") == 1


def test_unsafe_order_flag_blocked(tmp_path):
    result = append_paper_event(tmp_path / "paper-events.jsonl", _event(is_order_action=True))

    assert result.appended is False
    assert "PAPER_EVENT_UNSAFE_ORDER_ACTION_FLAG" in result.blockers


def test_broker_api_flag_blocked(tmp_path):
    result = append_paper_event(tmp_path / "paper-events.jsonl", _event(broker_api_called=True))

    assert result.appended is False
    assert "PAPER_EVENT_UNSAFE_BROKER_API_FLAG" in result.blockers


def test_real_order_id_blocked(tmp_path):
    result = append_paper_event(tmp_path / "paper-events.jsonl", _event(real_order_id="real-123"))

    assert result.appended is False
    assert "PAPER_EVENT_UNSAFE_REAL_ORDER_ID" in result.blockers


def test_missing_required_fields_blocked():
    event = _event(cycle_id="", event_type=None, ts_epoch=None)

    blockers = validate_paper_event(event)

    assert "PAPER_EVENT_MISSING_CYCLE_ID" in blockers
    assert "PAPER_EVENT_MISSING_EVENT_TYPE" in blockers
    assert "PAPER_EVENT_MISSING_TS_EPOCH" in blockers


def test_journal_is_append_only(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    first = _event(event_id="event-1", idempotency_key="key-1", event_sequence=1)
    second = _event(event_id="event-2", idempotency_key="key-2", event_sequence=2)

    assert append_paper_event(journal_path, first).appended is True
    assert append_paper_event(journal_path, second).appended is True
    loaded = load_paper_events(journal_path)

    assert [event["event_id"] for event in loaded.events] == ["event-1", "event-2"]
    assert journal_path.read_text(encoding="utf-8").count("\n") == 2


def test_corrupt_jsonl_line_blocked_deterministically(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    journal_path.write_text('{"event_id":"event-1"}\nnot-json\n', encoding="utf-8")

    result = load_paper_events(journal_path)

    assert result.appended is False
    assert "PAPER_EVENT_JOURNAL_CORRUPT_JSONL_LINE_2" in result.blockers
    assert any("LINE_1_PAPER_EVENT_MISSING_CYCLE_ID" == blocker for blocker in result.blockers)


def test_append_blocks_when_existing_journal_is_corrupt(tmp_path):
    journal_path = tmp_path / "paper-events.jsonl"
    journal_path.write_text("not-json\n", encoding="utf-8")

    result = append_paper_event(journal_path, _event())

    assert result.appended is False
    assert result.blockers == ["PAPER_EVENT_JOURNAL_CORRUPT_JSONL_LINE_1"]
    assert journal_path.read_text(encoding="utf-8") == "not-json\n"


def test_same_input_produces_same_journal(tmp_path):
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    events = [
        _event(event_id="event-1", idempotency_key="key-1", event_sequence=1),
        _event(event_id="event-2", idempotency_key="key-2", event_sequence=2, event_type="PAPER_ORDER_ACCEPTED"),
    ]

    for event in events:
        append_paper_event(first_path, dict(event))
        append_paper_event(second_path, dict(event))

    assert first_path.read_text(encoding="utf-8") == second_path.read_text(encoding="utf-8")
    first_lines = [json.loads(line) for line in first_path.read_text(encoding="utf-8").splitlines()]
    second_lines = [json.loads(line) for line in second_path.read_text(encoding="utf-8").splitlines()]
    assert first_lines == second_lines
