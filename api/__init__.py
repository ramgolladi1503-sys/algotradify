from __future__ import annotations


def _mount_dry_run_route() -> None:
    from api import server
    from api.dry_run_execution_route import install_dry_run_execution_route

    install_dry_run_execution_route(
        server.app,
        runtime_root_provider=lambda: server._runtime_root(),
        top_executable_provider=lambda limit, min_quality_score: server._top_executable_payload(limit, min_quality_score),
        readiness_provider=lambda limit: server._execution_readiness_payload(limit),
        safety_provider=lambda request, limit, min_quality_score: server._execution_safety_payload(request, limit, min_quality_score),
        approval_provider=lambda candidate_id, now_epoch: server._approval_audit_payload(candidate_id=candidate_id, now_epoch=now_epoch),
        readiness_matcher=lambda top_executable, readiness: server._matching_readiness(top_executable, readiness),
    )


_mount_dry_run_route()
