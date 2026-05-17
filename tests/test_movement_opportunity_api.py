from __future__ import annotations

import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.movement_opportunity_route import (
    MOVEMENT_OPPORTUNITY_API_ROUTE,
    MOVEMENT_OPPORTUNITY_CONTEXT_REQUIRED_KEYS,
    MOVEMENT_OPPORTUNITY_EXCLUSION_REQUIRED_KEYS,
    MOVEMENT_OPPORTUNITY_PIPELINE_REQUIRED_KEYS,
    MOVEMENT_OPPORTUNITY_RANK_RECORD_REQUIRED_KEYS,
    MOVEMENT_OPPORTUNITY_RANK_RESULT_REQUIRED_KEYS,
    MOVEMENT_OPPORTUNITY_RANKED_CANDIDATE_REQUIRED_KEYS,
    MOVEMENT_OPPORTUNITY_REQUIRED_SAFE_FLAGS,
    MOVEMENT_OPPORTUNITY_RESPONSE_TOP_LEVEL_KEYS,
    MOVEMENT_OPPORTUNITY_SUMMARY_REQUIRED_KEYS,
    build_strategy_context_from_query,
    install_movement_opportunity_route,
    movement_opportunity_schema_contract,
)


def _query(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": "NIFTY",
        "ts_epoch": 77777.0,
        "spot_ltp": 101.4,
        "vwap": 101.0,
        "orb_high": 101.0,
        "orb_low": 99.5,
        "day_high": 101.2,
        "day_low": 99.0,
        "prev_day_high": 102.0,
        "prev_day_low": 98.0,
        "atr": 1.1,
        "atr_short": 0.7,
        "atr_long": 1.0,
        "range_width_pct": 0.35,
        "volume_z": 1.9,
        "volatility_state": "COMPRESSION",
        "regime_hint": "COMPRESSION",
        "option_ce_ltp": 125.0,
        "option_pe_ltp": 85.0,
        "ce_premium_change": 22.0,
        "pe_premium_change": -4.0,
        "ce_spread_pct": 0.8,
        "pe_spread_pct": 1.1,
        "ce_depth": 650.0,
        "pe_depth": 500.0,
        "option_ltp_age_sec": 1.0,
        "quote_source": "PRIMARY",
        "time_of_day": "OPEN",
        "minutes_since_open": 14,
    }
    payload.update(overrides)
    return payload


def _client() -> TestClient:
    app = FastAPI()
    install_movement_opportunity_route(app)
    return TestClient(app)


def _assert_keys(payload: dict[str, object], required_keys: tuple[str, ...] | list[str]) -> None:
    assert set(required_keys).issubset(payload.keys())


def _assert_flag(payload: dict[str, object], key: str, expected: object) -> None:
    assert payload[key] is expected


def _assert_item_flags(items: list[dict[str, object]], *, label: str) -> None:
    for item in items:
        assert item["is_order_action"] is False, label


def test_movement_opportunity_schema_contract_is_read_only():
    contract = movement_opportunity_schema_contract()

    assert contract["route"] == "/movement-opportunity"
    assert contract["method"] == "GET"
    assert contract["read_only"] is True
    assert contract["is_order_action"] is False
    assert contract["required_query_params"] == ["symbol", "ts_epoch"]
    assert contract["response_top_level_keys"] == list(MOVEMENT_OPPORTUNITY_RESPONSE_TOP_LEVEL_KEYS)
    assert "ranked_candidates" in contract["response_top_level_keys"]
    assert "pipeline" in contract["response_top_level_keys"]
    assert contract["required_safe_flags"] == MOVEMENT_OPPORTUNITY_REQUIRED_SAFE_FLAGS


def test_movement_opportunity_schema_contract_declares_nested_required_keys():
    contract = movement_opportunity_schema_contract()
    nested = contract["response_nested_required_keys"]

    assert nested["context"] == list(MOVEMENT_OPPORTUNITY_CONTEXT_REQUIRED_KEYS)
    assert nested["summary"] == list(MOVEMENT_OPPORTUNITY_SUMMARY_REQUIRED_KEYS)
    assert nested["ranked_candidates[]"] == list(MOVEMENT_OPPORTUNITY_RANKED_CANDIDATE_REQUIRED_KEYS)
    assert nested["rank_records[]"] == list(MOVEMENT_OPPORTUNITY_RANK_RECORD_REQUIRED_KEYS)
    assert nested["exclusions[]"] == list(MOVEMENT_OPPORTUNITY_EXCLUSION_REQUIRED_KEYS)
    assert nested["pipeline"] == list(MOVEMENT_OPPORTUNITY_PIPELINE_REQUIRED_KEYS)
    assert nested["pipeline.summary"] == list(MOVEMENT_OPPORTUNITY_SUMMARY_REQUIRED_KEYS)
    assert nested["pipeline.rank_result"] == list(MOVEMENT_OPPORTUNITY_RANK_RESULT_REQUIRED_KEYS)


def test_build_strategy_context_from_query_normalizes_symbol_and_fields():
    context = build_strategy_context_from_query(
        symbol="nifty",
        ts_epoch=123.0,
        query_params={
            "spot_ltp": "101.5",
            "minutes_since_open": "12",
            "regime_hint": "COMPRESSION",
        },
    )

    assert context.symbol == "NIFTY"
    assert context.ts_epoch == 123.0
    assert context.spot_ltp == 101.5
    assert context.minutes_since_open == 12
    assert context.regime_hint == "COMPRESSION"
    assert context.is_order_action is False


def test_movement_opportunity_endpoint_returns_read_only_pipeline_payload():
    response = _client().get(MOVEMENT_OPPORTUNITY_API_ROUTE, params=_query())

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_schema_version"] == "1.0"
    assert payload["route"] == "/movement-opportunity"
    assert payload["method"] == "GET"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["context"]["symbol"] == "NIFTY"
    assert payload["context"]["is_order_action"] is False
    assert payload["summary"]["provider_count"] == 6
    assert payload["summary"]["read_only"] is True
    assert payload["summary"]["is_order_action"] is False
    assert payload["pipeline"]["read_only"] is True
    assert payload["pipeline"]["is_order_action"] is False
    assert payload["pipeline"]["summary"] == payload["summary"]
    assert payload["ranked_candidates"] == payload["pipeline"]["rank_result"]["ranked_candidates"]
    assert payload["rank_records"] == payload["pipeline"]["rank_result"]["rank_records"]
    assert payload["exclusions"] == payload["pipeline"]["rank_result"]["exclusions"]


def test_movement_opportunity_response_top_level_keys_cannot_disappear():
    response = _client().get(MOVEMENT_OPPORTUNITY_API_ROUTE, params=_query())

    assert response.status_code == 200
    payload = response.json()
    assert tuple(payload.keys()) == MOVEMENT_OPPORTUNITY_RESPONSE_TOP_LEVEL_KEYS


def test_movement_opportunity_response_nested_schema_cannot_disappear():
    response = _client().get(MOVEMENT_OPPORTUNITY_API_ROUTE, params=_query())

    assert response.status_code == 200
    payload = response.json()
    _assert_keys(payload["context"], MOVEMENT_OPPORTUNITY_CONTEXT_REQUIRED_KEYS)
    _assert_keys(payload["summary"], MOVEMENT_OPPORTUNITY_SUMMARY_REQUIRED_KEYS)
    _assert_keys(payload["pipeline"], MOVEMENT_OPPORTUNITY_PIPELINE_REQUIRED_KEYS)
    _assert_keys(payload["pipeline"]["summary"], MOVEMENT_OPPORTUNITY_SUMMARY_REQUIRED_KEYS)
    _assert_keys(payload["pipeline"]["rank_result"], MOVEMENT_OPPORTUNITY_RANK_RESULT_REQUIRED_KEYS)

    assert payload["ranked_candidates"], "happy-path movement API should expose at least one ranked candidate"
    assert payload["rank_records"], "happy-path movement API should expose rank records"
    for candidate in payload["ranked_candidates"]:
        _assert_keys(candidate, MOVEMENT_OPPORTUNITY_RANKED_CANDIDATE_REQUIRED_KEYS)
    for record in payload["rank_records"]:
        _assert_keys(record, MOVEMENT_OPPORTUNITY_RANK_RECORD_REQUIRED_KEYS)


def test_movement_opportunity_response_safe_flags_are_locked_everywhere():
    response = _client().get(MOVEMENT_OPPORTUNITY_API_ROUTE, params=_query())

    assert response.status_code == 200
    payload = response.json()
    _assert_flag(payload, "read_only", True)
    _assert_flag(payload, "is_order_action", False)
    _assert_flag(payload["context"], "is_order_action", False)
    _assert_flag(payload["summary"], "read_only", True)
    _assert_flag(payload["summary"], "is_order_action", False)
    _assert_flag(payload["pipeline"], "read_only", True)
    _assert_flag(payload["pipeline"], "is_order_action", False)
    _assert_flag(payload["pipeline"]["summary"], "read_only", True)
    _assert_flag(payload["pipeline"]["summary"], "is_order_action", False)
    _assert_flag(payload["pipeline"]["rank_result"], "is_order_action", False)
    _assert_item_flags(payload["ranked_candidates"], label="ranked candidate became order action")
    _assert_item_flags(payload["rank_records"], label="rank record became order action")
    _assert_item_flags(payload["diagnostics"], label="diagnostic became order action")

    for candidate in payload["pipeline"]["option_enriched_candidates"]:
        assert candidate["is_order_action"] is False
    for candidate in payload["pipeline"]["no_trade_filter_result"]["candidates"]:
        assert candidate["is_order_action"] is False
    for result in payload["pipeline"]["no_trade_filter_result"]["results"]:
        assert result["is_order_action"] is False
    for diagnostic in payload["pipeline"]["diagnostics"]:
        assert diagnostic["is_order_action"] is False


def test_movement_opportunity_endpoint_blocks_fallback_quote_without_ranking():
    response = _client().get(MOVEMENT_OPPORTUNITY_API_ROUTE, params=_query(quote_source="FALLBACK"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["ranked_count"] == 0
    assert payload["ranked_candidates"] == []
    assert payload["summary"]["blocked_count"] == payload["summary"]["option_enriched_count"]
    assert payload["is_order_action"] is False


def test_movement_opportunity_exclusions_keep_schema_and_safe_flags_when_candidates_are_blocked():
    response = _client().get(MOVEMENT_OPPORTUNITY_API_ROUTE, params=_query(quote_source="FALLBACK"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["exclusions"], "blocked movement candidates should be surfaced as rank exclusions"
    for exclusion in payload["exclusions"]:
        _assert_keys(exclusion, MOVEMENT_OPPORTUNITY_EXCLUSION_REQUIRED_KEYS)
        assert exclusion["is_order_action"] is False
    assert payload["exclusions"] == payload["pipeline"]["rank_result"]["exclusions"]


def test_movement_opportunity_endpoint_requires_symbol_and_timestamp():
    response = _client().get(MOVEMENT_OPPORTUNITY_API_ROUTE, params={"symbol": "NIFTY"})

    assert response.status_code == 422


def test_movement_opportunity_schema_endpoint_is_mounted_once():
    app = FastAPI()
    install_movement_opportunity_route(app)
    install_movement_opportunity_route(app)
    client = TestClient(app)

    route_paths = [getattr(route, "path", None) for route in app.routes]
    assert route_paths.count("/movement-opportunity") == 1
    assert route_paths.count("/movement-opportunity/schema") == 1

    response = client.get("/movement-opportunity/schema")
    assert response.status_code == 200
    assert response.json()["is_order_action"] is False


def test_movement_opportunity_openapi_contract_exposes_only_read_only_get_routes():
    app = FastAPI()
    install_movement_opportunity_route(app)
    openapi = app.openapi()

    assert set(openapi["paths"][MOVEMENT_OPPORTUNITY_API_ROUTE].keys()) == {"get"}
    assert set(openapi["paths"][f"{MOVEMENT_OPPORTUNITY_API_ROUTE}/schema"].keys()) == {"get"}
    operation = openapi["paths"][MOVEMENT_OPPORTUNITY_API_ROUTE]["get"]
    required_params = {
        param["name"]
        for param in operation["parameters"]
        if param.get("required") is True
    }
    assert required_params == {"symbol", "ts_epoch"}
    assert "post" not in openapi["paths"][MOVEMENT_OPPORTUNITY_API_ROUTE]
    assert "put" not in openapi["paths"][MOVEMENT_OPPORTUNITY_API_ROUTE]
    assert "delete" not in openapi["paths"][MOVEMENT_OPPORTUNITY_API_ROUTE]


def test_server_with_movement_mounts_read_only_endpoint():
    server_with_movement = importlib.import_module("api.server_with_movement")
    client = TestClient(server_with_movement.app)

    response = client.get(MOVEMENT_OPPORTUNITY_API_ROUTE, params=_query())

    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["summary"]["provider_count"] == 6
