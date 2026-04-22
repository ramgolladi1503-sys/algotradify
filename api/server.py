from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .paper_engine import (
    run_paper_cycle,
    get_positions,
    get_trade_history,
    get_pnl_summary,
    get_trade_diagnostics,
    get_learning,
    load_adaptive_params,
    get_rejections,
)

APP_TITLE = "AlgoTradify Backend Adapter"
TRADEBOT_ROOT = Path(os.getenv("TRADEBOT_ROOT", "core_bot")).resolve()
LOGS_DIR = TRADEBOT_ROOT / "logs"
RUNTIME_DIR = TRADEBOT_ROOT / "runtime"
ACTION_QUEUE_PATH = RUNTIME_DIR / "ui_action_queue.jsonl"
ACTION_HISTORY_PATH = RUNTIME_DIR / "ui_action_history.json"

app = FastAPI(title=APP_TITLE, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALGO_CORS_ORIGINS", "*").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ActionRequest(BaseModel):
    action: Literal["ENTER", "SKIP", "FORCE"]
    trade_id: str | None = None
    trade_key: str | None = None
    symbol: str | None = None
    reason: str | None = None
    payload: dict[str, Any] | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


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


def _load_action_history() -> list[dict[str, Any]]:
    data = _read_json(ACTION_HISTORY_PATH, default=[])
    return data if isinstance(data, list) else []


def _record_action(request: ActionRequest) -> dict[str, Any]:
    if not any([request.trade_id, request.trade_key, request.symbol]):
        raise HTTPException(status_code=400, detail="trade_id, trade_key, or symbol is required")
    item = {
        "timestamp": _utc_now(),
        "action": request.action,
        "trade_id": request.trade_id,
        "trade_key": request.trade_key,
        "symbol": request.symbol,
        "reason": request.reason,
        "payload": request.payload or {},
        "status": "queued",
        "source": "algotradify_ui",
    }
    _append_jsonl(ACTION_QUEUE_PATH, item)
    history = _load_action_history()
    history.insert(0, item)
    _write_json(ACTION_HISTORY_PATH, history[:200])
    return item


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
    run_paper_cycle()
    return _wrap("runtime_health", _load_runtime_health())


@app.get("/paper/positions")
def paper_positions() -> dict[str, Any]:
    run_paper_cycle()
    return _wrap("paper_positions", {"items": get_positions()})


@app.get("/paper/trades")
def paper_trades() -> dict[str, Any]:
    run_paper_cycle()
    return _wrap("paper_trades", {"items": get_trade_history()})


@app.get("/paper/pnl")
def paper_pnl() -> dict[str, Any]:
    run_paper_cycle()
    return _wrap("paper_pnl", get_pnl_summary())


@app.get("/paper/diagnostics")
def paper_diagnostics() -> dict[str, Any]:
    run_paper_cycle()
    return _wrap("paper_diagnostics", get_trade_diagnostics())


@app.get("/paper/learning")
def paper_learning() -> dict[str, Any]:
    run_paper_cycle()
    return _wrap("paper_learning", get_learning())


@app.get("/paper/params")
def paper_params() -> dict[str, Any]:
    run_paper_cycle()
    return _wrap("paper_params", load_adaptive_params())


@app.get("/paper/rejections")
def paper_rejections() -> dict[str, Any]:
    run_paper_cycle()
    return _wrap("paper_rejections", {"items": get_rejections()})


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


@app.get("/actions/history")
def action_history() -> dict[str, Any]:
    return _wrap("action_history", {"items": _load_action_history()})


@app.post("/actions/execute")
def action_execute(request: ActionRequest) -> dict[str, Any]:
    if request.action != "ENTER":
        raise HTTPException(status_code=400, detail="execute endpoint only accepts ENTER")
    return _wrap("action_execute", _record_action(request))


@app.post("/actions/skip")
def action_skip(request: ActionRequest) -> dict[str, Any]:
    if request.action != "SKIP":
        raise HTTPException(status_code=400, detail="skip endpoint only accepts SKIP")
    return _wrap("action_skip", _record_action(request))


@app.post("/actions/force")
def action_force(request: ActionRequest) -> dict[str, Any]:
    if request.action != "FORCE":
        raise HTTPException(status_code=400, detail="force endpoint only accepts FORCE")
    return _wrap("action_force", _record_action(request))


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
            cycle = run_paper_cycle()
            payload = {
                "runtime_health": runtime_health()["payload"],
                "opportunities": opportunities()["payload"],
                "incidents": incidents()["payload"],
                "paper_positions": {"items": get_positions()},
                "paper_pnl": get_pnl_summary(),
                "paper_learning": get_learning(),
                "paper_params": load_adaptive_params(),
                "paper_diagnostics": get_trade_diagnostics(),
                "paper_rejections": {"items": get_rejections()},
                "paper_cycle": cycle,
            }
            await ws.send_text(json.dumps(_wrap("dashboard", payload), default=str))
            await asyncio.sleep(float(os.getenv("ALGO_WS_REFRESH_SEC", "2.0") or "2.0"))
    except WebSocketDisconnect:
        return


@app.websocket("/ws")
async def ws_root(ws: WebSocket) -> None:
    await _stream(ws)
