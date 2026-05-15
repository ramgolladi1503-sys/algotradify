import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis
from redis.exceptions import RedisError

from api.schemas import (
    CandidateTruthRecordResponse,
    ExecutionReadinessResponse,
    HealthResponse,
    OpportunityLayerResponse,
    OpportunityResponse,
    RuntimeHealthResponse,
    RuntimePreflightResponse,
    RuntimeSnapshotResponse,
    StrategyCandidateDraftResponse,
    StrategyInfoResponse,
    TradeQualityResponse,
)
from candidate_truth import normalize_candidates
from execution_readiness import build_execution_readiness
from opportunity_layer import run_opportunity_pipeline
from runtime_contract import (
    candidate_runtime_roots,
    is_tradebot_compatible_root,
    run_preflight,
    runtime_artifact_root,
)
from strategies import StrategyContext, build_default_strategy_registry
from trade_quality import rank_trade_quality


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_tradebot_compatible_root(path: Path) -> bool:
    return is_tradebot_compatible_root(path)


def _candidate_tradebot_roots() -> list[Path]:
    return candidate_runtime_roots(base_repo_root=_repo_root())


def _tradebot_root() -> Path:
    for candidate in _candidate_tradebot_roots():
        if _is_tradebot_compatible_root(candidate):
            return candidate.expanduser().resolve()
    return (_repo_root() / "core_bot").resolve()


def _runtime_root() -> Path:
    return runtime_artifact_root(engine_root=_tradebot_root(), base_repo_root=_repo_root())


def _strategy_registry():
    return build_default_strategy_registry()


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _tail_jsonl(path: Path, limit: int = 100) -> list[dict]:
    if limit <= 0:
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    out: list[dict] = []
    for raw in lines[-limit:]:
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _query_feature_map(request: Request) -> dict[str, float | str]:
    features: dict[str, float | str] = {}
    for key, value in request.query_params.items():
        if key in {"symbol"}:
            continue
        try:
            features[key] = float(value)
        except (TypeError, ValueError):
            features[key] = value
    return features


def _strategy_draft_payload(request: Request, symbol: str) -> list[dict]:
    features = _query_feature_map(request)
    context = StrategyContext(symbol=symbol.upper(), features=features, raw={"source": "api_contract_preview"})
    return [draft.to_dict() for draft in _strategy_registry().generate_all(context)]


def _normalize_opportunity(row: dict, bucket: str, index: int) -> dict:
    symbol = row.get("symbol") or row.get("underlying") or row.get("index_symbol")
    strategy = row.get("strategy") or row.get("strategy_id") or row.get("strategy_family")
    setup_family = row.get("setup_family") or row.get("strategy_family") or row.get("setup") or strategy
    candidate_id = row.get("trade_id") or row.get("advisory_id") or row.get("candidate_id") or f"{bucket}_{index}"
    score = row.get("final_score")
    if score is None:
        score = row.get("rank_score")
    if score is None:
        score = row.get("score")
    return {
        "candidate_id": str(candidate_id),
        "symbol": symbol,
        "strategy": strategy,
        "strategy_id": strategy,
        "strategy_family": setup_family,
        "setup_family": setup_family,
        "permission": row.get("permission"),
        "final_action": row.get("final_action"),
        "status": row.get("status"),
        "execution_status": row.get("execution_status"),
        "confidence": row.get("confidence"),
        "score": score,
        "bucket": bucket,
        "source": row.get("source") or "runtime_snapshot",
        "raw": row,
    }


def _split_top_opportunities(top: dict) -> tuple[list, list]:
    if not isinstance(top, dict):
        return [], []
    payload = top.get("payload")
    if not isinstance(payload, dict):
        payload = top
    executable = payload.get("top_executable_opportunities") or payload.get("executable") or []
    advisory = payload.get("top_advisory_opportunities") or payload.get("advisory") or []
    return (
        executable if isinstance(executable, list) else [],
        advisory if isinstance(advisory, list) else [],
    )


def _runtime_health_payload() -> dict:
    root = _runtime_root()
    health_path_candidates = [
        root / "logs" / "runtime_health_latest.json",
        root / "runtime_health_latest.json",
    ]
    payload = {}
    for health_path in health_path_candidates:
        payload = _load_json(health_path, {})
        if isinstance(payload, dict) and payload:
            break

    base = {
        "runtime_root": str(root),
        "tradebot_root": str(_tradebot_root()),
    }
    if not isinstance(payload, dict) or not payload:
        return {
            **base,
            "status": "unknown",
            "reason": "runtime_health_unavailable",
        }
    feed = payload.get("feed")
    risk = payload.get("risk")
    execution = payload.get("execution")
    blocked = bool(feed and feed.get("blocked")) or bool(risk and risk.get("halted"))
    return {
        **base,
        "status": "blocked" if blocked else "ok",
        "mode": payload.get("mode"),
        "market_open": payload.get("market_open"),
        "feed": feed,
        "risk": risk,
        "execution": execution,
        "snapshot_ts_epoch": payload.get("snapshot_ts_epoch") or payload.get("ts_epoch"),
        "raw": payload,
    }


def _opportunities_payload(limit: int) -> list[dict]:
    root = _runtime_root()
    snap = _load_json(root / "top_opportunities_latest.json", {})
    if not snap:
        snap = _load_json(root / "logs" / "top_opportunities_latest.json", {})
    executable, advisory = _split_top_opportunities(snap)
    rows: list[dict] = []
    rows.extend(
        _normalize_opportunity(row, "executable", idx)
        for idx, row in enumerate(executable, start=1)
        if isinstance(row, dict)
    )
    rows.extend(
        _normalize_opportunity(row, "advisory", idx)
        for idx, row in enumerate(advisory, start=1)
        if isinstance(row, dict)
    )
    if rows:
        return rows[:limit]

    fallback_paths = [
        root / "logs" / "suggestions.jsonl",
        root / "suggestions.jsonl",
        root / "analytics" / "events" / "suggestions.jsonl",
    ]
    fallback_rows: list[dict] = []
    for path in fallback_paths:
        fallback_rows = _tail_jsonl(path, limit=max(limit, 100))
        if fallback_rows:
            break
    normalized = [
        _normalize_opportunity(row, "suggestion", idx)
        for idx, row in enumerate(reversed(fallback_rows), start=1)
    ]
    return normalized[:limit]


def _candidate_truth_payload(limit: int) -> list[dict]:
    rows = _opportunities_payload(limit)
    return [record.to_dict() for record in normalize_candidates(rows, source="api.opportunities")]


def _opportunity_layer_payload(limit: int) -> dict:
    rows = _opportunities_payload(limit)
    return run_opportunity_pipeline(rows, source="api.opportunities").to_dict()


def _runtime_records_from_files(root: Path, filenames: list[str], collection_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    for filename in filenames:
        for path in (root / filename, root / "logs" / filename):
            payload = _load_json(path, None)
            records = _extract_records(payload, collection_keys)
            if records:
                return records
    return []


def _extract_records(payload: Any, collection_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in collection_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    if any(key in payload for key in ("candidate_id", "symbol", "status", "readiness_status", "execution_allowed", "allowed")):
        return [payload]
    return []


def _index_by_keys(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in records:
        for key in _evidence_keys(row):
            index.setdefault(key, row)
    return index


def _evidence_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("candidate_id", "symbol", "tradingsymbol", "instrument_token"):
        value = row.get(field)
        if value not in (None, ""):
            keys.append(str(value).upper())
    instrument = row.get("instrument")
    if isinstance(instrument, dict):
        for field in ("tradingsymbol", "instrument_token", "symbol"):
            value = instrument.get(field)
            if value not in (None, ""):
                keys.append(str(value).upper())
    resolution = row.get("resolution")
    if isinstance(resolution, dict):
        instrument = resolution.get("instrument")
        if isinstance(instrument, dict):
            for field in ("tradingsymbol", "instrument_token", "symbol"):
                value = instrument.get(field)
                if value not in (None, ""):
                    keys.append(str(value).upper())
    return list(dict.fromkeys(keys))


def _runtime_evidence_indexes() -> dict[str, Any]:
    root = _runtime_root()
    broker_records = _runtime_records_from_files(
        root,
        [
            "broker_contract_readiness_latest.json",
            "contract_readiness_latest.json",
            "broker_readiness_latest.json",
        ],
        ("broker_contract_readiness", "contract_readiness", "records", "items"),
    )
    market_records = _runtime_records_from_files(
        root,
        [
            "market_readiness_latest.json",
            "quote_liquidity_latest.json",
            "quote_readiness_latest.json",
        ],
        ("market_readiness", "quote_liquidity", "records", "items"),
    )
    risk_records = _runtime_records_from_files(
        root,
        [
            "risk_readiness_latest.json",
            "risk_latest.json",
        ],
        ("risk_readiness", "risk", "records", "items"),
    )
    risk_global = risk_records[0] if len(risk_records) == 1 and not risk_records[0].get("candidate_id") else None
    return {
        "broker": _index_by_keys(broker_records),
        "market": _index_by_keys(market_records),
        "risk": _index_by_keys(risk_records),
        "risk_global": risk_global,
        "counts": {
            "broker_records": len(broker_records),
            "market_records": len(market_records),
            "risk_records": len(risk_records),
        },
    }


def _find_runtime_evidence(truth: dict[str, Any], opportunity: dict[str, Any] | None, indexes: dict[str, Any]) -> tuple[dict | None, dict | None, dict | None]:
    keys = _candidate_evidence_keys(truth, opportunity)
    broker = _first_index_hit(indexes["broker"], keys)
    market_keys = list(keys)
    if broker:
        market_keys.extend(_evidence_keys(broker))
    market = _first_index_hit(indexes["market"], market_keys)
    risk = _first_index_hit(indexes["risk"], keys) or indexes.get("risk_global")
    return broker, market, risk


def _candidate_evidence_keys(truth: dict[str, Any], opportunity: dict[str, Any] | None) -> list[str]:
    keys: list[str] = []
    for payload in (truth, opportunity or {}, truth.get("raw") if isinstance(truth.get("raw"), dict) else {}):
        for field in ("candidate_id", "symbol", "tradingsymbol", "instrument_token"):
            value = payload.get(field)
            if value not in (None, ""):
                keys.append(str(value).upper())
    normalized = truth.get("normalized")
    if isinstance(normalized, dict):
        for field in ("candidate_id", "symbol", "tradingsymbol", "instrument_token"):
            value = normalized.get(field)
            if value not in (None, ""):
                keys.append(str(value).upper())
    return list(dict.fromkeys(keys))


def _first_index_hit(index: dict[str, dict[str, Any]], keys: list[str]) -> dict[str, Any] | None:
    for key in keys:
        row = index.get(str(key).upper())
        if row is not None:
            return row
    return None


def _execution_readiness_payload(limit: int) -> list[dict]:
    rows = _opportunities_payload(limit)
    truth_records = [record.to_dict() for record in normalize_candidates(rows, source="api.opportunities")]
    opportunity_result = run_opportunity_pipeline(rows, source="api.opportunities").to_dict()
    opportunities_by_id = {
        row["candidate_id"]: row
        for section in ("ranked", "blocked", "dropped")
        for row in opportunity_result.get(section, [])
    }
    if opportunity_result.get("selected"):
        selected = opportunity_result["selected"]
        opportunities_by_id[selected["candidate_id"]] = selected

    evidence_indexes = _runtime_evidence_indexes()
    readiness: list[dict] = []
    for truth in truth_records:
        opportunity = opportunities_by_id.get(truth["candidate_id"])
        broker, market, risk = _find_runtime_evidence(truth, opportunity, evidence_indexes)
        record = build_execution_readiness(
            candidate_truth=truth,
            opportunity=opportunity,
            broker_contract=broker,
            market_readiness=market,
            risk=risk,
        ).to_dict()
        record["evidence"]["runtime_evidence_counts"] = evidence_indexes["counts"]
        readiness.append(record)
    return readiness


def _trade_quality_payload(limit: int) -> list[dict]:
    readiness = _execution_readiness_payload(limit)
    return [row.to_dict() for row in rank_trade_quality(readiness)]


def _strategy_execution_readiness_payload(request: Request, symbol: str) -> list[dict]:
    drafts = _strategy_draft_payload(request, symbol)
    truth_records = [record.to_dict() for record in normalize_candidates(drafts, source="api.strategy_draft_preview")]
    opportunity_result = run_opportunity_pipeline(drafts, source="api.strategy_draft_preview").to_dict()
    opportunities_by_id = {
        row["candidate_id"]: row
        for section in ("ranked", "blocked", "dropped")
        for row in opportunity_result.get(section, [])
    }
    if opportunity_result.get("selected"):
        selected = opportunity_result["selected"]
        opportunities_by_id[selected["candidate_id"]] = selected

    return [
        build_execution_readiness(
            candidate_truth=truth,
            opportunity=opportunities_by_id.get(truth["candidate_id"]),
            broker_contract=None,
            market_readiness=None,
            risk=None,
        ).to_dict()
        for truth in truth_records
    ]


def _runtime_snapshot_payload() -> dict:
    root = _runtime_root()
    cycle = _load_json(root / "logs" / "engine_cycle_status.json", {})
    if not cycle:
        cycle = _load_json(root / "engine_cycle_status.json", {})
    top = _load_json(root / "top_opportunities_latest.json", {})
    if not top:
        top = _load_json(root / "logs" / "top_opportunities_latest.json", {})
    executable, advisory = _split_top_opportunities(top)
    return {
        "runtime_root": str(root),
        "tradebot_root": str(_tradebot_root()),
        "cycle_stage": cycle.get("cycle_stage") if isinstance(cycle, dict) else None,
        "market_mode": cycle.get("market_mode") if isinstance(cycle, dict) else None,
        "cycle_ok": cycle.get("cycle_ok") if isinstance(cycle, dict) else None,
        "top_executable_count": len(executable),
        "top_advisory_count": len(advisory),
        "primary_blocker": cycle.get("primary_blocker") if isinstance(cycle, dict) else None,
        "reason": cycle.get("reason") if isinstance(cycle, dict) else None,
        "ts_epoch": cycle.get("ts_epoch") if isinstance(cycle, dict) else None,
    }


def _runtime_preflight_payload() -> dict:
    return run_preflight(base_repo_root=_repo_root())


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def _build_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
        health_check_interval=15,
    )


def _open_tradebot_pubsub():
    try:
        client = _build_redis_client()
        client.ping()
        pubsub = client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(os.getenv("TRADEBOT_REDIS_CHANNEL", "tradebot_events"))
        return pubsub, None
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}"


def _runtime_snapshot_event() -> dict:
    return {"type": "runtime_snapshot", "payload": _runtime_snapshot_payload()}


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@app.get("/runtime/health", response_model=RuntimeHealthResponse)
def runtime_health():
    return _runtime_health_payload()


@app.get("/runtime/preflight", response_model=RuntimePreflightResponse)
def runtime_preflight():
    return _runtime_preflight_payload()


@app.get("/runtime/snapshot", response_model=RuntimeSnapshotResponse)
def runtime_snapshot():
    return _runtime_snapshot_payload()


@app.get("/opportunities", response_model=list[OpportunityResponse])
def opportunities(limit: int = Query(default=25, ge=1, le=200)):
    return _opportunities_payload(limit=limit)


@app.get("/candidate-truth", response_model=list[CandidateTruthRecordResponse])
def candidate_truth(limit: int = Query(default=25, ge=1, le=200)):
    return _candidate_truth_payload(limit)


@app.get("/opportunity-layer", response_model=OpportunityLayerResponse)
def opportunity_layer(limit: int = Query(default=25, ge=1, le=200)):
    return _opportunity_layer_payload(limit)


@app.get("/execution-readiness", response_model=list[ExecutionReadinessResponse])
def execution_readiness(limit: int = Query(default=25, ge=1, le=200)):
    return _execution_readiness_payload(limit)


@app.get("/trade-quality", response_model=list[TradeQualityResponse])
def trade_quality(limit: int = Query(default=25, ge=1, le=200)):
    return _trade_quality_payload(limit)


@app.get("/strategies", response_model=list[StrategyInfoResponse])
def strategies():
    return _strategy_registry().list()


@app.get("/strategies/draft-candidates", response_model=list[StrategyCandidateDraftResponse])
def draft_candidates(request: Request, symbol: str = Query(..., min_length=1)):
    """Generate strategy candidate drafts from supplied score features.

    Query params other than `symbol` are treated as feature values. This is a
    contract preview endpoint for PR 3; real runtime strategy wiring belongs in
    later candidate truth/opportunity-layer PRs.
    """
    return _strategy_draft_payload(request, symbol)


@app.get("/strategies/draft-candidates/truth", response_model=list[CandidateTruthRecordResponse])
def draft_candidate_truth(request: Request, symbol: str = Query(..., min_length=1)):
    drafts = _strategy_draft_payload(request, symbol)
    return [record.to_dict() for record in normalize_candidates(drafts, source="api.strategy_draft_preview")]


@app.get("/strategies/draft-candidates/opportunity-layer", response_model=OpportunityLayerResponse)
def draft_candidate_opportunity_layer(request: Request, symbol: str = Query(..., min_length=1)):
    drafts = _strategy_draft_payload(request, symbol)
    return run_opportunity_pipeline(drafts, source="api.strategy_draft_preview").to_dict()


@app.get("/strategies/draft-candidates/execution-readiness", response_model=list[ExecutionReadinessResponse])
def draft_candidate_execution_readiness(request: Request, symbol: str = Query(..., min_length=1)):
    return _strategy_execution_readiness_payload(request, symbol)


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    pubsub, redis_boot_error = _open_tradebot_pubsub()
    last_snapshot = ""
    next_snapshot_at = 0.0
    redis_warning_sent = False

    try:
        while True:
            if pubsub is not None:
                try:
                    msg = pubsub.get_message(timeout=0.0)
                except RedisError as exc:
                    redis_boot_error = f"{type(exc).__name__}:{exc}"
                    try:
                        pubsub.close()
                    except Exception:
                        pass
                    pubsub = None
                    msg = None

                if msg and msg.get("type") == "message":
                    await ws.send_text(msg.get("data", ""))

            now = asyncio.get_running_loop().time()
            if redis_boot_error and not redis_warning_sent:
                warning = {
                    "type": "runtime_notice",
                    "payload": {
                        "source": "redis",
                        "status": "degraded",
                        "reason": redis_boot_error,
                    },
                }
                await ws.send_text(json.dumps(warning, separators=(",", ":")))
                redis_warning_sent = True

            if now >= next_snapshot_at:
                snapshot = _runtime_snapshot_event()
                encoded = json.dumps(snapshot, separators=(",", ":"))
                if encoded != last_snapshot:
                    await ws.send_text(encoded)
                    last_snapshot = encoded
                next_snapshot_at = now + 2.0

            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        if pubsub is not None:
            try:
                pubsub.unsubscribe(os.getenv("TRADEBOT_REDIS_CHANNEL", "tradebot_events"))
            except Exception:
                pass
            pubsub.close()
