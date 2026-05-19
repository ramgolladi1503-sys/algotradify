from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import FastAPI

from api.auth_visibility import build_broker_auth_visibility_payload
from api.schemas import BrokerAuthVisibilityResponse


def install_auth_visibility_route(app: FastAPI, *, runtime_artifact_root_provider: Callable[[], Path]) -> None:
    """Install read-only broker auth visibility route.

    This route is local visibility only. It must not call broker APIs, run login,
    mutate tokens, expose raw credentials, create orders, or touch live mode.
    """

    @app.get("/broker/auth/visibility", response_model=BrokerAuthVisibilityResponse)
    def broker_auth_visibility() -> dict:
        return build_broker_auth_visibility_payload(
            runtime_artifact_root=runtime_artifact_root_provider()
        )
