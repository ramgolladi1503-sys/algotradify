from __future__ import annotations


def _mount_dry_run_route() -> None:
    from api import server
    from api.dry_run_execution_route import install_dry_run_execution_route

    install_dry_run_execution_route(
        server.app,
        runtime_root_provider=server._runtime_root,
        top_executable_provider=server._top_executable_payload,
        readiness_provider=server._execution_readiness_payload,
        safety_provider=server._execution_safety_payload,
        approval_provider=server._approval_audit_payload,
        readiness_matcher=server._matching_readiness,
    )


_mount_dry_run_route()
