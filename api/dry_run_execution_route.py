from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Query, Request

from dry_run_execution import append_dry_run_execution, build_dry_run_execution


DRY_RUN_EXPORT_BUNDLE_TYPE = "DRY_RUN_EVIDENCE_BUNDLE"
DRY_RUN_EXPORT_SCHEMA_VERSION = "1.0"
DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS = (DRY_RUN_EXPORT_SCHEMA_VERSION,)
DRY_RUN_EXPORT_REQUIRED_KEYS = frozenset(
    {
        "bundle_type",
        "schema_version",
        "created",
        "candidate_id",
        "dry_run_order_id",
        "dry_run_only",
        "is_order_action",
        "broker_api_called",
        "real_order_id",
        "status",
        "blockers",
        "warnings",
        "selected_candidate_snapshot",
        "execution_safety_snapshot",
        "approval_snapshot",
        "readiness_snapshot",
        "dry_run_intent",
        "lifecycle_event",
        "outcome_event",
        "export_preview_only",
    }
)
DRY_RUN_EXPORT_SAFE_FLAGS = {
    "dry_run_only": True,
    "is_order_action": False,
    "broker_api_called": False,
    "real_order_id": None,
    "export_preview_only": True,
}


def dry_run_export_schema_contract() -> dict[str, Any]:
    return {
        "bundle_type": DRY_RUN_EXPORT_BUNDLE_TYPE,
        "schema_version": DRY_RUN_EXPORT_SCHEMA_VERSION,
        "compatible_schema_versions": list(DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS),
        "required_keys": sorted(DRY_RUN_EXPORT_REQUIRED_KEYS),
        "safe_flags": dict(DRY_RUN_EXPORT_SAFE_FLAGS),
    }


def build_dry_run_export_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    intent = payload.get("intent") if isinstance(payload.get("intent"), dict) else {}
    lifecycle = payload.get("lifecycle_event") if isinstance(payload.get("lifecycle_event"), dict) else {}
    outcome = payload.get("outcome_event") if isinstance(payload.get("outcome_event"), dict) else {}
    bundle = {
        "bundle_type": DRY_RUN_EXPORT_BUNDLE_TYPE,
        "schema_version": DRY_RUN_EXPORT_SCHEMA_VERSION,
        "created": payload.get("created") is True,
        "candidate_id": payload.get("candidate_id") or intent.get("candidate_id"),
        "dry_run_order_id": intent.get("dry_run_order_id"),
        "dry_run_only": DRY_RUN_EXPORT_SAFE_FLAGS["dry_run_only"],
        "is_order_action": DRY_RUN_EXPORT_SAFE_FLAGS["is_order_action"],
        "broker_api_called": DRY_RUN_EXPORT_SAFE_FLAGS["broker_api_called"],
        "real_order_id": DRY_RUN_EXPORT_SAFE_FLAGS["real_order_id"],
        "status": "BUNDLE_READY" if payload.get("created") is True else "BUNDLE_BLOCKED",
        "blockers": list(payload.get("blockers") or []),
        "warnings": list(payload.get("warnings") or []),
        "selected_candidate_snapshot": intent.get("top_executable_snapshot") or payload.get("top_executable_snapshot") or {},
        "execution_safety_snapshot": intent.get("execution_safety_snapshot") or payload.get("execution_safety_snapshot") or {},
        "approval_snapshot": intent.get("approval_snapshot") or payload.get("approval_snapshot") or {},
        "readiness_snapshot": intent.get("readiness_snapshot") or payload.get("readiness_snapshot") or {},
        "dry_run_intent": intent,
        "lifecycle_event": lifecycle,
        "outcome_event": outcome,
        "export_preview_only": DRY_RUN_EXPORT_SAFE_FLAGS["export_preview_only"],
    }
    return bundle


def build_dry_run_execution_payload(
    *,
    request: Request,
    runtime_root: Path,
    top_executable_provider: Callable[[int, float], dict[str, Any]],
    readiness_provider: Callable[[int], list[dict[str, Any]]],
    safety_provider: Callable[[Request, int, float], dict[str, Any]],
    approval_provider: Callable[[str | None, float | None], dict[str, Any]],
    readiness_matcher: Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any] | None],
    limit: int,
    min_quality_score: float,
    now_epoch: float | None = None,
    append: bool = False,
) -> dict[str, Any]:
    top_executable = top_executable_provider(limit, min_quality_score)
    readiness = readiness_provider(limit)
    matching_readiness = readiness_matcher(top_executable, readiness)
    safety = safety_provider(request, limit, min_quality_score)
    selected = top_executable.get("selected") if isinstance(top_executable, dict) else None
    candidate_id = selected.get("candidate_id") if isinstance(selected, dict) else None
    approval = approval_provider(candidate_id, now_epoch)
    result = build_dry_run_execution(
        top_executable=top_executable,
        execution_safety=safety,
        approval=approval,
        readiness=matching_readiness,
        ts_epoch=now_epoch,
    )
    if append:
        result = append_dry_run_execution(runtime_root, result)
    payload = result.to_dict()
    payload["candidate_id"] = candidate_id
    payload["top_executable_status"] = top_executable.get("status") if isinstance(top_executable, dict) else None
    payload["readiness_records_checked"] = len(readiness)
    return payload


def install_dry_run_execution_route(
    app: FastAPI,
    *,
    runtime_root_provider: Callable[[], Path],
    top_executable_provider: Callable[[int, float], dict[str, Any]],
    readiness_provider: Callable[[int], list[dict[str, Any]]],
    safety_provider: Callable[[Request, int, float], dict[str, Any]],
    approval_provider: Callable[[str | None, float | None], dict[str, Any]],
    readiness_matcher: Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any] | None],
) -> None:
    if not any(getattr(route, "path", None) == "/dry-run-execution" for route in app.routes):
        @app.get("/dry-run-execution")
        def dry_run_execution(
            request: Request,
            limit: int = Query(default=25, ge=1, le=200),
            min_quality_score: float = Query(default=50.0, ge=0.0, le=100.0),
            now_epoch: float | None = Query(default=None),
            append: bool = Query(default=False),
        ):
            return build_dry_run_execution_payload(
                request=request,
                runtime_root=runtime_root_provider(),
                top_executable_provider=top_executable_provider,
                readiness_provider=readiness_provider,
                safety_provider=safety_provider,
                approval_provider=approval_provider,
                readiness_matcher=readiness_matcher,
                limit=limit,
                min_quality_score=min_quality_score,
                now_epoch=now_epoch,
                append=append,
            )

    if any(getattr(route, "path", None) == "/dry-run-execution/export" for route in app.routes):
        return

    @app.get("/dry-run-execution/export")
    def dry_run_execution_export(
        request: Request,
        limit: int = Query(default=25, ge=1, le=200),
        min_quality_score: float = Query(default=50.0, ge=0.0, le=100.0),
        now_epoch: float | None = Query(default=None),
    ):
        payload = build_dry_run_execution_payload(
            request=request,
            runtime_root=runtime_root_provider(),
            top_executable_provider=top_executable_provider,
            readiness_provider=readiness_provider,
            safety_provider=safety_provider,
            approval_provider=approval_provider,
            readiness_matcher=readiness_matcher,
            limit=limit,
            min_quality_score=min_quality_score,
            now_epoch=now_epoch,
            append=False,
        )
        return build_dry_run_export_bundle(payload)
