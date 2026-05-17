from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

from movement_engine import StrategyContext, run_movement_opportunity_pipeline


MOVEMENT_OPPORTUNITY_API_SCHEMA_VERSION = "1.0"
MOVEMENT_OPPORTUNITY_API_ROUTE = "/movement-opportunity"

_NUMERIC_CONTEXT_FIELDS = {
    "spot_ltp",
    "vwap",
    "day_high",
    "day_low",
    "orb_high",
    "orb_low",
    "prev_day_high",
    "prev_day_low",
    "atr",
    "atr_short",
    "atr_long",
    "range_width_pct",
    "volume_z",
    "option_ce_ltp",
    "option_pe_ltp",
    "ce_premium_change",
    "pe_premium_change",
    "ce_spread_pct",
    "pe_spread_pct",
    "ce_depth",
    "pe_depth",
    "option_ltp_age_sec",
}

_INT_CONTEXT_FIELDS = {"minutes_since_open", "minutes_to_close"}

_STRING_CONTEXT_FIELDS = {
    "volatility_state",
    "regime_hint",
    "quote_source",
    "time_of_day",
    "expiry_context",
}


def movement_opportunity_schema_contract() -> dict[str, Any]:
    return {
        "route": MOVEMENT_OPPORTUNITY_API_ROUTE,
        "schema_version": MOVEMENT_OPPORTUNITY_API_SCHEMA_VERSION,
        "method": "GET",
        "read_only": True,
        "is_order_action": False,
        "required_query_params": ["symbol", "ts_epoch"],
        "optional_numeric_query_params": sorted(_NUMERIC_CONTEXT_FIELDS),
        "optional_integer_query_params": sorted(_INT_CONTEXT_FIELDS),
        "optional_string_query_params": sorted(_STRING_CONTEXT_FIELDS),
        "response_top_level_keys": [
            "api_schema_version",
            "route",
            "method",
            "read_only",
            "is_order_action",
            "context",
            "summary",
            "ranked_candidates",
            "rank_records",
            "exclusions",
            "warnings",
            "diagnostics",
            "pipeline",
        ],
    }


def build_strategy_context_from_query(
    *,
    symbol: str,
    ts_epoch: float,
    query_params: dict[str, Any],
) -> StrategyContext:
    payload: dict[str, Any] = {
        "symbol": str(symbol).upper(),
        "ts_epoch": float(ts_epoch),
    }
    for field in _NUMERIC_CONTEXT_FIELDS:
        payload[field] = _optional_float(query_params.get(field))
    for field in _INT_CONTEXT_FIELDS:
        payload[field] = _optional_int(query_params.get(field))
    for field in _STRING_CONTEXT_FIELDS:
        value = query_params.get(field)
        payload[field] = str(value) if value not in (None, "") else None
    return StrategyContext(**payload)


def build_movement_opportunity_api_payload(context: StrategyContext) -> dict[str, Any]:
    pipeline_result = run_movement_opportunity_pipeline(context)
    pipeline_payload = pipeline_result.to_dict()
    rank_payload = pipeline_payload["rank_result"]
    return {
        "api_schema_version": MOVEMENT_OPPORTUNITY_API_SCHEMA_VERSION,
        "route": MOVEMENT_OPPORTUNITY_API_ROUTE,
        "method": "GET",
        "read_only": True,
        "is_order_action": False,
        "context": context.to_dict(),
        "summary": pipeline_payload["summary"],
        "ranked_candidates": rank_payload["ranked_candidates"],
        "rank_records": rank_payload["rank_records"],
        "exclusions": rank_payload["exclusions"],
        "warnings": pipeline_payload["warnings"],
        "diagnostics": pipeline_payload["diagnostics"],
        "pipeline": pipeline_payload,
    }


def install_movement_opportunity_route(app: FastAPI) -> None:
    if not any(getattr(route, "path", None) == MOVEMENT_OPPORTUNITY_API_ROUTE for route in app.routes):
        @app.get(MOVEMENT_OPPORTUNITY_API_ROUTE)
        def movement_opportunity(
            symbol: str = Query(..., min_length=1),
            ts_epoch: float = Query(...),
            spot_ltp: float | None = Query(default=None),
            vwap: float | None = Query(default=None),
            day_high: float | None = Query(default=None),
            day_low: float | None = Query(default=None),
            orb_high: float | None = Query(default=None),
            orb_low: float | None = Query(default=None),
            prev_day_high: float | None = Query(default=None),
            prev_day_low: float | None = Query(default=None),
            atr: float | None = Query(default=None),
            atr_short: float | None = Query(default=None),
            atr_long: float | None = Query(default=None),
            range_width_pct: float | None = Query(default=None),
            volume_z: float | None = Query(default=None),
            volatility_state: str | None = Query(default=None),
            regime_hint: str | None = Query(default=None),
            option_ce_ltp: float | None = Query(default=None),
            option_pe_ltp: float | None = Query(default=None),
            ce_premium_change: float | None = Query(default=None),
            pe_premium_change: float | None = Query(default=None),
            ce_spread_pct: float | None = Query(default=None),
            pe_spread_pct: float | None = Query(default=None),
            ce_depth: float | None = Query(default=None),
            pe_depth: float | None = Query(default=None),
            option_ltp_age_sec: float | None = Query(default=None),
            quote_source: str | None = Query(default=None),
            time_of_day: str | None = Query(default=None),
            minutes_since_open: int | None = Query(default=None),
            minutes_to_close: int | None = Query(default=None),
            expiry_context: str | None = Query(default=None),
        ):
            context = StrategyContext(
                symbol=symbol.upper(),
                ts_epoch=ts_epoch,
                spot_ltp=spot_ltp,
                vwap=vwap,
                day_high=day_high,
                day_low=day_low,
                orb_high=orb_high,
                orb_low=orb_low,
                prev_day_high=prev_day_high,
                prev_day_low=prev_day_low,
                atr=atr,
                atr_short=atr_short,
                atr_long=atr_long,
                range_width_pct=range_width_pct,
                volume_z=volume_z,
                volatility_state=volatility_state,
                regime_hint=regime_hint,
                option_ce_ltp=option_ce_ltp,
                option_pe_ltp=option_pe_ltp,
                ce_premium_change=ce_premium_change,
                pe_premium_change=pe_premium_change,
                ce_spread_pct=ce_spread_pct,
                pe_spread_pct=pe_spread_pct,
                ce_depth=ce_depth,
                pe_depth=pe_depth,
                option_ltp_age_sec=option_ltp_age_sec,
                quote_source=quote_source,
                time_of_day=time_of_day,
                minutes_since_open=minutes_since_open,
                minutes_to_close=minutes_to_close,
                expiry_context=expiry_context,
            )
            return build_movement_opportunity_api_payload(context)

    schema_route = f"{MOVEMENT_OPPORTUNITY_API_ROUTE}/schema"
    if not any(getattr(route, "path", None) == schema_route for route in app.routes):
        @app.get(schema_route)
        def movement_opportunity_schema():
            return movement_opportunity_schema_contract()


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
