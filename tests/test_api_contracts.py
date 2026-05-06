import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient


server = importlib.import_module("api.server")
client = TestClient(server.app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_health_degrades_safely_when_health_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CORE_BOT_RUNTIME_ROOT", str(tmp_path))

    response = client.get("/runtime/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unknown"
    assert payload["reason"] == "runtime_health_unavailable"
    assert payload["runtime_root"] == str(tmp_path.resolve())


def test_runtime_snapshot_reads_cycle_status(tmp_path, monkeypatch):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "engine_cycle_status.json").write_text(
        json.dumps(
            {
                "cycle_stage": "scan_complete",
                "market_mode": "paper",
                "cycle_ok": True,
                "primary_blocker": None,
                "reason": "ok",
                "ts_epoch": 12345,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "top_opportunities_latest.json").write_text(
        json.dumps(
            {
                "payload": {
                    "top_executable_opportunities": [{"symbol": "NIFTY"}],
                    "top_advisory_opportunities": [{"symbol": "BANKNIFTY"}],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CORE_BOT_RUNTIME_ROOT", str(tmp_path))

    response = client.get("/runtime/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_root"] == str(tmp_path.resolve())
    assert payload["cycle_stage"] == "scan_complete"
    assert payload["market_mode"] == "paper"
    assert payload["cycle_ok"] is True
    assert payload["top_executable_count"] == 1
    assert payload["top_advisory_count"] == 1
    assert payload["ts_epoch"] == 12345


def test_opportunities_normalizes_executable_and_advisory_rows(tmp_path, monkeypatch):
    (tmp_path / "top_opportunities_latest.json").write_text(
        json.dumps(
            {
                "payload": {
                    "top_executable_opportunities": [
                        {
                            "trade_id": "T1",
                            "symbol": "NIFTY",
                            "strategy": "breakout",
                            "final_score": 91.5,
                            "execution_status": "EXECUTABLE",
                        }
                    ],
                    "top_advisory_opportunities": [
                        {
                            "advisory_id": "A1",
                            "underlying": "BANKNIFTY",
                            "strategy_family": "mean_reversion",
                            "rank_score": 77,
                            "status": "ADVISORY_ONLY",
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CORE_BOT_RUNTIME_ROOT", str(tmp_path))

    response = client.get("/opportunities?limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["candidate_id"] == "T1"
    assert payload[0]["bucket"] == "executable"
    assert payload[0]["symbol"] == "NIFTY"
    assert payload[0]["score"] == 91.5
    assert payload[1]["candidate_id"] == "A1"
    assert payload[1]["bucket"] == "advisory"
    assert payload[1]["symbol"] == "BANKNIFTY"
    assert payload[1]["score"] == 77


def test_opportunities_falls_back_to_suggestions_jsonl(tmp_path, monkeypatch):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "suggestions.jsonl").write_text(
        "not-json\n"
        + json.dumps({"trade_id": "OLD", "symbol": "NIFTY", "final_score": 10})
        + "\n"
        + json.dumps({"trade_id": "NEW", "symbol": "SENSEX", "final_score": 20})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CORE_BOT_RUNTIME_ROOT", str(tmp_path))

    response = client.get("/opportunities?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["candidate_id"] == "NEW"
    assert payload[0]["bucket"] == "suggestion"
    assert payload[0]["score"] == 20
