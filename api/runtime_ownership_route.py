from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import FastAPI

from api.runtime_ownership import build_runtime_ownership_payload
from api.schemas import RuntimeOwnershipResponse


def install_runtime_ownership_route(app: FastAPI, *, repo_root_provider: Callable[[], Path]) -> None:
    """Install read-only runtime ownership API route.

    This route is visibility-only. It must not start the runtime, call broker APIs,
    create orders, mutate execution mode, or write runtime state.
    """

    @app.get("/runtime/ownership", response_model=RuntimeOwnershipResponse)
    def runtime_ownership() -> dict:
        return build_runtime_ownership_payload(base_repo_root=repo_root_provider())
