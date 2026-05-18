from __future__ import annotations

import json

from paper_trading.export_bundle import (
    build_paper_export_bundle,
    load_paper_export_manifest,
    paper_export_bundle_schema_contract,
    stable_file_hash,
    validate_paper_export_bundle,
)
from paper_trading.persistence import write_paper_evidence_record


def _payload(**overrides):
    payload = {
        "scenario_result_type": "PAPER_SCENARIO_RESULT",
        "scenario_name": "FULL_FILL_HAPPY_PATH",
        "status": "PASSED",
        "passed": True,
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


def _scenario_result(**overrides):
    payload = {
        "schema_version": "1.0",
        "scenario_result_type": "PAPER_SCENARIO_RESULT",
        "scenario_name": "FULL_FILL_HAPPY_PATH",
        "status": "PASSED",
        "passed": True,
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def test_schema_contract_exposes_safe_flags_and_bundle_layout():
    contract = paper_export_bundle_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["bundle_type"] == "PAPER_EVIDENCE_EXPORT_BUNDLE"
    assert contract["bundle_layout"] == {
        "manifest": "manifest.json",
        "checksums": "checksums.json",
        "evidence": "evidence/paper_evidence.jsonl",
        "scenarios": "scenarios/scenario_results.json",
    }
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "no_replay_dataset" in contract["scope_boundary"]
    assert "no_expectancy_scoring" in contract["scope_boundary"]
    assert "no_runtime_wiring" in contract["scope_boundary"]


def test_valid_evidence_export_builds_bundle(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    bundle_root = tmp_path / "bundle"

    result = build_paper_export_bundle(
        bundle_root=bundle_root,
        evidence_path=evidence_path,
        scenario_results=[_scenario_result()],
        created_at_epoch=100.0,
    ).to_dict()

    assert result["status"] == "BUILT"
    assert result["manifest"]["schema_version"] == "1.0"
    assert result["manifest"]["bundle_type"] == "PAPER_EVIDENCE_EXPORT_BUNDLE"
    assert result["manifest"]["record_count"] == 1
    assert result["manifest"]["scenario_count"] == 1
    assert result["manifest"]["paper_only"] is True
    assert result["manifest"]["read_only"] is True
    assert result["manifest"]["is_order_action"] is False
    assert result["manifest"]["broker_api_called"] is False
    assert result["manifest"]["real_order_id"] is None
    assert (bundle_root / "manifest.json").exists()
    assert (bundle_root / "checksums.json").exists()
    assert (bundle_root / "evidence" / "paper_evidence.jsonl").exists()
    assert (bundle_root / "scenarios" / "scenario_results.json").exists()


def test_validate_built_bundle_returns_valid(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    bundle_root = tmp_path / "bundle"
    build_paper_export_bundle(
        bundle_root=bundle_root,
        evidence_path=evidence_path,
        scenario_results=[_scenario_result()],
        created_at_epoch=100.0,
    )

    result = validate_paper_export_bundle(bundle_root).to_dict()

    assert result["status"] == "VALID"
    assert result["manifest"]["record_count"] == 1
    assert result["manifest"]["scenario_count"] == 1


def test_missing_bundle_root_blocks(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)

    result = build_paper_export_bundle(
        bundle_root=None,
        evidence_path=evidence_path,
        scenario_results=[],
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EXPORT_BUNDLE_ROOT_REQUIRED" in result["blockers"]


def test_missing_evidence_path_blocks(tmp_path):
    result = build_paper_export_bundle(
        bundle_root=tmp_path / "bundle",
        evidence_path=None,
        scenario_results=[],
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EXPORT_EVIDENCE_PATH_REQUIRED" in result["blockers"]


def test_corrupt_evidence_load_blocks(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    evidence_path.write_text("not-json\n", encoding="utf-8")

    result = build_paper_export_bundle(
        bundle_root=tmp_path / "bundle",
        evidence_path=evidence_path,
        scenario_results=[],
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("EVIDENCE_LOAD" in blocker for blocker in result["blockers"])


def test_unsafe_evidence_record_blocks(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    unsafe_record = {
        "schema_version": "1.0",
        "record_type": "PAPER_SCENARIO_RESULT",
        "record_id": "bad",
        "cycle_id": "cycle-1",
        "candidate_id": None,
        "strategy_id": None,
        "created_at_epoch": 100.0,
        "source": "test",
        "payload": _payload(),
        "payload_hash": "bad",
        "paper_only": True,
        "read_only": True,
        "is_order_action": True,
        "broker_api_called": False,
        "real_order_id": None,
    }
    evidence_path.write_text(json.dumps(unsafe_record) + "\n", encoding="utf-8")

    result = build_paper_export_bundle(
        bundle_root=tmp_path / "bundle",
        evidence_path=evidence_path,
        scenario_results=[],
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("EVIDENCE_LOAD" in blocker for blocker in result["blockers"])


def test_scenario_result_with_unsafe_flag_blocks(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)

    result = build_paper_export_bundle(
        bundle_root=tmp_path / "bundle",
        evidence_path=evidence_path,
        scenario_results=[_scenario_result(is_order_action=True)],
    ).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("UNSAFE_ORDER_ACTION_FLAG" in blocker for blocker in result["blockers"])


def test_checksum_mismatch_blocks_validation(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    bundle_root = tmp_path / "bundle"
    build_paper_export_bundle(bundle_root=bundle_root, evidence_path=evidence_path, scenario_results=[], created_at_epoch=100.0)
    evidence_out = bundle_root / "evidence" / "paper_evidence.jsonl"
    evidence_out.write_text(evidence_out.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = validate_paper_export_bundle(bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert any("CHECKSUM_MISMATCH" in blocker for blocker in result["blockers"])


def test_missing_manifest_blocks_validation(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    bundle_root = tmp_path / "bundle"
    build_paper_export_bundle(bundle_root=bundle_root, evidence_path=evidence_path, scenario_results=[], created_at_epoch=100.0)
    (bundle_root / "manifest.json").unlink()

    result = validate_paper_export_bundle(bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EXPORT_MANIFEST_MISSING" in result["blockers"]


def test_missing_evidence_file_blocks_validation(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    bundle_root = tmp_path / "bundle"
    build_paper_export_bundle(bundle_root=bundle_root, evidence_path=evidence_path, scenario_results=[], created_at_epoch=100.0)
    (bundle_root / "evidence" / "paper_evidence.jsonl").unlink()

    result = validate_paper_export_bundle(bundle_root).to_dict()

    assert result["status"] == "BLOCKED"
    assert "PAPER_EXPORT_FILE_MISSING_EVIDENCE" in result["blockers"]


def test_bundle_result_has_no_order_controls(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)

    result_text = json.dumps(
        build_paper_export_bundle(
            bundle_root=tmp_path / "bundle",
            evidence_path=evidence_path,
            scenario_results=[_scenario_result()],
            created_at_epoch=100.0,
        ).to_dict()
    ).lower()

    assert "submit" not in result_text
    assert "modify" not in result_text
    assert "cancel_order" not in result_text
    assert "exit_order" not in result_text
    assert "place_order" not in result_text


def test_export_bundle_does_not_create_replay_dataset_file(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    bundle_root = tmp_path / "bundle"

    build_paper_export_bundle(bundle_root=bundle_root, evidence_path=evidence_path, scenario_results=[], created_at_epoch=100.0)

    assert not (bundle_root / "replay_dataset.json").exists()
    assert not (bundle_root / "replay_dataset.jsonl").exists()


def test_export_bundle_does_not_compute_expectancy_or_profitability_fields(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    result = build_paper_export_bundle(bundle_root=tmp_path / "bundle", evidence_path=evidence_path, scenario_results=[], created_at_epoch=100.0).to_dict()
    text = json.dumps(result).lower()

    assert "expectancy" not in text
    assert "profitability" not in text


def test_same_input_produces_deterministic_manifest_and_checksums(tmp_path):
    evidence_one = tmp_path / "source1.jsonl"
    evidence_two = tmp_path / "source2.jsonl"
    _write_evidence(evidence_one)
    _write_evidence(evidence_two)

    first = build_paper_export_bundle(bundle_root=tmp_path / "bundle1", evidence_path=evidence_one, scenario_results=[_scenario_result()], created_at_epoch=100.0).to_dict()
    second = build_paper_export_bundle(bundle_root=tmp_path / "bundle2", evidence_path=evidence_two, scenario_results=[_scenario_result()], created_at_epoch=100.0).to_dict()

    first_manifest = dict(first["manifest"])
    second_manifest = dict(second["manifest"])
    first_manifest.pop("source_evidence_path")
    second_manifest.pop("source_evidence_path")
    assert first_manifest == second_manifest
    assert first["checksums"] == second["checksums"]


def test_load_paper_export_manifest_returns_manifest(tmp_path):
    evidence_path = tmp_path / "source.jsonl"
    _write_evidence(evidence_path)
    bundle_root = tmp_path / "bundle"
    build_paper_export_bundle(bundle_root=bundle_root, evidence_path=evidence_path, scenario_results=[], created_at_epoch=100.0)

    result = load_paper_export_manifest(bundle_root).to_dict()

    assert result["status"] == "VALID"
    assert result["manifest"]["bundle_type"] == "PAPER_EVIDENCE_EXPORT_BUNDLE"


def test_stable_file_hash_changes_when_file_changes(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("one", encoding="utf-8")
    first = stable_file_hash(path)
    path.write_text("two", encoding="utf-8")
    second = stable_file_hash(path)

    assert first != second
