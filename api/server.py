import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis
from redis.exceptions import RedisError


def _runtime_root() -> Path:
    configured = str(os.getenv("CORE_BOT_RUNTIME_ROOT", "")).strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(__file__).resolve().parents[1] / "core_bot" / ".runtime").resolve()


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


def _normalize_opportunity(row: dict, bucket: str, index: int) -> dict:
    symbol = row.get("symbol") or row.get("underlying") or row.get("index_symbol")
    strategy = row.get("strategy") or row.get("strategy_family")
    candidate_id = row.get("trade_id") or row.get("advisory_id") or f"{bucket}_{index}"
    score = row.get("final_score")
    if score is None:
        score = row.get("rank_score")
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "strategy": strategy,
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


def _runtime_health_payload() -> dict:
    root = _runtime_root()
    health_path = root / "logs" / "runtime_health_latest.json"
    payload = _load_json(health_path, {})
    if not isinstance(payload, dict) or not payload:
        return {
            "status": "unknown",
            "reason": "runtime_health_unavailable",
            "runtime_root": str(root),
        }
    feed = payload.get("feed")
    risk = payload.get("risk")
    execution = payload.get("execution")
    blocked = bool(feed and feed.get("blocked")) or bool(risk and risk.get("halted"))
    return {
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
    if isinstance(snap, dict):
        payload = snap.get("payload") or {}
        if isinstance(payload, dict):
            executable = payload.get("top_executable_opportunities")
            advisory = payload.get("top_advisory_opportunities")
            rows: list[dict] = []
            if isinstance(executable, list):
                rows.extend(
                    _normalize_opportunity(row, "executable", idx)
                    for idx, row in enumerate(executable, start=1)
                    if isinstance(row, dict)
                )
            if isinstance(advisory, list):
                rows.extend(
                    _normalize_opportunity(row, "advisory", idx)
                    for idx, row in enumerate(advisory, start=1)
                    if isinstance(row, dict)
                )
            if rows:
                return rows[:limit]

    fallback_rows = _tail_jsonl(root / "logs" / "suggestions.jsonl", limit=max(limit, 100))
    normalized = [
        _normalize_opportunity(row, "suggestion", idx)
        for idx, row in enumerate(reversed(fallback_rows), start=1)
    ]
    return normalized[:limit]


def _runtime_snapshot_payload() -> dict:
    root = _runtime_root()
    cycle = _load_json(root / "logs" / "engine_cycle_status.json", {})
    top = _load_json(root / "top_opportunities_latest.json", {})
    top_payload = top.get("payload") if isinstance(top, dict) else {}
    executable = top_payload.get("top_executable_opportunities") if isinstance(top_payload, dict) else []
    advisory = top_payload.get("top_advisory_opportunities") if isinstance(top_payload, dict) else []
    return {
        "runtime_root": str(root),
        "cycle_stage": cycle.get("cycle_stage") if isinstance(cycle, dict) else None,
        "market_mode": cycle.get("market_mode") if isinstance(cycle, dict) else None,
        "cycle_ok": cycle.get("cycle_ok") if isinstance(cycle, dict) else None,
        "top_executable_count": len(executable) if isinstance(executable, list) else 0,
        "top_advisory_count": len(advisory) if isinstance(advisory, list) else 0,
        "primary_blocker": cycle.get("primary_blocker") if isinstance(cycle, dict) else None,
        "reason": cycle.get("reason") if isinstance(cycle, dict) else None,
        "ts_epoch": cycle.get("ts_epoch") if isinstance(cycle, dict) else None,
    }


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def _build_redis_client():
    # Keep Redis polling non-blocking for the websocket pipeline.
    return redis.Redis(
        host="localhost",
        port=6379,
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
        pubsub.subscribe("tradebot_events")
        return pubsub, None
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}"


def _runtime_snapshot_event() -> dict:
    return {"type": "runtime_snapshot", "payload": _runtime_snapshot_payload()}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/runtime/health")
def runtime_health():
    return _runtime_health_payload()


@app.get("/runtime/snapshot")
def runtime_snapshot():
    return _runtime_snapshot_payload()


@app.get("/opportunities")
def opportunities(limit: int = Query(default=25, ge=1, le=200)):
    return _opportunities_payload(limit=limit)


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
                pubsub.unsubscribe("tradebot_events")
            except Exception:
                pass
            pubsub.close()
