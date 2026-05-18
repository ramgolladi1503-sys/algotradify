from __future__ import annotations

import json

from paper_trading.persistence import (
    load_paper_evidence_records,
    paper_evidence_persistence_schema_contract,
    stable_paper_evidence_payload_hash,
    validate_paper_evidence_record,
    write_paper_evidence_record,
)


def _payload(**overrides):
    payload = {
        "pipeline_type": "IN_MEMORY_PAPER_TRADING_PIPELINE",
        "status": "COMPLETED",
        "cycle_id": "cycle-1",
        "candidate_id": "candidate-1",
        "strategy_id": "orb_retest",
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "events": [],
        "state": {"paper_only": True, "read_only": True, "is_order_action": False, "broker_api_called": False, "real_order_id": None},
    }
    payload.update(overrides)
    return payload


def test_schema_contract_exposes_safe_flags_and_jsonl_boundary():
    contract = paper_evidence_persistence_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["persistence_type"] == "PAPER_EVIDENCE_JSONL_PERSISTENCE"
    assert contract["format"] == "JSONL"
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "local_jsonl_only" in contract["scope_boundary"]
    assert "no_runtime_wiring" in contract["scope_boundary"]
    assert "no_broker_execution" in contract["scope_boundary"]
    assert "payload_hash" in contract["required_record_keys"]


def test_valid_evidence_record_writes_successfully(tmp_path):
    path = tmp_path / "paper" / "evidence.jsonl"

    result = write_paper_evidence_record(
        path,
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        candidate_id="candidate-1",
        strategy_id="orb_retest",
        created_at_epoch=100.0,
        payload=_payload(),
    ).to_dict()

    assert result["status"] == "WRITTEN"
    assert result["written"] is True
    assert result["record"]["record_type"] == "PAPER_PIPELINE_RESULT"
    assert result["record"]["cycle_id"] == "cycle-1"
    assert result["record"]["payload_hash"] == stable_paper_evidence_payload_hash(_payload())
    assert result["paper_only"] is True
    assert result["read_only"] is True
    assert result["is_order_action"] is False
    assert result["broker_api_called"] is False
    assert result["real_order_id"] is None
    assert path.exists()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_written_evidence_can_be_loaded_back_deterministically(tmp_path):
    path = tmp_path / "evidence.jsonl"
    write_result = write_paper_evidence_record(
        path,
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        candidate_id="candidate-1",
        strategy_id="orb_retest",
        payload=_payload(),
    ).to_dict()

    read_result = load_paper_evidence_records(path).to_dict()

    assert read_result["status"] == "LOADED"
    assert read_result["loaded"] is True
    assert read_result["record_count"] == 1
    assert read_result["records"] == [write_result["record"]]
    assert read_result["records"][0]["payload_hash"] == stable_paper_evidence_payload_hash(_payload())


def test_missing_evidence_path_blocks_write():
    result = write_paper_evidence_record(
        None,
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        payload=_payload(),
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert result["blockers"] == ["PAPER_EVIDENCE_PATH_REQUIRED"]


def test_missing_cycle_id_blocks_write(tmp_path):
    result = write_paper_evidence_record(
        tmp_path / "evidence.jsonl",
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="",
        payload=_payload(),
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EVIDENCE_CYCLE_ID_REQUIRED" in result["blockers"]


def test_missing_record_type_blocks_write(tmp_path):
    result = write_paper_evidence_record(
        tmp_path / "evidence.jsonl",
        record_type="",
        cycle_id="cycle-1",
        payload=_payload(),
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EVIDENCE_RECORD_TYPE_REQUIRED" in result["blockers"]


def test_missing_payload_blocks_write(tmp_path):
    result = write_paper_evidence_record(
        tmp_path / "evidence.jsonl",
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        payload=None,
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EVIDENCE_PAYLOAD_REQUIRED" in result["blockers"]


def test_non_object_payload_blocks_write(tmp_path):
    result = write_paper_evidence_record(
        tmp_path / "evidence.jsonl",
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        payload=["bad"],  # type: ignore[arg-type]
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EVIDENCE_PAYLOAD_MUST_BE_OBJECT" in result["blockers"]


def test_unsafe_order_action_payload_blocks_write(tmp_path):
    result = write_paper_evidence_record(
        tmp_path / "evidence.jsonl",
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        payload=_payload(is_order_action=True),
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("UNSAFE_ORDER_ACTION_FLAG" in blocker for blocker in result["blockers"])


def test_broker_api_called_payload_blocks_write(tmp_path):
    result = write_paper_evidence_record(
        tmp_path / "evidence.jsonl",
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        payload=_payload(broker_api_called=True),
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("BROKER_API_CALLED" in blocker for blocker in result["blockers"])


def test_real_order_id_payload_blocks_write(tmp_path):
    result = write_paper_evidence_record(
        tmp_path / "evidence.jsonl",
        record_type="PAPER_PIPELINE_RESULT",
        cycle_id="cycle-1",
        payload=_payload(real_order_id="real-1"),
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("REAL_ORDER_ID_PRESENT" in blocker for blocker in result["blockers"])


def test_corrupt_jsonl_line_blocks_load(tmp_path):
    path = tmp_path / "evidence.jsonl"
    path.write_text("not-json\n", encoding="utf-8")

    result = load_paper_evidence_records(path).to_dict()

    assert result["status"] == "BLOCKED"
    assert result["loaded"] is False
    assert result["blockers"] == ["PAPER_EVIDENCE_CORRUPT_JSONL_LINE_1"]


def test_non_object_jsonl_line_blocks_load(tmp_path):
    path = tmp_path / "evidence.jsonl"
    path.write_text("[]\n", encoding="utf-8")

    result = load_paper_evidence_records(path).to_dict()

    assert result["status"] == "BLOCKED"
    assert result["blockers"] == ["PAPER_EVIDENCE_NON_OBJECT_JSONL_LINE_1"]


def test_load_missing_file_returns_empty_safely(tmp_path):
    path = tmp_path / "missing.jsonl"

    result = load_paper_evidence_records(path).to_dict()

    assert result["status"] == "EMPTY"
    assert result["loaded"] is True
    assert result["record_count"] == 0
    assert result["warnings"] == ["PAPER_EVIDENCE_FILE_MISSING_EMPTY"]
    assert result["paper_only"] is True
    assert result["read_only"] is True
    assert result["is_order_action"] is False
    assert result["broker_api_called"] is False
    assert result["real_order_id"] is None


def test_write_result_has_no_order_controls(tmp_path):
    result_text = json.dumps(
        write_paper_evidence_record(
            tmp_path / "evidence.jsonl",
            record_type="PAPER_PIPELINE_RESULT",
            cycle_id="cycle-1",
            payload=_payload(),
        ).to_dict()
    ).lower()

    assert "submit" not in result_text
    assert "modify" not in result_text
    assert "cancel_order" not in result_text
    assert "exit_order" not in result_text
    assert "place_order" not in result_text


def test_load_result_has_no_order_controls(tmp_path):
    path = tmp_path / "evidence.jsonl"
    write_paper_evidence_record(path, record_type="PAPER_PIPELINE_RESULT", cycle_id="cycle-1", payload=_payload())

    result_text = json.dumps(load_paper_evidence_records(path).to_dict()).lower()

    assert "submit" not in result_text
    assert "modify" not in result_text
    assert "cancel_order" not in result_text
    assert "exit_order" not in result_text
    assert "place_order" not in result_text


def test_payload_hash_is_deterministic():
    first = {"b": 2, "a": 1, "nested": {"z": 3, "c": 4}}
    second = {"nested": {"c": 4, "z": 3}, "a": 1, "b": 2}

    assert stable_paper_evidence_payload_hash(first) == stable_paper_evidence_payload_hash(second)


def test_payload_hash_mismatch_blocks_validation(tmp_path):
    path = tmp_path / "evidence.jsonl"
    record = write_paper_evidence_record(path, record_type="PAPER_PIPELINE_RESULT", cycle_id="cycle-1", payload=_payload()).to_dict()["record"]
    record["payload"]["status"] = "DRIFTED"

    blockers = validate_paper_evidence_record(record)

    assert "PAPER_EVIDENCE_PAYLOAD_HASH_MISMATCH" in blockers
