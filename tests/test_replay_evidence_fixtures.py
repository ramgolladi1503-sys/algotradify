from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from outcome_replay import filter_outcome_replay_records, replay_query_metadata
from outcome_replay.query import _candidate_id, _row_status, _row_strategy


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "replay"
REQUIRED_FIXTURES = [
    "empty_replay.json",
    "single_candidate_lifecycle.json",
    "multi_candidate_mixed_status.json",
]
REQUIRED_REPLAY_EVENT_FIELDS = {"ts_epoch"}
REQUIRED_EXPECTED_KEYS = {
    "source_count",
    "candidate_count",
    "status_counts",
    "strategy_counts",
    "query_cases",
}


def _load_fixture(filename: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


def _fixtures() -> list[dict[str, Any]]:
    return [_load_fixture(filename) for filename in REQUIRED_FIXTURES]


def _fixture_contract_payload() -> dict[str, Any]:
    fixtures = _fixtures()
    metadata_samples = []
    for fixture in fixtures:
        rows = fixture["outcome_replay"]
        for case in fixture["expected"]["query_cases"]:
            result = filter_outcome_replay_records(rows, **case["filters"])
            metadata_samples.append(
                replay_query_metadata(
                    **case["filters"],
                    source_count=len(rows),
                    result_count=len(result),
                )
            )
    return {"fixtures": fixtures, "metadata_samples": metadata_samples}


def test_replay_fixture_files_exist():
    for filename in REQUIRED_FIXTURES:
        assert (FIXTURE_DIR / filename).is_file()


def test_replay_fixtures_have_stable_shape():
    for fixture in _fixtures():
        assert fixture["fixture_id"]
        assert isinstance(fixture["description"], str)
        assert isinstance(fixture["outcome_replay"], list)
        assert REQUIRED_EXPECTED_KEYS.issubset(fixture["expected"])
        for row in fixture["outcome_replay"]:
            assert isinstance(row, dict)
            assert REQUIRED_REPLAY_EVENT_FIELDS.issubset(row)
            assert _candidate_id(row)
            assert str(_row_status(row))


def test_replay_fixture_expected_counts_match_records():
    for fixture in _fixtures():
        rows = fixture["outcome_replay"]
        expected = fixture["expected"]

        assert len(rows) == expected["source_count"]
        assert len({_candidate_id(row) for row in rows}) == expected["candidate_count"]
        assert dict(Counter(str(_row_status(row).value) for row in rows)) == expected["status_counts"]
        assert dict(Counter(_row_strategy(row) or "UNKNOWN" for row in rows)) == expected["strategy_counts"]


def test_replay_fixture_query_cases_are_deterministic():
    for fixture in _fixtures():
        rows = fixture["outcome_replay"]
        for case in fixture["expected"]["query_cases"]:
            result = filter_outcome_replay_records(rows, **case["filters"])

            assert len(result) == case["result_count"], case["name"]
            assert [_candidate_id(row) for row in result] == case["candidate_ids"], case["name"]


def test_replay_fixture_query_metadata_stays_read_only():
    for fixture in _fixtures():
        rows = fixture["outcome_replay"]
        for case in fixture["expected"]["query_cases"]:
            result = filter_outcome_replay_records(rows, **case["filters"])
            metadata = replay_query_metadata(
                **case["filters"],
                source_count=len(rows),
                result_count=len(result),
            )

            assert metadata["source_count"] == fixture["expected"]["source_count"]
            assert metadata["result_count"] == case["result_count"]
            assert metadata["read_only"] is True
            assert metadata["is_order_action"] is False


def test_replay_fixture_ui_contract_fields_are_present():
    expected_ui_terms = [
        "candidate_id",
        "status",
        "strategy",
        "ts_epoch",
        "quality_score",
        "source_count",
        "result_count",
        "read_only",
        "is_order_action",
    ]
    serialized = json.dumps(_fixture_contract_payload(), sort_keys=True)

    for term in expected_ui_terms:
        assert term in serialized
