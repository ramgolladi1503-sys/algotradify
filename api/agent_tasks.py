from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query, Request

from agent_system.approval import approve_agent_work
from agent_system.evidence import AgentEvidenceError, write_agent_evidence
from agent_system.scope_guard import assess_agent_scope
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


def _safe_flags() -> dict[str, Any]:
    return {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
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
    return {
        "contract": AGENT_TASKS_QUERY_CONTRACT,
        "work_id": work_id,
        "task": task,
        "metadata": {
            "scope": "agent_task_detail_query_only_no_execution",
        },
        **_safe_flags(),
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

    if not _route_exists(app, "/agent/tasks/{work_id}", "GET"):
        @app.get("/agent/tasks/{work_id}")
        def agent_task_detail(work_id: str):
            try:
                result = build_agent_task_detail_payload(root_dir=root_dir(), work_id=work_id)
            except (AgentTaskStoreError, OSError) as exc:
                raise _query_error("QUERY_ERROR", str(exc), 500) from exc
            if result is None:
                raise _query_error("NOT_FOUND", "AGENT_TASK_NOT_FOUND", 404)
            return result
