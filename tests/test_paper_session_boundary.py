from __future__ import annotations

import json

from paper_trading.persistence import write_paper_evidence_record
from paper_trading.session_boundary import (
    PAPER_SESSION_BOUNDARY_RECORD_TYPE,
    build_paper_session_boundary_record,
    build_paper_session_id,
    load_paper_session_boundaries,
    mark_paper_session_boundary,
    paper_session_boundary_schema_contract,
)


def _metadata(**overrides):
    payload = {
        "source": "test",
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def test_schema_contract_exposes_safe_flags_and_allowed_boundary_types():
    contract = paper_session_boundary_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["record_type"] == PAPER_SESSION_BOUNDARY_RECORD_TYPE
    assert contract["allowed_boundary_types"] == ["SESSION_START", "SESSION_END", "RESET_MARKER"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "reset_marker_is_non_destructive" in contract["scope_boundary"]
    assert "no_delete" in contract["scope_boundary"]
    assert "no_truncate" in contract["scope_boundary"]
    assert "no_runtime_wiring" in contract["scope_boundary"]


def test_build_paper_session_id_is_deterministic():
    first = build_paper_session_id(trading_date="2026-05-18", session_label="AM")
    second = build_paper_session_id(trading_date="2026-05-18", session_label="AM")
    third = build_paper_session_id(trading_date="2026-05-18", session_label="PM")

    assert first == second
    assert first.startswith("paper-session-")
    assert first != third


def test_valid_session_start_boundary_builds_safely():
    session_id = build_paper_session_id(trading_date="2026-05-18", session_label="AM")

    payload = build_paper_session_boundary_record(
        session_id=session_id,
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        reason="start paper session",
        metadata=_metadata(),
    ).to_dict()

    assert payload["status"] == "BUILT"
    assert payload["record"]["boundary_type"] == "SESSION_START"
    assert payload["record"]["session_id"] == session_id
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_valid_session_end_boundary_builds_safely():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="SESSION_END",
        created_at_epoch=120.0,
        reason="end paper session",
        metadata=_metadata(),
    ).to_dict()

    assert payload["status"] == "BUILT"
    assert payload["record"]["boundary_type"] == "SESSION_END"


def test_valid_reset_marker_boundary_builds_safely():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="RESET_MARKER",
        created_at_epoch=130.0,
        reason="reset before next session",
        metadata=_metadata(reset_scope="future_only"),
    ).to_dict()

    assert payload["status"] == "BUILT"
    assert payload["record"]["boundary_type"] == "RESET_MARKER"
    assert payload["record"]["metadata"]["reset_scope"] == "future_only"


def test_missing_session_id_blocks_boundary_build():
    payload = build_paper_session_boundary_record(
        session_id="",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        metadata=_metadata(),
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_SESSION_BOUNDARY_SESSION_ID_REQUIRED" in payload["blockers"]


def test_invalid_boundary_type_blocks():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="DELETE_ALL",
        created_at_epoch=100.0,
        metadata=_metadata(),
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_SESSION_BOUNDARY_TYPE_INVALID" in payload["blockers"]


def test_unsafe_metadata_order_action_flag_blocks():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        metadata=_metadata(is_order_action=True),
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("UNSAFE_ORDER_ACTION_FLAG" in blocker for blocker in payload["blockers"])


def test_broker_api_called_metadata_blocks():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        metadata=_metadata(broker_api_called=True),
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("BROKER_API_CALLED" in blocker for blocker in payload["blockers"])


def test_real_order_id_metadata_blocks():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        metadata=_metadata(real_order_id="real-1"),
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("REAL_ORDER_ID_PRESENT" in blocker for blocker in payload["blockers"])


def test_non_object_metadata_blocks():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        metadata=["bad"],  # type: ignore[arg-type]
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_SESSION_BOUNDARY_METADATA_MUST_BE_OBJECT" in payload["blockers"]


def test_destructive_reset_marker_blocks():
    payload = build_paper_session_boundary_record(
        session_id="paper-session-1",
        boundary_type="RESET_MARKER",
        created_at_epoch=100.0,
        metadata=_metadata(delete=True),
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("DESTRUCTIVE_RESET_FORBIDDEN" in blocker for blocker in payload["blockers"])


def test_mark_boundary_writes_through_persistence_safely(tmp_path):
    path = tmp_path / "evidence.jsonl"

    payload = mark_paper_session_boundary(
        path,
        session_id="paper-session-1",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        reason="start",
        metadata=_metadata(),
    ).to_dict()

    assert payload["status"] == "MARKED"
    assert payload["persistence"]["status"] == "WRITTEN"
    assert payload["record"]["record_type"] == PAPER_SESSION_BOUNDARY_RECORD_TYPE
    assert path.exists()
    loaded = load_paper_session_boundaries(path).to_dict()
    assert loaded["status"] == "LOADED"
    assert loaded["record_count"] == 1
    assert loaded["records"][0]["boundary_type"] == "SESSION_START"


def test_persistence_write_blocker_returns_blocked():
    payload = mark_paper_session_boundary(
        None,
        session_id="paper-session-1",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        metadata=_metadata(),
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("PERSISTENCE_WRITE" in blocker for blocker in payload["blockers"])


def test_load_missing_file_returns_empty_safely(tmp_path):
    payload = load_paper_session_boundaries(tmp_path / "missing.jsonl").to_dict()

    assert payload["status"] == "EMPTY"
    assert payload["record_count"] == 0
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_load_filters_only_session_boundary_records(tmp_path):
    path = tmp_path / "evidence.jsonl"
    write_paper_evidence_record(
        path,
        record_type="OTHER_RECORD",
        cycle_id="cycle-1",
        payload=_metadata(kind="other"),
    )
    mark_paper_session_boundary(
        path,
        session_id="paper-session-1",
        boundary_type="SESSION_START",
        created_at_epoch=100.0,
        metadata=_metadata(),
    )

    payload = load_paper_session_boundaries(path).to_dict()

    assert payload["status"] == "LOADED"
    assert payload["record_count"] == 1
    assert payload["records"][0]["record_type"] == PAPER_SESSION_BOUNDARY_RECORD_TYPE


def test_boundary_result_has_no_order_controls():
    result_text = json.dumps(
        mark_paper_session_boundary(
            "unused.jsonl",
            session_id="paper-session-1",
            boundary_type="RESET_MARKER",
            created_at_epoch=100.0,
            metadata=_metadata(),
        ).to_dict()
    ).lower()

    assert "submit" not in result_text
    assert "modify" not in result_text
    assert "cancel_order" not in result_text
    assert "exit_order" not in result_text
    assert "place_order" not in result_text


def test_reset_marker_does_not_delete_or_truncate_existing_evidence(tmp_path):
    path = tmp_path / "evidence.jsonl"
    write_paper_evidence_record(
        path,
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        payload=_metadata(kind="pipeline"),
    )
    before = path.read_text(encoding="utf-8")
    before_lines = before.splitlines()

    payload = mark_paper_session_boundary(
        path,
        session_id="paper-session-2",
        boundary_type="RESET_MARKER",
        created_at_epoch=200.0,
        reason="start clean future session",
        metadata=_metadata(reset_scope="future_only"),
    ).to_dict()

    after = path.read_text(encoding="utf-8")
    after_lines = after.splitlines()

    assert payload["status"] == "MARKED"
    assert len(after_lines) == len(before_lines) + 1
    assert after.startswith(before)
    assert "PAPER_PIPELINE_RESULT" in after_lines[0]
    assert PAPER_SESSION_BOUNDARY_RECORD_TYPE in after_lines[-1]


def test_load_blocks_corrupt_persistence_evidence(tmp_path):
    path = tmp_path / "evidence.jsonl"
    path.write_text("not-json\n", encoding="utf-8")

    payload = load_paper_session_boundaries(path).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("PERSISTENCE_LOAD" in blocker for blocker in payload["blockers"])
