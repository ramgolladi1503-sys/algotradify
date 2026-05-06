import importlib
import json

from fastapi.testclient import TestClient


server = importlib.import_module("api.server")
client = TestClient(server.app)


def test_websocket_sends_degraded_redis_notice_when_redis_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        server,
        "_open_tradebot_pubsub",
        lambda: (None, "ConnectionError:redis unavailable"),
    )

    with client.websocket_connect("/ws") as websocket:
        raw = websocket.receive_text()

    payload = json.loads(raw)
    assert payload["type"] == "runtime_notice"
    assert payload["payload"]["source"] == "redis"
    assert payload["payload"]["status"] == "degraded"
    assert "redis unavailable" in payload["payload"]["reason"]


def test_websocket_sends_runtime_snapshot_event(monkeypatch):
    monkeypatch.setattr(server, "_open_tradebot_pubsub", lambda: (None, None))
    monkeypatch.setattr(
        server,
        "_runtime_snapshot_payload",
        lambda: {
            "runtime_root": "/tmp/runtime",
            "cycle_stage": "scan_complete",
            "market_mode": "paper",
            "cycle_ok": True,
            "top_executable_count": 1,
            "top_advisory_count": 0,
            "primary_blocker": None,
            "reason": "ok",
            "ts_epoch": 12345,
        },
    )

    with client.websocket_connect("/ws") as websocket:
        raw = websocket.receive_text()

    payload = json.loads(raw)
    assert payload["type"] == "runtime_snapshot"
    assert payload["payload"]["cycle_stage"] == "scan_complete"
    assert payload["payload"]["cycle_ok"] is True
    assert payload["payload"]["top_executable_count"] == 1


def test_runtime_snapshot_event_contract_is_stable(monkeypatch):
    monkeypatch.setattr(
        server,
        "_runtime_snapshot_payload",
        lambda: {"cycle_stage": "idle", "cycle_ok": False},
    )

    event = server._runtime_snapshot_event()

    assert event == {
        "type": "runtime_snapshot",
        "payload": {"cycle_stage": "idle", "cycle_ok": False},
    }
