from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TradeQualityStatus(StrEnum):
    QUALIFIED = "QUALIFIED"
    BLOCKED_NOT_EXECUTION_READY = "BLOCKED_NOT_EXECUTION_READY"
    DEGRADED_BY_WARNINGS = "DEGRADED_BY_WARNINGS"


@dataclass(frozen=True)
class TradeQualityScore:
    candidate_id: str
    quality_score: float
    status: TradeQualityStatus
    rank: int | None = None
    components: dict[str, float] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    execution_readiness: dict[str, Any] = field(default_factory=dict)

    @property
    def is_order(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "quality_score": self.quality_score,
            "status": self.status.value,
            "rank": self.rank,
            "components": dict(self.components),
            "penalties": dict(self.penalties),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "execution_readiness": dict(self.execution_readiness),
            "is_order": self.is_order,
        }


def score_trade_quality(execution_readiness: dict[str, Any]) -> TradeQualityScore:
    candidate_id = str(execution_readiness.get("candidate_id") or "unknown")
    blockers = list(execution_readiness.get("blockers") or [])
    warnings = list(execution_readiness.get("warnings") or [])

    if not execution_readiness.get("execution_allowed"):
        return TradeQualityScore(
            candidate_id=candidate_id,
            quality_score=0.0,
            status=TradeQualityStatus.BLOCKED_NOT_EXECUTION_READY,
            blockers=blockers or ["EXECUTION_NOT_ALLOWED"],
            warnings=warnings,
            execution_readiness=execution_readiness,
        )

    evidence = execution_readiness.get("evidence") or {}
    candidate_truth = evidence.get("candidate_truth") or {}
    opportunity = evidence.get("opportunity") or {}
    broker = evidence.get("broker_contract") or {}
    market = evidence.get("market_readiness") or {}
    risk = evidence.get("risk") or {}

    components = {
        "confidence": _confidence_component(candidate_truth, opportunity),
        "broker_contract": _broker_component(broker),
        "quote_freshness": _quote_freshness_component(market),
        "liquidity": _liquidity_component(market),
        "risk": _risk_component(risk),
    }
    penalties = _penalties(execution_readiness, broker, market, risk)
    raw_score = sum(components.values()) - sum(penalties.values())
    score = max(0.0, min(100.0, round(raw_score, 2)))
    status = TradeQualityStatus.DEGRADED_BY_WARNINGS if warnings or penalties else TradeQualityStatus.QUALIFIED

    return TradeQualityScore(
        candidate_id=candidate_id,
        quality_score=score,
        status=status,
        components=components,
        penalties=penalties,
        blockers=blockers,
        warnings=warnings,
        execution_readiness=execution_readiness,
    )


def rank_trade_quality(execution_readiness_records: list[dict[str, Any]]) -> list[TradeQualityScore]:
    scored = [score_trade_quality(record) for record in execution_readiness_records]
    scored.sort(key=lambda row: (row.quality_score, row.candidate_id), reverse=True)
    ranked: list[TradeQualityScore] = []
    for index, row in enumerate(scored, start=1):
        ranked.append(
            TradeQualityScore(
                candidate_id=row.candidate_id,
                quality_score=row.quality_score,
                status=row.status,
                rank=index,
                components=dict(row.components),
                penalties=dict(row.penalties),
                blockers=list(row.blockers),
                warnings=list(row.warnings),
                execution_readiness=dict(row.execution_readiness),
            )
        )
    return ranked


def _confidence_component(candidate_truth: dict[str, Any], opportunity: dict[str, Any]) -> float:
    value = _first_number(
        candidate_truth.get("normalized", {}).get("confidence") if isinstance(candidate_truth.get("normalized"), dict) else None,
        candidate_truth.get("raw", {}).get("confidence") if isinstance(candidate_truth.get("raw"), dict) else None,
        opportunity.get("rank_score"),
        opportunity.get("score"),
    )
    if value is None:
        return 10.0
    return max(0.0, min(25.0, (float(value) / 100.0) * 25.0))


def _broker_component(broker: dict[str, Any]) -> float:
    status = broker.get("readiness_status")
    if status == "RESOLVED_EXACT":
        return 20.0
    if status == "RESOLVED_FALLBACK":
        return 14.0
    return 0.0


def _quote_freshness_component(market: dict[str, Any]) -> float:
    quote = market.get("quote") if isinstance(market.get("quote"), dict) else market
    age = _first_number(quote.get("quote_age_sec"), quote.get("ltp_age_sec"), quote.get("age_sec")) if isinstance(quote, dict) else None
    max_age = _first_number(quote.get("max_quote_age_sec")) if isinstance(quote, dict) else None
    if age is None:
        return 8.0 if market.get("status") == "READY" else 0.0
    max_age = max_age or 2.0
    freshness = max(0.0, 1.0 - min(float(age) / float(max_age), 1.0))
    return round(15.0 * freshness, 2)


def _liquidity_component(market: dict[str, Any]) -> float:
    quote = market.get("quote") if isinstance(market.get("quote"), dict) else market
    spread_pct = _first_number(quote.get("spread_pct")) if isinstance(quote, dict) else None
    max_spread = _first_number(quote.get("max_spread_pct")) if isinstance(quote, dict) else None
    if spread_pct is None:
        return 12.0 if market.get("status") == "READY" else 0.0
    max_spread = max_spread or 1.0
    quality = max(0.0, 1.0 - min(float(spread_pct) / float(max_spread), 1.0))
    return round(20.0 * quality, 2)


def _risk_component(risk: dict[str, Any]) -> float:
    if risk.get("allowed") is True:
        return 20.0
    return 0.0


def _penalties(execution_readiness: dict[str, Any], broker: dict[str, Any], market: dict[str, Any], risk: dict[str, Any]) -> dict[str, float]:
    penalties: dict[str, float] = {}
    warnings = list(execution_readiness.get("warnings") or [])
    if warnings:
        penalties["warnings"] = min(10.0, 2.0 * len(warnings))
    if broker.get("fallback_used"):
        penalties["broker_fallback"] = 5.0
    market_warnings = market.get("warnings") if isinstance(market, dict) else None
    if market_warnings:
        penalties["market_warnings"] = min(6.0, 2.0 * len(market_warnings))
    risk_warnings = risk.get("warnings") if isinstance(risk, dict) else None
    if risk_warnings:
        penalties["risk_warnings"] = min(6.0, 2.0 * len(risk_warnings))
    return penalties


def _first_number(*values: Any) -> float | None:
    for value in values:
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
