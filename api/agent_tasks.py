from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query, Request

from agent_system.approval import approve_agent_work
from agent_system.evidence import AgentEvidenceError, write_agent_evidence
from agent_system.patch_approval import (
    AgentPatchApprovalError,
    agent_patch_approval_schema_contract,
    build_agent_patch_approval_record,
    build_agent_patch_rejection_record,
    load_agent_patch_approval,
    persist_agent_patch_approval,
)
from agent_system.scope_guard import AgentScopeDecision, assess_agent_scope
from agent_system.task_store import (
    AgentTaskStoreError,
    build_agent_task_record,
    load_agent_task,
    persist_agent_task,
    query_agent_tasks,
)
from agent_system.work_contract import AgentWorkValidationError, normalize_agent_work_request


AGENT_TASKS_ROUTE_CONTRACT = "agent_tasks_intake_v1"
AGENT_TASKS_QUERY_CONTRACT = "agent_tasks_query_v1"
AGENT_TASKS_PATCH_APPROVAL_CONTRACT = "agent_tasks_patch_approval_api_v1"


def agent_tasks_intake_schema_contract() -> dict[str, Any]:
    return {
        "contract": AGENT_TASKS_ROUTE_CONTRACT,
        "route": "POST /agent/tasks",
        "method": "POST",
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
        "scope": "intake_only_no_execution_no_broker_no_live_no_paper_orders",
    }


def agent_tasks_query_schema_contract() -> dict[str, Any]:
    return {
        "contract": AGENT_TASKS_QUERY_CONTRACT,
        "routes": ["GET /agent/tasks", "GET /agent/tasks/{work_id}"],
        "methods": ["GET"],
        "filters": [
            "source_agent",
            "action",
            "state",
            "risk_level",
            "created_from",
            "created_to",
            "limit",
        ],
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
        "scope": "query_only_no_execution_no_approval_no_broker_no_live_no_paper_orders",
    }


def agent_tasks_patch_approval_api_schema_contract() -> dict[str, Any]:
    return {
        "contract": AGENT_TASKS_PATCH_APPROVAL_CONTRACT,
        "routes": [
            "POST /agent/tasks/{work_id}/approval",
            "POST /agent/tasks/{work_id}/rejection",
        ],
        "methods": ["POST"],
        "record_contract": agent_patch_approval_schema_contract()["contract"],
        "safe_defaults": {
            "read_only": True,
            "patch_approval_only": True,
            "allowed_for_patch": False,
            "allowed_for_runtime_wiring": False,
            "allowed_for_broker_api": False,
            "allowed_for_live_execution": False,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "real_order_id": None,
        },
        "scope": "patch_approval_api_record_only_no_execution_no_broker_no_live_no_paper_orders",
    }


def _safe_flags() -> dict[str, Any]:
    return {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }


def _patch_safe_flags(*, allowed_for_patch: bool = False) -> dict[str, Any]:
    return {
        **_safe_flags(),
        "patch_approval_only": True,
        "allowed_for_patch": allowed_for_patch,
        "allowed_for_runtime_wiring": False,
        "allowed_for_broker_api": False,
        "real_order_id": None,
    }


def _route_exists(app: FastAPI, path: str, method: str) -> bool:
    expected = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if expected in methods:
            return True
    return False


def _scope_decision_from_task(task: dict[str, Any]) -> AgentScopeDecision:
    payload = task.get("scope_decision")
    if not isinstance(payload, dict):
        raise AgentTaskStoreError("TASK_SCOPE_DECISION_MISSING")
    return AgentScopeDecision(
        schema_version=int(payload.get("schema_version", 1)),
        work_id=payload.get("work_id"),
        accepted=bool(payload.get("accepted")),
        state=str(payload.get("state") or "UNKNOWN"),
        source_agent=str(payload.get("source_agent") or ""),
        action=str(payload.get("action") or ""),
        risk_level=str(payload.get("risk_level") or "UNKNOWN"),
        read_only=payload.get("read_only") is True,
        is_order_action=payload.get("is_order_action") is True,
        broker_api_called=payload.get("broker_api_called") is True,
        live_mode_touched=payload.get("live_mode_touched") is True,
        allowed_for_patch=payload.get("allowed_for_patch") is True,
        allowed_for_runtime_wiring=payload.get("allowed_for_runtime_wiring") is True,
        allowed_for_broker_api=payload.get("allowed_for_broker_api") is True,
        allowed_for_live_execution=payload.get("allowed_for_live_execution") is True,
        requires_human_approval=payload.get("requires_human_approval") is True,
        blockers=tuple(payload.get("blockers") or ()),
        warnings=tuple(payload.get("warnings") or ()),
        reasons=tuple(payload.get("reasons") or ()),
        metadata=dict(payload.get("metadata") or {}),
    )


def _clean_optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise AgentPatchApprovalError(f"{key.upper()}_MUST_BE_STRING")
    return value


def build_agent_task_intake_payload(
    request_payload: dict[str, Any],
    *,
    root_dir: str | Path = "runtime/agent_work",
    human_approved: bool = False,
    approved_by: str | None = None,
) -> dict[str, Any]:
    """Submit an agent task through the safe intake layers.

    This is intake-only: no patch application, no runtime worker, no broker calls,
    no paper orders, and no live config mutation.
    """

    request = normalize_agent_work_request(request_payload)
    scope_decision = assess_agent_scope(request)
    approval_decision = approve_agent_work(
        scope_decision,
        human_approved=human_approved,
        approved_by=approved_by,
    )
    evidence_ref = write_agent_evidence(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        root_dir=root_dir,
    )
    task_record = build_agent_task_record(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        evidence_ref=evidence_ref,
    )
    task_ref = persist_agent_task(task_record, root_dir=root_dir)

    if scope_decision.state == "BLOCKED":
        status = "BLOCKED"
        accepted = False
    elif approval_decision.approved:
        status = "APPROVED_FOR_PATCH"
        accepted = True
    else:
        status = "REJECTED"
        accepted = False

    return {
        "contract": AGENT_TASKS_ROUTE_CONTRACT,
        "status": status,
        "accepted": accepted,
        "work_id": task_record.work_id,
        "scope_decision": scope_decision.to_dict(),
        "approval_decision": approval_decision.to_dict(),
        "evidence_ref": evidence_ref,
        "task_ref": task_ref,
        "metadata": {
            "scope": "agent_task_intake_only_no_execution",
        },
        **_safe_flags(),
    }


def build_agent_task_query_payload(
    *,
    root_dir: str | Path = "runtime/agent_work",
    source_agent: str | None = None,
    action: str | None = None,
    state: str | None = None,
    risk_level: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    query = query_agent_tasks(
        root_dir,
        source_agent=source_agent,
        action=action,
        state=state,
        risk_level=risk_level,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
    )
    return {
        "contract": AGENT_TASKS_QUERY_CONTRACT,
        "query": {
            "source_agent": source_agent,
            "action": action,
            "state": state,
            "risk_level": risk_level,
            "created_from": created_from,
            "created_to": created_to,
            "limit": limit,
        },
        "source_count": query["source_count"],
        "result_count": query["result_count"],
        "records": query["records"],
        "metadata": {
            "scope": "agent_task_query_only_no_execution",
        },
        **_safe_flags(),
    }


def build_agent_task_detail_payload(*, root_dir: str | Path = "runtime/agent_work", work_id: str) -> dict[str, Any] | None:
    task = load_agent_task(root_dir, work_id)
    if task is None:
        return None
    approval_record = load_agent_patch_approval(root_dir, work_id)
    return {
        "contract": AGENT_TASKS_QUERY_CONTRACT,
        "work_id": work_id,
        "task": task,
        "patch_approval": approval_record,
        "metadata": {
            "scope": "agent_task_detail_query_only_no_execution",
        },
        **_safe_flags(),
    }


def build_agent_task_patch_approval_payload(
    *,
    root_dir: str | Path = "runtime/agent_work",
    work_id: str,
    approved_by: str | None,
    reason: str | None = None,
) -> dict[str, Any]:
    task = load_agent_task(root_dir, work_id)
    if task is None:
        raise AgentPatchApprovalError("AGENT_TASK_NOT_FOUND")
    scope_decision = _scope_decision_from_task(task)
    approval_decision = approve_agent_work(scope_decision, human_approved=True, approved_by=approved_by)
    approval_payload = approval_decision.to_dict()
    record = build_agent_patch_approval_record(
        work_id=work_id,
        task=task,
        approval_decision=approval_payload,
        approved_by=approved_by,
        reason=reason,
    )
    approval_ref = persist_agent_patch_approval(record, root_dir=root_dir)
    return {
        "contract": AGENT_TASKS_PATCH_APPROVAL_CONTRACT,
        "status": "APPROVED_FOR_PATCH",
        "work_id": work_id,
        "approval_record": record,
        "approval_ref": approval_ref,
        "metadata": {
            "scope": "agent_patch_approval_api_record_only_no_execution",
        },
        **_patch_safe_flags(allowed_for_patch=True),
    }


def build_agent_task_patch_rejection_payload(
    *,
    root_dir: str | Path = "runtime/agent_work",
    work_id: str,
    rejected_by: str | None,
    reason: str | None = None,
) -> dict[str, Any]:
    task = load_agent_task(root_dir, work_id)
    if task is None:
        raise AgentPatchApprovalError("AGENT_TASK_NOT_FOUND")
    record = build_agent_patch_rejection_record(
        work_id=work_id,
        task=task,
        rejected_by=rejected_by,
        reason=reason,
    )
    approval_ref = persist_agent_patch_approval(record, root_dir=root_dir)
    return {
        "contract": AGENT_TASKS_PATCH_APPROVAL_CONTRACT,
        "status": "REJECTED_FOR_PATCH",
        "work_id": work_id,
        "approval_record": record,
        "approval_ref": approval_ref,
        "metadata": {
            "scope": "agent_patch_rejection_api_record_only_no_execution",
        },
        **_patch_safe_flags(allowed_for_patch=False),
    }


def _query_error(status: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "status": status,
            "message": message,
            **_safe_flags(),
        },
    )


def _patch_error(status: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "status": status,
            "message": message,
            **_patch_safe_flags(allowed_for_patch=False),
        },
    )


async def _json_object_payload(request: Request) -> dict[str, Any]:
    try:
        raw_payload = await request.json()
    except Exception as exc:
        raise _patch_error("INPUT_ERROR", f"invalid json: {type(exc).__name__}", 400) from exc
    if not isinstance(raw_payload, dict):
        raise _patch_error("INPUT_ERROR", "PAYLOAD_JSON_MUST_BE_OBJECT", 400)
    return dict(raw_payload)


def install_agent_tasks_route(
    app: FastAPI,
    *,
    root_dir_provider: Callable[[], str | Path] | None = None,
) -> None:
    def root_dir() -> str | Path:
        if root_dir_provider is None:
            return "runtime/agent_work"
        return root_dir_provider()

    if not _route_exists(app, "/agent/tasks", "POST"):
        @app.post("/agent/tasks")
        async def agent_tasks(request: Request):
            try:
                raw_payload = await request.json()
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "INPUT_ERROR",
                        "message": f"invalid json: {type(exc).__name__}",
                        **_safe_flags(),
                    },
                ) from exc

            if not isinstance(raw_payload, dict):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "INPUT_ERROR",
                        "message": "PAYLOAD_JSON_MUST_BE_OBJECT",
                        **_safe_flags(),
                    },
                )

            payload = dict(raw_payload)
            human_approved = bool(payload.pop("human_approved", False))
            approved_by = payload.pop("approved_by", None)
            if approved_by is not None and not isinstance(approved_by, str):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "INPUT_ERROR",
                        "message": "APPROVED_BY_MUST_BE_STRING",
                        **_safe_flags(),
                    },
                )

            try:
                result = build_agent_task_intake_payload(
                    payload,
                    root_dir=root_dir(),
                    human_approved=human_approved,
                    approved_by=approved_by,
                )
            except AgentWorkValidationError as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "INPUT_ERROR",
                        "message": str(exc),
                        **_safe_flags(),
                    },
                ) from exc
            except (AgentEvidenceError, AgentTaskStoreError, OSError) as exc:
                raise _query_error("INTAKE_PERSISTENCE_ERROR", str(exc), 500) from exc

            return result

    if not _route_exists(app, "/agent/tasks", "GET"):
        @app.get("/agent/tasks")
        def agent_task_query(
            source_agent: str | None = Query(default=None),
            action: str | None = Query(default=None),
            state: str | None = Query(default=None),
            risk_level: str | None = Query(default=None),
            created_from: str | None = Query(default=None),
            created_to: str | None = Query(default=None),
            limit: int | None = Query(default=None, ge=0, le=500),
        ):
            try:
                return build_agent_task_query_payload(
                    root_dir=root_dir(),
                    source_agent=source_agent,
                    action=action,
                    state=state,
                    risk_level=risk_level,
                    created_from=created_from,
                    created_to=created_to,
                    limit=limit,
                )
            except (AgentTaskStoreError, OSError) as exc:
                raise _query_error("QUERY_ERROR", str(exc), 500) from exc

    if not _route_exists(app, "/agent/tasks/{work_id}/approval", "POST"):
        @app.post("/agent/tasks/{work_id}/approval")
        async def agent_task_patch_approval(work_id: str, request: Request):
            payload = await _json_object_payload(request)
            try:
                approved_by = _clean_optional_string(payload, "approved_by")
                reason = _clean_optional_string(payload, "reason")
                return build_agent_task_patch_approval_payload(
                    root_dir=root_dir(),
                    work_id=work_id,
                    approved_by=approved_by,
                    reason=reason,
                )
            except AgentPatchApprovalError as exc:
                message = str(exc)
                if message == "AGENT_TASK_NOT_FOUND":
                    raise _patch_error("NOT_FOUND", message, 404) from exc
                if message == "APPROVAL_DECISION_ALREADY_RECORDED":
                    raise _patch_error("CONFLICT", message, 409) from exc
                if message in {"APPROVAL_DECISION_NOT_APPROVED", "PATCH_NOT_ALLOWED"}:
                    raise _patch_error("REJECTED", message, 409) from exc
                raise _patch_error("INPUT_ERROR", message, 400) from exc
            except (AgentTaskStoreError, OSError) as exc:
                raise _patch_error("APPROVAL_PERSISTENCE_ERROR", str(exc), 500) from exc

    if not _route_exists(app, "/agent/tasks/{work_id}/rejection", "POST"):
        @app.post("/agent/tasks/{work_id}/rejection")
        async def agent_task_patch_rejection(work_id: str, request: Request):
            payload = await _json_object_payload(request)
            try:
                rejected_by = _clean_optional_string(payload, "rejected_by")
                reason = _clean_optional_string(payload, "reason")
                return build_agent_task_patch_rejection_payload(
                    root_dir=root_dir(),
                    work_id=work_id,
                    rejected_by=rejected_by,
                    reason=reason,
                )
            except AgentPatchApprovalError as exc:
                message = str(exc)
                if message == "AGENT_TASK_NOT_FOUND":
                    raise _patch_error("NOT_FOUND", message, 404) from exc
                if message == "APPROVAL_DECISION_ALREADY_RECORDED":
                    raise _patch_error("CONFLICT", message, 409) from exc
                raise _patch_error("INPUT_ERROR", message, 400) from exc
            except (AgentTaskStoreError, OSError) as exc:
                raise _patch_error("APPROVAL_PERSISTENCE_ERROR", str(exc), 500) from exc

    if not _route_exists(app, "/agent/tasks/{work_id}", "GET"):
        @app.get("/agent/tasks/{work_id}")
        def agent_task_detail(work_id: str):
            try:
                result = build_agent_task_detail_payload(root_dir=root_dir(), work_id=work_id)
            except (AgentTaskStoreError, AgentPatchApprovalError, OSError) as exc:
                raise _query_error("QUERY_ERROR", str(exc), 500) from exc
            if result is None:
                raise _query_error("NOT_FOUND", "AGENT_TASK_NOT_FOUND", 404)
            return result
