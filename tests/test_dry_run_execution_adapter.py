from __future__ import annotations

import json

from dry_run_execution import append_dry_run_execution, build_dry_run_execution


def _top(candidate_id="c1", **selected_overrides):
    selected = {
        "candidate_id": candidate_id,
        "symbol": "NIFTY26MAY25500CE",
        "tradingsymbol": "NIFTY26MAY25500CE",
        "instrument_token": 12345,
        "transaction_type": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "product": "MIS",
        "price": 100.5,
        "trigger_price": 95.0,
        "strategy": "orb_retest",
        "quality_score": 91.0,
        "is_order": False,
    }
    selected.update(selected_overrides)
    return {"status": "SELECTED", "selected": selected, "is_order_action": False}


def _safety(**overrides):
    payload = {
        "execution_permitted": True,
        "status": "PERMITTED",
        "is_order_action": False,
        "safety_visibility_only": True,
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _approval(candidate_id="c1", **overrides):
    payload = {
        "candidate_id": candidate_id,
        "current_status": "APPROVED",
        "approval_id": "approval-1234",
        "operator_id": "op1",
        "events": [
            {
                "approval_id": "approval-1234",
                "candidate_id": candidate_id,
                "operator_id": "op1",
                "status": "APPROVED",
                "safety_decision": {"execution_permitted": True, "status": "PERMITTED", "is_order_action": False},
                "is_order_action": False,
            }
        ],
        "blockers": [],
        "is_order_action": False,
    }
    payload.update(overrides)
    return payload


def test_creates_dry_run_intent_when_all_evidence_valid():
    result = build_dry_run_execution(
        top_executable=_top(),
        execution_safety=_safety(),
        approval=_approval(),
        readiness={"candidate_id": "c1", "execution_allowed": True},
        ts_epoch=100.0,
    )

    payload = result.to_dict()
    assert payload["created"] is True
    assert payload["intent"] is not None
    assert payload["lifecycle_event"] is not None
    assert payload["outcome_event"] is not None
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["intent"]["dry_run_only"] is True
    assert payload["intent"]["is_order_action"] is False
    assert payload["intent"]["broker_api_called"] is False
    assert payload["intent"]["real_order_id"] is None
    assert payload["lifecycle_event"]["status"] == "DRY_RUN_INTENT_CREATED"
    assert payload["outcome_event"]["evidence"]["dry_run_only"] is True


def test_blocks_without_selected_top_executable():
    result = build_dry_run_execution(top_executable={"status": "NONE"}, execution_safety=_safety(), approval=_approval())

    assert result.created is False
    assert "NO_TOP_EXECUTABLE_SELECTED" in result.blockers
    assert result.is_order_action is False


def test_blocks_if_top_candidate_order_flag_unsafe():
    result = build_dry_run_execution(top_executable=_top(is_order=True), execution_safety=_safety(), approval=_approval())

    assert result.created is False
    assert "TOP_EXECUTABLE_ORDER_FLAG_UNSAFE" in result.blockers


def test_blocks_if_execution_safety_not_permitted():
    result = build_dry_run_execution(
        top_executable=_top(),
        execution_safety=_safety(execution_permitted=False, status="BLOCKED"),
        approval=_approval(),
    )

    assert result.created is False
    assert "EXECUTION_SAFETY_NOT_PERMITTED" in result.blockers


def test_blocks_without_approved_approval_evidence():
    result = build_dry_run_execution(top_executable=_top(), execution_safety=_safety(), approval=_approval(current_status="REJECTED"))

    assert result.created is False
    assert "APPROVAL_NOT_APPROVED" in result.blockers


def test_blocks_candidate_mismatch_between_approval_and_top_candidate():
    result = build_dry_run_execution(top_executable=_top(candidate_id="c1"), execution_safety=_safety(), approval=_approval(candidate_id="c2"))

    assert result.created is False
    assert "APPROVAL_CANDIDATE_MISMATCH" in result.blockers


def test_result_never_exposes_order_action():
    result = build_dry_run_execution(top_executable=_top(), execution_safety=_safety(), approval=_approval(), ts_epoch=100.0)
    payload = result.to_dict()

    assert payload["is_order_action"] is False
    assert payload["dry_run_only"] is True
    assert payload["broker_api_called"] is False
    assert payload["intent"]["is_order_action"] is False
    assert payload["intent"]["dry_run_only"] is True
    assert payload["intent"]["broker_api_called"] is False
    assert payload["lifecycle_event"]["is_order_action"] is False
    assert payload["lifecycle_event"]["dry_run_only"] is True
    assert payload["lifecycle_event"]["broker_api_called"] is False
    assert payload["outcome_event"]["is_order_action"] is False
    assert payload["outcome_event"]["dry_run_only"] is True
    assert payload["outcome_event"]["broker_api_called"] is False


def test_append_writes_jsonl_only_when_append_true(tmp_path):
    result = build_dry_run_execution(top_executable=_top(), execution_safety=_safety(), approval=_approval(), ts_epoch=100.0)
    assert not (tmp_path / "logs" / "dry_run_order_intents.jsonl").exists()

    appended = append_dry_run_execution(tmp_path, result)

    assert appended.created is True
    assert set(appended.append_paths) == {"intent", "lifecycle", "outcome"}
    intent_rows = [json.loads(line) for line in (tmp_path / "logs" / "dry_run_order_intents.jsonl").read_text(encoding="utf-8").splitlines()]
    lifecycle_rows = [json.loads(line) for line in (tmp_path / "logs" / "dry_run_lifecycle.jsonl").read_text(encoding="utf-8").splitlines()]
    outcome_rows = [json.loads(line) for line in (tmp_path / "logs" / "outcome_replay.jsonl").read_text(encoding="utf-8").splitlines()]
    assert intent_rows[0]["dry_run_only"] is True
    assert lifecycle_rows[0]["status"] == "DRY_RUN_INTENT_CREATED"
    assert outcome_rows[0]["evidence"]["broker_api_called"] is False
