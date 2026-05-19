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


class RuntimePreflightCheck(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    status: str
    message: str
    path: str | None = None
    metadata: dict[str, Any] | None = None


class RuntimePreflightResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    runtime_root: str | None = None
    runtime_artifact_root: str | None = None
    checked_at_source: str
    summary: dict[str, int]
    checks: list[RuntimePreflightCheck]


class RuntimeOwnershipResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    contract: str
    status: str | None = None
    runtime_ownership: str
    native_source_present: bool
    native_main_promoted: bool
    native_required: bool
    external_runtime_allowed: bool
    external_runtime_used: bool
    runtime_root: str | None = None
    runtime_artifact_root: str | None = None
    can_start_native_runtime: bool
    warnings: list[str]
    blockers: list[str]
    summary: dict[str, int]
    checked_at_source: str
    preflight_checked_at_source: str | None = None
    read_only: bool
    audit_only: bool
    is_order_action: bool
    broker_api_called: bool
    real_order_id: str | None = None
    live_mode_touched: bool


class BrokerAuthVisibilityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    contract: str
    status: str
    auth_state: str
    source: str
    runtime_artifact_root: str
    token_file_path: str
    api_key_present: bool
    api_key_tail4: str
    api_secret_present: bool
    token_file_present: bool
    token_file_length: int
    token_file_tail4: str
    token_file_usable_shape: bool
    env_token_present: bool
    env_token_length: int
    env_token_tail4: str
    env_token_usable_shape: bool
    can_validate_locally: bool
    can_attempt_login_locally: bool
    login_required: bool
    operator_commands: dict[str, str]
    blockers: list[str]
    warnings: list[str]
    read_only: bool
    auth_visibility_only: bool
    is_order_action: bool
    broker_api_called: bool
    profile_probe_called: bool
    token_mutated: bool
    raw_token_exposed: bool
    api_secret_exposed: bool
    real_order_id: str | None = None
    live_mode_touched: bool


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


class StrategyInfoResponse(BaseModel):
    strategy_id: str
    setup_family: str
    display_name: str
    required_data: list[str]


class StrategyCandidateDraftResponse(BaseModel):
    candidate_id: str
    symbol: str
    strategy_id: str
    setup_family: str
    direction: str
    confidence: float | int
    entry_hypothesis: dict[str, Any]
    invalidation_hypothesis: dict[str, Any]
    required_market_regime: str | None = None
    required_data: list[str]
    signal_features: dict[str, Any]
    blockers: list[str]
    warnings: list[str]
    provenance: dict[str, Any]
    raw: dict[str, Any]
    is_execution_decision: bool


class CandidateTruthRecordResponse(BaseModel):
    candidate_id: str
    symbol: str | None = None
    strategy_id: str | None = None
    setup_family: str | None = None
    truth_status: str
    blockers: list[str]
    warnings: list[str]
    provenance: dict[str, Any]
    normalized: dict[str, Any]
    raw: dict[str, Any]
    is_candidate_truth_record: bool
    is_execution_decision: bool


class OpportunityLayerRecordResponse(BaseModel):
    candidate_id: str
    symbol: str | None = None
    strategy_id: str | None = None
    setup_family: str | None = None
    truth_status: str
    opportunity_status: str
    rank_score: float | int
    rank: int | None = None
    selected: bool
    blockers: list[str]
    warnings: list[str]
    provenance: dict[str, Any]
    candidate_truth: dict[str, Any]
    is_execution_decision: bool


class OpportunityLayerResponse(BaseModel):
    status: str
    reason: str | None = None
    counts: dict[str, int]
    selected: OpportunityLayerRecordResponse | None = None
    ranked: list[OpportunityLayerRecordResponse]
    blocked: list[OpportunityLayerRecordResponse]
    dropped: list[OpportunityLayerRecordResponse]
    diagnostics: dict[str, Any]
    is_execution_decision: bool


class ExecutionReadinessResponse(BaseModel):
    candidate_id: str
    execution_allowed: bool
    status: str
    blockers: list[str]
    warnings: list[str]
    evidence: dict[str, Any]
    is_execution_readiness_record: bool
    is_order: bool


class TradeQualityResponse(BaseModel):
    candidate_id: str
    quality_score: float | int
    status: str
    rank: int | None = None
    components: dict[str, float]
    penalties: dict[str, float]
    blockers: list[str]
    warnings: list[str]
    execution_readiness: dict[str, Any]
    is_order: bool


class TopExecutableSelectionResponse(BaseModel):
    status: str
    selected: dict[str, Any] | None = None
    eligible: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    reason: str | None = None
    is_order: bool
    is_selector_decision: bool


class FillLifecycleStateResponse(BaseModel):
    candidate_id: str
    current_status: str
    terminal: bool
    filled_quantity: float | int | None = None
    average_price: float | int | None = None
    events: list[dict[str, Any]]
    blockers: list[str]
    warnings: list[str]
    is_order_submission: bool


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