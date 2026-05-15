from __future__ import annotations

from top_selector import TopExecutableSelectorStatus, select_top_executable


def _quality(candidate_id: str, score: float, allowed: bool = True, blockers=None):
    return {
        "candidate_id": candidate_id,
        "quality_score": score,
        "status": "QUALIFIED" if allowed else "BLOCKED_NOT_EXECUTION_READY",
        "blockers": blockers or [],
        "warnings": [],
        "execution_readiness": {
            "candidate_id": candidate_id,
            "execution_allowed": allowed,
            "status": "ALLOWED" if allowed else "BLOCKED_RISK",
        },
        "is_order": False,
    }


def test_select_top_executable_picks_highest_allowed_quality_candidate():
    result = select_top_executable([
        _quality("mid", 75),
        _quality("best", 92),
        _quality("low", 60),
    ])

    assert result.status == TopExecutableSelectorStatus.SELECTED
    assert result.selected is not None
    assert result.selected["candidate_id"] == "best"
    assert result.selected["selected_by"] == "top_executable_selector"
    assert result.selected["selection_reason"] == "highest_quality_score_above_threshold"
    assert [row["candidate_id"] for row in result.eligible] == ["best", "mid", "low"]
    assert [row["selector_rank"] for row in result.eligible] == [1, 2, 3]
    assert result.rejected == []
    assert result.is_order is False
    assert result.is_selector_decision is True


def test_select_top_executable_rejects_blocked_candidates():
    result = select_top_executable([
        _quality("blocked", 99, allowed=False, blockers=["RISK_NOT_ALLOWED"]),
        _quality("allowed", 70, allowed=True),
    ])

    assert result.status == TopExecutableSelectorStatus.SELECTED
    assert result.selected["candidate_id"] == "allowed"
    assert len(result.rejected) == 1
    rejected = result.rejected[0]
    assert rejected["candidate_id"] == "blocked"
    assert "EXECUTION_NOT_ALLOWED" in rejected["selector_rejection_reasons"]
    assert "TRADE_QUALITY_BLOCKED" in rejected["selector_rejection_reasons"]
    assert "BLOCKER:RISK_NOT_ALLOWED" in rejected["selector_rejection_reasons"]


def test_select_top_executable_rejects_below_threshold_candidates():
    result = select_top_executable([
        _quality("weak", 49.9),
    ], min_quality_score=50.0)

    assert result.status == TopExecutableSelectorStatus.NO_ELIGIBLE_CANDIDATES
    assert result.selected is None
    assert result.reason == "no_execution_allowed_quality_candidate"
    assert result.eligible == []
    assert result.rejected[0]["candidate_id"] == "weak"
    assert "QUALITY_SCORE_BELOW_THRESHOLD" in result.rejected[0]["selector_rejection_reasons"]


def test_select_top_executable_empty_input():
    result = select_top_executable([])

    assert result.status == TopExecutableSelectorStatus.NO_ELIGIBLE_CANDIDATES
    assert result.selected is None
    assert result.rejected == []
    assert result.reason == "no_execution_allowed_quality_candidate"


def test_select_top_executable_to_dict_is_not_order():
    result = select_top_executable([_quality("best", 90)])
    payload = result.to_dict()

    assert payload["status"] == "SELECTED"
    assert payload["selected"]["candidate_id"] == "best"
    assert payload["is_order"] is False
    assert payload["is_selector_decision"] is True
