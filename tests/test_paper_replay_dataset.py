from __future__ import annotations

import json

from paper_trading.export_bundle import build_paper_export_bundle, stable_file_hash
from paper_trading.persistence import write_paper_evidence_record
from paper_trading.replay_dataset import (
    build_paper_replay_dataset,
    load_paper_replay_dataset_rows,
    paper_replay_dataset_schema_contract,
    stable_replay_row_id,
    validate_paper_replay_dataset_rows,
)


def _payload(**overrides):
    payload = {
        "scenario_result_type": "PAPER_SCENARIO_RESULT",
        "scenario_name": "FULL_FILL_HAPPY_PATH",
        "status": "COMPLETED",
        "candidate_id": "candidate-1",
        "strategy_id": "orb_retest",
        "event_count": 4,
        "session_id": "paper-session-1",
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _write_evidence(path, payload=None):
    return write_paper_evidence_record(
        path,
        record_type="PAPER_SCENARIO_RESULT",
        cycle_id="cycle-1",
        candidate_id="candidate-1",
        strategy_id="orb_retest",
        created_at_epoch=100.0,
        source="test",
        payload=payload or _payload(),
    ).to_dict()


def _build_bundle(tmp_path, *, payload=None):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path, payload=payload)
    bundle_root = tmp_path / "bundle"
    bundle = build_paper_export_bundle(
        bundle_root=bundle_root,
        evidence_path=evidence_path,
        scenario_results=[],
        created_at_epoch=100.0,
    ).to_dict()
    assert bundle["status"] == "BUILT"
    return bundle_root, bundle


def test_schema_contract_exposes_safe_flags_and_jsonl_output():
    contract = paper_replay_dataset_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["dataset_type"] == "PAPER_REPLAY_DATASET"
    assert contract["output_format"] == "JSONL"
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "no_outcome_scoring" in contract["scope_boundary"]
    assert "no_model_features" in contract["scope_boundary"]
    assert "no_runtime_wiring" in contract["scope_boundary"]
    assert "row_id" in contract["required_row_keys"]


def test_valid_export_bundle_builds_replay_rows(tmp_path):
    bundle_root, bundle = _build_bundle(tmp_path)

    result = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()

    assert result["status"] == "BUILT"
    assert result["row_count"] == 1
    row = result["rows"][0]
    assert row["source_bundle_id"] == bundle["manifest"]["bundle_id"]
    assert row["source_record_id"]
    assert row["source_record_type"] == "PAPER_SCENARIO_RESULT"
    assert row["source_cycle_id"] == "cycle-1"
    assert row["source_candidate_id"] == "candidate-1"
    assert row["source_strategy_id"] == "orb_retest"
    assert row["scenario_name"] == "FULL_FILL_HAPPY_PATH"
    assert row["event_count"] == 4
    assert row["pipeline_status"] == "COMPLETED"
    assert row["session_id"] == "paper-session-1"
    assert row["paper_only"] is True
    assert row["read_only"] is True
    assert row["is_order_action"] is False
    assert row["broker_api_called"] is False
    assert row["real_order_id"] is None


def test_valid_replay_rows_can_be_written_and_loaded(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)
    output_path = tmp_path / "replay_dataset.jsonl"

    built = build_paper_replay_dataset(bundle_root=bundle_root, output_path=output_path).to_dict()
    loaded = load_paper_replay_dataset_rows(output_path).to_dict()

    assert built["status"] == "BUILT"
    assert output_path.exists()
    assert loaded["status"] == "VALID"
    assert loaded["rows"] == built["rows"]
    assert loaded["row_count"] == 1


def test_missing_bundle_root_blocks():
    result = build_paper_replay_dataset(bundle_root=None).to_dict()

    assert result["status"] == "BLOCKED"
    assert result["blockers"] == ["PAPER_REPLAY_BUNDLE_ROOT_REQUIRED"]


def test_invalid_bundle_blocks(tmp_path):
    bundle_root = tmp_path / "bad-bundle"
    bundle_root.mkdir()

    result = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("BUNDLE_VALIDATION" in blocker for blocker in result["blockers"])


def test_missing_evidence_file_blocks(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)
    (bundle_root / "evidence" / "paper_evidence.jsonl").unlink()

    result = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("BUNDLE_VALIDATION" in blocker for blocker in result["blockers"])


def test_corrupt_evidence_jsonl_blocks(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)
    evidence_path = bundle_root / "evidence" / "paper_evidence.jsonl"
    evidence_path.write_text("not-json\n", encoding="utf-8")
    # Keep checksum validation from catching this first so replay parser proves the corrupt-line guard.
    checksums_path = bundle_root / "checksums.json"
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    checksums["evidence/paper_evidence.jsonl"] = stable_file_hash(evidence_path)
    checksums_path.write_text(json.dumps(checksums, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    result = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_REPLAY_EVIDENCE_CORRUPT_JSONL_LINE_1" in result["blockers"]


def test_unsafe_evidence_record_blocks(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)
    evidence_path = bundle_root / "evidence" / "paper_evidence.jsonl"
    unsafe_record = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[0])
    unsafe_record["payload"]["broker_api_called"] = True
    evidence_path.write_text(json.dumps(unsafe_record, sort_keys=True) + "\n", encoding="utf-8")
    checksums_path = bundle_root / "checksums.json"
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    checksums["evidence/paper_evidence.jsonl"] = stable_file_hash(evidence_path)
    checksums_path.write_text(json.dumps(checksums, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    result = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("BROKER_API_CALLED" in blocker for blocker in result["blockers"])


def test_unsafe_replay_row_blocks_validation():
    row = {
        "schema_version": "1.0",
        "row_type": "PAPER_REPLAY_DATASET_ROW",
        "row_id": "row-1",
        "source_bundle_id": "bundle-1",
        "source_record_id": "record-1",
        "source_record_type": "PAPER_SCENARIO_RESULT",
        "source_cycle_id": "cycle-1",
        "source_candidate_id": "candidate-1",
        "source_strategy_id": "strategy-1",
        "source_created_at_epoch": 100.0,
        "scenario_name": "FULL_FILL_HAPPY_PATH",
        "event_count": 4,
        "pipeline_status": "COMPLETED",
        "session_id": "paper-session-1",
        "payload_hash": "hash",
        "paper_only": True,
        "read_only": True,
        "is_order_action": True,
        "broker_api_called": False,
        "real_order_id": None,
    }

    blockers = validate_paper_replay_dataset_rows([row])

    assert any("UNSAFE_ORDER_ACTION_FLAG" in blocker for blocker in blockers)


def test_output_has_no_order_controls(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)

    text = json.dumps(build_paper_replay_dataset(bundle_root=bundle_root).to_dict()).lower()

    assert "submit" not in text
    assert "modify" not in text
    assert "cancel_order" not in text
    assert "exit_order" not in text
    assert "place_order" not in text


def test_dataset_does_not_include_expectancy_profitability_reward_or_label_fields(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)

    result = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()
    text = json.dumps(result).lower()

    assert "expectancy" not in text
    assert "profitability" not in text
    assert "reward" not in text
    assert "label" not in text
    assert "future_return" not in text
    assert "win_loss" not in text


def test_analysis_fields_in_evidence_block_dataset_build(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path, payload=_payload(reward=1.0))

    result = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("ANALYSIS_FIELD_FORBIDDEN" in blocker for blocker in result["blockers"])


def test_same_input_produces_deterministic_rows(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)

    first = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()
    second = build_paper_replay_dataset(bundle_root=bundle_root).to_dict()

    assert first["rows"] == second["rows"]


def test_builder_does_not_mutate_export_bundle_files(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)
    manifest_before = (bundle_root / "manifest.json").read_text(encoding="utf-8")
    checksums_before = (bundle_root / "checksums.json").read_text(encoding="utf-8")
    evidence_before = (bundle_root / "evidence" / "paper_evidence.jsonl").read_text(encoding="utf-8")

    result = build_paper_replay_dataset(bundle_root=bundle_root, output_path=tmp_path / "dataset.jsonl").to_dict()

    assert result["status"] == "BUILT"
    assert (bundle_root / "manifest.json").read_text(encoding="utf-8") == manifest_before
    assert (bundle_root / "checksums.json").read_text(encoding="utf-8") == checksums_before
    assert (bundle_root / "evidence" / "paper_evidence.jsonl").read_text(encoding="utf-8") == evidence_before


def test_output_path_inside_bundle_blocks(tmp_path):
    bundle_root, _bundle = _build_bundle(tmp_path)

    result = build_paper_replay_dataset(bundle_root=bundle_root, output_path=bundle_root / "replay_dataset.jsonl").to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_REPLAY_OUTPUT_PATH_MUST_NOT_MUTATE_BUNDLE" in result["blockers"]


def test_load_missing_dataset_returns_empty(tmp_path):
    result = load_paper_replay_dataset_rows(tmp_path / "missing.jsonl").to_dict()

    assert result["status"] == "EMPTY"
    assert result["row_count"] == 0
    assert result["warnings"] == ["PAPER_REPLAY_DATASET_FILE_MISSING_EMPTY"]


def test_load_corrupt_dataset_blocks(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("not-json\n", encoding="utf-8")

    result = load_paper_replay_dataset_rows(path).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_REPLAY_CORRUPT_JSONL_LINE_1" in result["blockers"]


def test_stable_replay_row_id_is_deterministic():
    first = stable_replay_row_id({"b": 2, "a": 1})
    second = stable_replay_row_id({"a": 1, "b": 2})

    assert first == second
    assert first.startswith("paper-replay-row-")
