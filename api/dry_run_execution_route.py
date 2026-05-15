from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Query, Request

from dry_run_execution import append_dry_run_execution, build_dry_run_execution


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
