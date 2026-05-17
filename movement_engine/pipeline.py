from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from movement_engine.candidate_pool import CandidatePoolResult, build_candidate_pool
from movement_engine.context import StrategyContext
from movement_engine.contract import StrategyCandidate
from movement_engine.no_trade_filter import NoTradeFilterBatchResult, apply_no_trade_filter_to_candidates
from movement_engine.option_pressure import attach_option_pressure_to_candidates
from movement_engine.providers import (
    register_compression_trend_providers,
    register_opening_drive_orb_providers,
    register_vwap_trap_providers,
)
from movement_engine.ranker import MovementRankResult, rank_movement_candidates
from movement_engine.registry import MovementRegistryRunResult, MovementStrategyRegistry


PIPELINE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class MovementOpportunityPipelineSummary:
    schema_version: int = PIPELINE_SCHEMA_VERSION
    provider_count: int = 0
    registry_candidate_count: int = 0
    pooled_candidate_count: int = 0
    option_enriched_count: int = 0
    allowed_count: int = 0
    blocked_count: int = 0
    no_trade_count: int = 0
    ranked_count: int = 0
    excluded_count: int = 0
    diagnostic_count: int = 0
    warning_count: int = 0
    top_candidate_id: str | None = None
    read_only: bool = True

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_count": self.provider_count,
            "registry_candidate_count": self.registry_candidate_count,
            "pooled_candidate_count": self.pooled_candidate_count,
            "option_enriched_count": self.option_enriched_count,
            "allowed_count": self.allowed_count,
            "blocked_count": self.blocked_count,
            "no_trade_count": self.no_trade_count,
            "ranked_count": self.ranked_count,
            "excluded_count": self.excluded_count,
            "diagnostic_count": self.diagnostic_count,
            "warning_count": self.warning_count,
            "top_candidate_id": self.top_candidate_id,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class MovementOpportunityPipelineResult:
    summary: MovementOpportunityPipelineSummary
    registry_result: MovementRegistryRunResult
    candidate_pool_result: CandidatePoolResult
    option_enriched_candidates: tuple[StrategyCandidate, ...]
    no_trade_filter_result: NoTradeFilterBatchResult
    rank_result: MovementRankResult
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "registry_result": self.registry_result.to_dict(),
            "candidate_pool_result": self.candidate_pool_result.to_dict(),
            "option_enriched_candidates": [candidate.to_dict() for candidate in self.option_enriched_candidates],
            "no_trade_filter_result": self.no_trade_filter_result.to_dict(),
            "rank_result": self.rank_result.to_dict(),
            "warnings": list(self.warnings),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "read_only": True,
            "is_order_action": self.is_order_action,
        }


def build_default_movement_registry() -> MovementStrategyRegistry:
    """Build the default read-only movement provider registry."""

    registry = MovementStrategyRegistry()
    register_opening_drive_orb_providers(registry)
    register_compression_trend_providers(registry)
    register_vwap_trap_providers(registry)
    return registry


def run_movement_opportunity_pipeline(
    context: StrategyContext | None,
    *,
    registry: MovementStrategyRegistry | None = None,
) -> MovementOpportunityPipelineResult:
    """Run the read-only movement opportunity pipeline.

    Flow:

    StrategyContext -> registry -> candidate pool -> option pressure ->
    no-trade filter -> ranker.

    The function never calls brokers, never creates order intents, and never
    returns order actions.
    """

    movement_registry = registry or build_default_movement_registry()
    registry_result = movement_registry.run(context)
    candidate_pool_result = build_candidate_pool(
        registry_result.candidates,
        upstream_warnings=registry_result.warnings,
        upstream_diagnostics=registry_result.diagnostics,
    )

    option_enriched_candidates = attach_option_pressure_to_candidates(candidate_pool_result.candidates, context)
    no_trade_filter_result = apply_no_trade_filter_to_candidates(option_enriched_candidates)
    rank_result = rank_movement_candidates(no_trade_filter_result.candidates)

    warnings = _collect_warnings(
        registry_result.warnings,
        candidate_pool_result.warnings,
        no_trade_filter_result.warnings,
        rank_result.warnings,
    )
    diagnostics = _collect_diagnostics(
        registry_result.diagnostics,
        candidate_pool_result.diagnostics,
        no_trade_filter_result.diagnostics,
        rank_result.diagnostics,
    )

    summary = MovementOpportunityPipelineSummary(
        provider_count=registry_result.provider_count,
        registry_candidate_count=len(registry_result.candidates),
        pooled_candidate_count=len(candidate_pool_result.candidates),
        option_enriched_count=len(option_enriched_candidates),
        allowed_count=no_trade_filter_result.summary.allowed_count,
        blocked_count=no_trade_filter_result.summary.blocked_count,
        no_trade_count=no_trade_filter_result.summary.no_trade_count,
        ranked_count=rank_result.summary.ranked_count,
        excluded_count=rank_result.summary.excluded_count,
        diagnostic_count=len(diagnostics),
        warning_count=len(warnings),
        top_candidate_id=rank_result.summary.top_candidate_id,
    )

    return MovementOpportunityPipelineResult(
        summary=summary,
        registry_result=registry_result,
        candidate_pool_result=candidate_pool_result,
        option_enriched_candidates=option_enriched_candidates,
        no_trade_filter_result=no_trade_filter_result,
        rank_result=rank_result,
        warnings=warnings,
        diagnostics=diagnostics,
    )


def _collect_warnings(*warning_groups: tuple[str, ...]) -> tuple[str, ...]:
    warnings: list[str] = []
    for group in warning_groups:
        warnings.extend(group)
    return tuple(_dedupe(warnings))


def _collect_diagnostics(*diagnostic_groups: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    diagnostics: list[dict[str, Any]] = []
    for group in diagnostic_groups:
        diagnostics.extend(_with_stage(item) for item in group)
    return tuple(diagnostics)


def _with_stage(item: dict[str, Any]) -> dict[str, Any]:
    payload = dict(item)
    payload.setdefault("is_order_action", False)
    return payload


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
