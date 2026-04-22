from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

APP_TITLE = "AlgoTradify Backend Adapter"
TRADEBOT_ROOT = Path(os.getenv("TRADEBOT_ROOT", "core_bot")).resolve()
LOGS_DIR = TRADEBOT_ROOT / "logs"
RUNTIME_DIR = TRADEBOT_ROOT / "runtime"

app = FastAPI(title=APP_TITLE, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALGO_CORS_ORIGINS", "*").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _candidate_files(*names: str) -> list[Path]:
    out: list[Path] = []
    for name in names:
        out.append(RUNTIME_DIR / name)
        out.append(LOGS_DIR / name)
    return out


def _first_existing_json(*names: str, default: Any) -> Any:
    for path in _candidate_files(*names):
        if path.exists():
            return _read_json(path, default=default)
    return default


def _unwrap_payload(blob: Any) -> Any:
    if isinstance(blob, dict) and isinstance(blob.get("payload"), (dict, list)):
        return blob["payload"]
    return blob


def _safe_list(blob: Any) -> list[dict[str, Any]]:
    if isinstance(blob, list):
        return [row for row in blob if isinstance(row, dict)]
    return []


def _safe_dict(blob: Any) -> dict[str, Any]:
    return blob if isinstance(blob, dict) else {}


def _load_top_opportunities() -> dict[str, Any]:
    raw = _safe_dict(_unwrap_payload(_first_existing_json("top_opportunities_latest.json", default={})))
    rows: list[dict[str, Any]] = []
    for key in ("top_executable_opportunities", "top_advisory_opportunities", "rows", "items"):
        rows.extend(_safe_list(raw.get(key)))
    return {
        "generated_at": raw.get("generated_at") or _utc_now(),
        "items": rows,
        "count": len(rows),
    }


def _load_advisory() -> dict[str, Any]:
    raw = _safe_dict(_unwrap_payload(_first_existing_json("advisory_latest.json", default={})))
    rows = _safe_list(raw.get("rows") or raw.get("items") or raw.get("advisories"))
    return {
        "generated_at": raw.get("generated_at") or _utc_now(),
        "items": rows,
        "count": len(rows),
        "state": raw.get("state"),
    }


def _load_runtime_health() -> dict[str, Any]:
    raw = _safe_dict(_first_existing_json("runtime_health_latest.json", default={}))
    return {
        "generated_at": raw.get("generated_at") or _utc_now(),
        "market_open": raw.get("market_open"),
        "mode": raw.get("mode"),
        "feed": _safe_dict(raw.get("feed")),
        "risk": _safe_dict(raw.get("risk")),
        "execution": _safe_dict(raw.get("execution")),
        "ok": bool(raw),
    }


def _load_incidents() -> dict[str, Any]:
    raw = _first_existing_json("incidents_latest.json", "incident_log_latest.json", default=[])
    items = raw if isinstance(raw, list) else _safe_list(_safe_dict(raw).get("items"))
    return {"generated_at": _utc_now(), "items": items, "count": len(items)}


def _load_checks() -> dict[str, Any]:
    raw = _first_existing_json("verification_checks_latest.json", default=[])
    items = raw if isinstance(raw, list) else _safe_list(_safe_dict(raw).get("items"))
    return {"generated_at": _utc_now(), "items": items, "count": len(items)}


def _wrap(name: str, payload: Any) -> dict[str, Any]:
    return {"type": name, "generated_at": _utc_now(), "payload": payload}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": APP_TITLE,
        "tradebot_root": str(TRADEBOT_ROOT),
        "generated_at": _utc_now(),
    }


@app.get("/runtime/health")
def runtime_health() -> dict[str, Any]:
    return _wrap("runtime_health", _load_runtime_health())


@app.get("/runtime/risk")
def runtime_risk() -> dict[str, Any]:
    health_payload = _load_runtime_health()
    return _wrap("runtime_risk", health_payload.get("risk") or {})


@app.get("/runtime/execution")
def runtime_execution() -> dict[str, Any]:
    health_payload = _load_runtime_health()
    return _wrap("runtime_execution", health_payload.get("execution") or {})


@app.get("/opportunities")
def opportunities() -> dict[str, Any]:
    top = _load_top_opportunities()
    advisory = _load_advisory()
    merged = list(top.get("items", [])) + list(advisory.get("items", []))
    return _wrap(
        "opportunities",
        {
            "items": merged,
            "count": len(merged),
            "top": top,
            "advisory": advisory,
        },
    )


@app.get("/opportunities/{item_id}")
def opportunity_detail(item_id: str) -> dict[str, Any]:
    items = opportunities()["payload"]["items"]
    for item in items:
        current_id = item.get("trade_id") or item.get("trade_key") or item.get("id")
        if str(current_id) == item_id:
            return _wrap("opportunity_detail", item)
    return _wrap("opportunity_detail", {})


@app.get("/trades/{item_id}")
def trade_detail(item_id: str) -> dict[str, Any]:
    return _wrap("trade_detail", {"id": item_id})


@app.get("/incidents")
def incidents() -> dict[str, Any]:
    return _wrap("incidents", _load_incidents())


@app.get("/verification-checks")
def verification_checks() -> dict[str, Any]:
    return _wrap("verification_checks", _load_checks())


@app.get("/analytics/pnl-curve")
def analytics_pnl_curve() -> dict[str, Any]:
    return _wrap("analytics_pnl_curve", {"points": []})


@app.get("/analytics/candidate-volume")
def analytics_candidate_volume() -> dict[str, Any]:
    opps = _load_top_opportunities()
    return _wrap("analytics_candidate_volume", {"count": opps.get("count", 0)})


@app.get("/analytics/blocker-frequency")
def analytics_blocker_frequency() -> dict[str, Any]:
    return _wrap("analytics_blocker_frequency", {"items": []})


@app.get("/analytics/strategy-hit-rate")
def analytics_strategy_hit_rate() -> dict[str, Any]:
    return _wrap("analytics_strategy_hit_rate", {"items": []})


async def _stream(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = {
                "runtime_health": runtime_health()["payload"],
                "opportunities": opportunities()["payload"],
                "incidents": incidents()["payload"],
            }
            await ws.send_text(json.dumps(_wrap("dashboard", payload), default=str))
            await asyncio.sleep(float(os.getenv("ALGO_WS_REFRESH_SEC", "2.0") or "2.0"))
    except WebSocketDisconnect:
        return


@app.websocket("/ws")
async def ws_root(ws: WebSocket) -> None:
    await _stream(ws)
