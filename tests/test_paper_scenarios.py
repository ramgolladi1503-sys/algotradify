from __future__ import annotations

import json

from paper_trading.scenarios import (
    PaperScenarioName,
    paper_scenario_schema_contract,
    run_paper_scenario,
    run_standard_paper_scenarios,
)


def test_schema_contract_exposes_safe_flags_and_scenario_names():
    contract = paper_scenario_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["scenario_result_type"] == "PAPER_SCENARIO_RESULT"
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert contract["scenario_names"] == [name.value for name in PaperScenarioName]
    assert "no_export_bundle" in contract["scope_boundary"]
    assert "no_replay_dataset" in contract["scope_boundary"]
    assert "no_runtime_wiring" in contract["scope_boundary"]


def test_full_fill_scenario_passes_deterministically(tmp_path):
    path = tmp_path / "full.jsonl"

    first = run_paper_scenario(
        scenario_name="FULL_FILL_HAPPY_PATH",
        evidence_path=path,
    ).to_dict()
    second = run_paper_scenario(
        scenario_name="FULL_FILL_HAPPY_PATH",
        evidence_path=tmp_path / "full-second.jsonl",
    ).to_dict()

    assert first["status"] == "PASSED"
    assert first["passed"] is True
    assert first["actual"]["pipeline_status"] == "COMPLETED"
    assert first["actual"]["last_event_type"] == "PAPER_ORDER_FILLED"
    assert first["actual"]["record_count"] >= 3
    assert first["paper_only"] is True
    assert first["read_only"] is True
    assert first["is_order_action"] is False
    assert first["broker_api_called"] is False
    assert first["real_order_id"] is None
    assert first["actual"] == second["actual"]


def test_partial_fill_scenario_passes_deterministically(tmp_path):
    payload = run_paper_scenario(
        scenario_name="PARTIAL_FILL_PATH",
        evidence_path=tmp_path / "partial.jsonl",
    ).to_dict()

    assert payload["status"] == "PASSED"
    assert payload["actual"]["pipeline_status"] == "COMPLETED"
    assert payload["actual"]["last_event_type"] == "PAPER_ORDER_PARTIALLY_FILLED"
    assert payload["actual"]["record_count"] >= 3


def test_no_fill_scenario_passes_deterministically(tmp_path):
    payload = run_paper_scenario(
        scenario_name="NO_FILL_PATH",
        evidence_path=tmp_path / "nofill.jsonl",
    ).to_dict()

    assert payload["status"] == "PASSED"
    assert payload["actual"]["pipeline_status"] == "COMPLETED"
    assert payload["actual"]["last_event_type"] == "PAPER_ORDER_OPENED"
    assert payload["actual"]["record_count"] >= 3


def test_stale_quote_scenario_reports_expected_blocked_safely(tmp_path):
    payload = run_paper_scenario(
        scenario_name="STALE_QUOTE_BLOCKED_PATH",
        evidence_path=tmp_path / "stale.jsonl",
    ).to_dict()

    assert payload["status"] == "PASSED"
    assert payload["actual"]["pipeline_status"] == "BLOCKED"
    assert payload["actual"]["last_event_type"] is None
    assert payload["pipeline"]["status"] == "BLOCKED"
    assert any("STALE" in blocker for blocker in payload["pipeline"]["blockers"])


def test_session_reset_marker_scenario_appends_marker_without_altering_previous_evidence(tmp_path):
    path = tmp_path / "reset.jsonl"

    payload = run_paper_scenario(
        scenario_name="SESSION_RESET_MARKER_PATH",
        evidence_path=path,
    ).to_dict()
    lines = path.read_text(encoding="utf-8").splitlines()

    assert payload["status"] == "PASSED"
    assert payload["actual"]["final_boundary_type"] == "RESET_MARKER"
    assert len(lines) == payload["persistence"]["load"]["record_count"]
    assert any("PAPER_SESSION_BOUNDARY" in line for line in lines)
    assert any("PAPER_SCENARIO_PIPELINE_RESULT" in line for line in lines)


def test_missing_scenario_name_blocks(tmp_path):
    payload = run_paper_scenario(
        scenario_name="",
        evidence_path=tmp_path / "missing.jsonl",
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_SCENARIO_NAME_REQUIRED" in payload["blockers"]


def test_unknown_scenario_name_blocks(tmp_path):
    payload = run_paper_scenario(
        scenario_name="UNKNOWN",
        evidence_path=tmp_path / "unknown.jsonl",
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_SCENARIO_NAME_UNKNOWN" in payload["blockers"]


def test_unsafe_scenario_input_blocks(tmp_path):
    payload = run_paper_scenario(
        scenario_name="FULL_FILL_HAPPY_PATH",
        evidence_path=tmp_path / "unsafe.jsonl",
        overrides={"quote": {"broker_api_called": True}},
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("BROKER_API_CALLED" in blocker for blocker in payload["blockers"])


def test_pipeline_blocker_is_surfaced(tmp_path):
    payload = run_paper_scenario(
        scenario_name="FULL_FILL_HAPPY_PATH",
        evidence_path=tmp_path / "pipeline-blocked.jsonl",
        overrides={"market_data": {"status": "BLOCKED_STALE_SPOT"}},
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("PIPELINE" in blocker for blocker in payload["blockers"])
    assert payload["pipeline"]["status"] == "BLOCKED"


def test_persistence_blocker_is_surfaced():
    payload = run_paper_scenario(
        scenario_name="FULL_FILL_HAPPY_PATH",
        evidence_path=None,
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert "PAPER_SCENARIO_EVIDENCE_PATH_REQUIRED" in payload["blockers"]


def test_session_boundary_blocker_is_surfaced(tmp_path):
    payload = run_paper_scenario(
        scenario_name="FULL_FILL_HAPPY_PATH",
        evidence_path=tmp_path / "session-blocked.jsonl",
        overrides={"ts_epoch": "bad"},
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("SESSION_START" in blocker for blocker in payload["blockers"])


def test_corrupt_evidence_load_is_surfaced(tmp_path):
    path = tmp_path / "corrupt.jsonl"
    path.write_text("not-json\n", encoding="utf-8")

    payload = run_paper_scenario(
        scenario_name="FULL_FILL_HAPPY_PATH",
        evidence_path=path,
    ).to_dict()

    assert payload["status"] == "BLOCKED"
    assert any("PERSISTENCE_LOAD" in blocker for blocker in payload["blockers"])


def test_scenario_result_has_no_order_controls(tmp_path):
    payload_text = json.dumps(
        run_paper_scenario(
            scenario_name="FULL_FILL_HAPPY_PATH",
            evidence_path=tmp_path / "safe.jsonl",
        ).to_dict()
    ).lower()

    assert "submit" not in payload_text
    assert "modify" not in payload_text
    assert "cancel_order" not in payload_text
    assert "exit_order" not in payload_text
    assert "place_order" not in payload_text


def test_same_scenario_input_produces_same_result(tmp_path):
    first = run_paper_scenario(
        scenario_name="PARTIAL_FILL_PATH",
        evidence_path=tmp_path / "first.jsonl",
    ).to_dict()
    second = run_paper_scenario(
        scenario_name="PARTIAL_FILL_PATH",
        evidence_path=tmp_path / "second.jsonl",
    ).to_dict()

    assert first["expected"] == second["expected"]
    assert first["actual"] == second["actual"]
    assert first["pipeline"]["events"] == second["pipeline"]["events"]


def test_standard_scenario_suite_runs_all_scenarios(tmp_path):
    payload = run_standard_paper_scenarios(evidence_dir=tmp_path).copy()

    assert payload["status"] == "PASSED"
    assert payload["passed"] is True
    assert payload["scenario_count"] == len(PaperScenarioName)
    assert payload["blockers"] == []
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_scenario_suite_blocks_missing_evidence_dir():
    payload = run_standard_paper_scenarios(evidence_dir=None)

    assert payload["status"] == "FAILED"
    assert payload["passed"] is False
    assert payload["blockers"] == ["PAPER_SCENARIO_EVIDENCE_DIR_REQUIRED"]


def test_scenario_suite_does_not_mutate_established_paper_contracts():
    contract = paper_scenario_schema_contract()

    assert contract["upstream_contracts"]["pipeline"]["pipeline_type"] == "IN_MEMORY_PAPER_TRADING_PIPELINE"
    assert contract["upstream_contracts"]["session_boundary"]["boundary_result_type"] == "PAPER_SESSION_BOUNDARY_RESULT"
