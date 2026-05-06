import importlib

from fastapi.testclient import TestClient


server = importlib.import_module("api.server")
client = TestClient(server.app)


def test_openapi_declares_typed_runtime_endpoints():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    schemas = schema["components"]["schemas"]

    assert "HealthResponse" in schemas
    assert "RuntimeHealthResponse" in schemas
    assert "RuntimeSnapshotResponse" in schemas
    assert "OpportunityResponse" in schemas

    assert (
        schema["paths"]["/runtime/snapshot"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/RuntimeSnapshotResponse"
    )


def test_runtime_snapshot_response_model_filters_to_contract_fields(tmp_path, monkeypatch):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "engine_cycle_status.json").write_text(
        '{"cycle_stage":"scan_complete","market_mode":"paper","cycle_ok":true,"extra_internal":"hidden"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("CORE_BOT_RUNTIME_ROOT", str(tmp_path))

    response = client.get("/runtime/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert "extra_internal" not in payload
    assert set(payload).issuperset(
        {
            "runtime_root",
            "cycle_stage",
            "market_mode",
            "cycle_ok",
            "top_executable_count",
            "top_advisory_count",
        }
    )


def test_opportunity_response_schema_requires_candidate_id_bucket_source_and_raw():
    response = client.get("/openapi.json")

    schema = response.json()["components"]["schemas"]["OpportunityResponse"]
    required = set(schema["required"])

    assert {"candidate_id", "bucket", "source", "raw"}.issubset(required)
