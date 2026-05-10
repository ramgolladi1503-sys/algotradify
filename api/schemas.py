from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="API health status")


class RuntimeHealthResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    reason: str | None = None
    runtime_root: str | None = None
    tradebot_root: str | None = None
    mode: str | None = None
    market_open: bool | None = None
    feed: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    snapshot_ts_epoch: float | int | None = None
    raw: dict[str, Any] | None = None


class RuntimeSnapshotResponse(BaseModel):
    runtime_root: str
    tradebot_root: str | None = None
    cycle_stage: str | None = None
    market_mode: str | None = None
    cycle_ok: bool | None = None
    top_executable_count: int
    top_advisory_count: int
    primary_blocker: str | None = None
    reason: str | None = None
    ts_epoch: float | int | None = None


class OpportunityResponse(BaseModel):
    candidate_id: str
    symbol: str | None = None
    strategy: str | None = None
    permission: str | None = None
    final_action: str | None = None
    status: str | None = None
    execution_status: str | None = None
    confidence: float | int | None = None
    score: float | int | None = None
    bucket: str
    source: str
    raw: dict[str, Any]


class RuntimeNoticePayload(BaseModel):
    source: str
    status: str
    reason: str


class RuntimeNoticeEvent(BaseModel):
    type: str = "runtime_notice"
    payload: RuntimeNoticePayload


class RuntimeSnapshotEvent(BaseModel):
    type: str = "runtime_snapshot"
    payload: RuntimeSnapshotResponse
