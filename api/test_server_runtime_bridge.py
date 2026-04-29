import json
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


_SERVER_PATH = Path(__file__).resolve().with_name("server.py")
_SERVER_SPEC = importlib.util.spec_from_file_location("api_server_module", _SERVER_PATH)
assert _SERVER_SPEC and _SERVER_SPEC.loader
server = importlib.util.module_from_spec(_SERVER_SPEC)
_SERVER_SPEC.loader.exec_module(server)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_runtime_health_payload_reads_runtime_snapshot(tmp_path, monkeypatch):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "logs" / "runtime_health_latest.json",
        {
            "mode": "SIM",
            "market_open": False,
            "feed": {"blocked": False},
            "risk": {"halted": False},
            "execution": {"enabled": True},
            "ts_epoch": 123.0,
        },
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)

    payload = server._runtime_health_payload()

    assert payload["status"] == "ok"
    assert payload["mode"] == "SIM"
    assert payload["snapshot_ts_epoch"] == 123.0


def test_opportunities_payload_falls_back_to_suggestions_when_top_empty(tmp_path, monkeypatch):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "top_opportunities_latest.json",
        {
            "payload": {
                "top_executable_opportunities": [],
                "top_advisory_opportunities": [],
            }
        },
    )
    suggestions = runtime_root / "logs" / "suggestions.jsonl"
    suggestions.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "trade_id": "T-1",
        "symbol": "NIFTY",
        "strategy_family": "synthetic_advisory",
        "permission": "ADVISORY_ONLY",
        "final_action": "ADVISORY_ONLY",
        "final_score": 0.42,
    }
    suggestions.write_text(json.dumps(row) + "\n", encoding="utf-8")
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)

    rows = server._opportunities_payload(limit=5)

    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "T-1"
    assert rows[0]["symbol"] == "NIFTY"
    assert rows[0]["bucket"] == "suggestion"


def test_open_tradebot_pubsub_returns_degraded_error_on_connect_failure(monkeypatch):
    def _raise_connect_error():
        raise ConnectionError("redis down")

    monkeypatch.setattr(server, "_build_redis_client", _raise_connect_error)
    pubsub, error = server._open_tradebot_pubsub()

    assert pubsub is None
    assert isinstance(error, str)
    assert error.startswith("ConnectionError:")


def test_runtime_snapshot_event_shape(monkeypatch):
    snapshot = {"cycle_stage": "ok", "top_executable_count": 1}
    monkeypatch.setattr(server, "_runtime_snapshot_payload", lambda: snapshot)

    event = server._runtime_snapshot_event()

    assert event["type"] == "runtime_snapshot"
    assert event["payload"] == snapshot


def test_ws_emits_snapshot_even_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(server, "_open_tradebot_pubsub", lambda: (None, "ConnectionError:redis down"))
    monkeypatch.setattr(
        server,
        "_runtime_snapshot_payload",
        lambda: {"cycle_stage": "ok", "top_executable_count": 1},
    )
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        second = ws.receive_json()

    kinds = {first.get("type"), second.get("type")}
    assert "runtime_notice" in kinds
    assert "runtime_snapshot" in kinds
