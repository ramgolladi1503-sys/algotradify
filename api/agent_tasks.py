from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request

from agent_system.approval import approve_agent_work
from agent_system.evidence import AgentEvidenceError, write_agent_evidence
from agent_system.scope_guard import assess_agent_scope
from agent_system.task_store import AgentTaskStoreError, build_agent_task_record, persist_agent_task
from agent_system.work_contract import AgentWorkValidationError, normalize_agent_work_request


AGENT_TASKS_ROUTE_CONTRACT = "agent_tasks_intake_v1"


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


def _safe_flags() -> dict[str, Any]:
    return {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }


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


def install_agent_tasks_route(
    app: FastAPI,
    *,
    root_dir_provider: Callable[[], str | Path] | None = None,
) -> None:
    if any(getattr(route, "path", None) == "/agent/tasks" for route in app.routes):
        return

    def root_dir() -> str | Path:
        if root_dir_provider is None:
            return "runtime/agent_work"
        return root_dir_provider()

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
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "INTAKE_PERSISTENCE_ERROR",
                    "message": str(exc),
                    **_safe_flags(),
                },
            ) from exc

        return result
