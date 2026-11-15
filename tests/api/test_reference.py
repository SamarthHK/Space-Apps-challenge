"""Real saved-model HTTP checks; no mocked providers or manufactured crop examples."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
import pytest
import requests

from agri_data.api.app import create_app
from agri_data.api.config import ReferenceSettings, Settings
from agri_data.contracts.india_inference import predict_reference


ORIGIN = {"Origin": "http://localhost:1080"}


@pytest.fixture(scope="module")
def artifact():
    supplied = os.environ.get("AGRI_INDIA_MODELS")
    assert supplied, "Set AGRI_INDIA_MODELS to the actual saved Indian reference model"
    path = Path(supplied).resolve()
    manifest = json.loads((path / "manifest.json").read_bytes())
    example = json.loads((path / "example_request.json").read_bytes())
    return path, manifest, {**example, "model_id": manifest["model_id"]}


def app_for(path=None, model_id=None):
    api = Settings.from_env({"AGRI_ALLOWED_ORIGINS": ORIGIN["Origin"]})
    reference = ReferenceSettings.from_env({
        "AGRI_REFERENCE_MODEL_DIR": str(path), "AGRI_REFERENCE_MODEL_ID": model_id,
    }) if path is not None else None
    return create_app(api, reference_settings=reference)


@pytest.fixture(scope="module")
def client(artifact):
    path, manifest, _ = artifact
    with TestClient(app_for(path, manifest["model_id"]), base_url="http://localhost") as client:
        yield client


def test_reference_configuration_is_explicit_and_does_not_load_weights():
    assert ReferenceSettings.from_env({}) is None
    for values in ({"AGRI_REFERENCE_MODEL_DIR": "data"},
                   {"AGRI_REFERENCE_MODEL_ID": "not-a-model"},
                   {"AGRI_REFERENCE_MODEL_DIR": "https://example.com/model", "AGRI_REFERENCE_MODEL_ID": "0" * 64}):
        with pytest.raises(ValueError):
            ReferenceSettings.from_env(values)
    script = """
import sys
from agri_data.api.app import create_app
from agri_data.api.config import Settings
app=create_app(Settings.from_env({'AGRI_ALLOWED_ORIGINS':'http://localhost:1080'}))
assert '/api/v1/reference-model/predictions' in app.openapi()['paths']
assert not {'torch', 'catboost', 'agri_data.contracts.india_inference'} & set(sys.modules)
"""
    process = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr


def test_actual_metadata_and_capability_do_not_claim_field_recommendations(client, artifact):
    path, manifest, original = artifact
    response = client.get("/api/v1/reference-model", headers={"X-Request-ID": "reference-audit"})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["model_id"] == manifest["model_id"] and data["method"] == manifest["champion"]
    assert data["example_request"]["context_id"] == original["context_id"]
    assert {crop["crop_id"] for crop in data["crops"]} == {
        pair[0] for pair in json.loads((path / "mlp.state.json").read_bytes())["crop_system_support"]}
    assert data["context_count"] == 1318
    assert not data["operational_recommendation_ready"] and not data["rotation_effects_supported"]
    assert str(path) not in response.text and "process_rss" not in response.text and "raw_path" not in response.text
    assert response.json()["meta"]["request_id"] == response.headers["X-Request-ID"] == "reference-audit"
    capabilities = {row["capability_id"]: row for row in client.get("/api/v1/workspace").json()["data"]["capabilities"]}
    assert capabilities["reference_suitability"]["state"] == "ready"
    assert all(capabilities[name]["state"] == "not_implemented" for name in ("recommendations", "crops", "markets"))


def test_http_scores_equal_actual_cli_and_validate_against_openapi(client, artifact):
    path, _, request = artifact
    response = client.post("/api/v1/reference-model/predictions", json=request, headers=ORIGIN)
    assert response.status_code == 200, response.text
    expected = predict_reference(path, {key: value for key, value in request.items() if key != "model_id"})
    assert response.json()["data"] == expected
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN["Origin"]
    assert response.headers["Cache-Control"] == "no-store"
    assert "Location" not in response.headers and "job_id" not in response.text
    schema = client.get("/api/v1/openapi.json").json()
    for route, name in (("/api/v1/reference-model", "ReferenceModelResponse"),
                        ("/api/v1/reference-model/predictions", "ReferencePredictionResponse")):
        body = client.get(route).json() if route.endswith("reference-model") else response.json()
        Draft202012Validator({"components": schema["components"], "$ref": f"#/components/schemas/{name}"},
                            format_checker=FormatChecker()).validate(body)


def test_reference_context_pages_are_bound_to_real_model_periods_and_filters(client, artifact):
    _, manifest, _ = artifact
    url = "/api/v1/reference-model/contexts"
    query = {"model_id": manifest["model_id"], "period_id": "HP8100", "limit": 2}
    first = client.get(url, params=query)
    assert first.status_code == 200, first.text
    page = first.json()
    assert len(page["data"]) == 2 and all(row["analysis_end"] == "2000-12-31" for row in page["data"])
    cursor = page["meta"]["next_cursor"]
    second = client.get(url, params={**query, "cursor": cursor}).json()
    assert not {row["context_id"] for row in page["data"]} & {row["context_id"] for row in second["data"]}
    assert client.get(url, params={**query, "cursor": cursor + "x"}).status_code == 400
    assert client.get(url, params={**query, "cursor": cursor, "period_id": "HP0120"}).status_code == 400
    assert client.get(url, params={**query, "model_id": manifest["dataset_id"]}).status_code == 409
    assert client.get(url, params={**query, "period_id": "2026-season"}).status_code == 422
    assert client.get(url, params={**query, "limit": 201}).status_code == 422


def test_unsupported_dates_tasks_inputs_and_stale_models_never_return_scores(client, artifact):
    _, manifest, original = artifact
    url = "/api/v1/reference-model/predictions"
    cases = [
        ({"analysis_start": original["analysis_end"]}, 422, "reference_interval_mismatch"),
        ({"context_id": manifest["model_id"]}, 404, "reference_context_not_found"),
        ({"model_id": manifest["dataset_id"]}, 409, "reference_model_changed"),
        ({"mode": "strict_as_of_recommendation"}, 422, "validation_error"),
        ({"task": "field_rotation_outcomes"}, 422, "validation_error"),
        ({"latitude": 12.0}, 422, "validation_error"),
        ({"crop_ids": original["crop_ids"] * 34}, 422, "validation_error"),
        ({"crop_ids": [original["crop_ids"][0]] * 2}, 422, "validation_error"),
    ]
    for changes, status, code in cases:
        response = client.post(url, json={**original, **changes}, headers=ORIGIN)
        assert response.status_code == status, response.text
        assert response.json()["error"]["code"] == code and "data" not in response.json()
    assert client.post(url, json=original).status_code == 403
    assert client.post(url, json=original, headers={"Origin": "https://example.com"}).status_code == 403
    assert client.post(url, json=original, headers=ORIGIN).status_code == 200


def test_actual_untrained_crop_and_farmer_exclusions_abstain_without_fallback(client, artifact):
    _, _, original = artifact
    request = deepcopy(original)
    request["crop_ids"] = ["ecocrop:1112"]
    response = client.post("/api/v1/reference-model/predictions", json=request, headers=ORIGIN)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "abstained" and not result["ranked"]
    assert result["withheld"] == [{"crop_id": "ecocrop:1112", "reason": "no_target_bearing_training_support",
                                  "relative_preference": 0.0}]
    request = {**original, "excluded_crop_ids": original["crop_ids"]}
    result = client.post("/api/v1/reference-model/predictions", json=request, headers=ORIGIN).json()["data"]
    assert result["status"] == "abstained" and all(row["relative_preference"] == 0 for row in result["withheld"])


def test_busy_model_requests_fail_fast_and_a_finished_request_releases_the_model(client, artifact):
    _, _, request = artifact
    with client.app.state.reference_store.access():
        response = client.post("/api/v1/reference-model/predictions", json=request, headers=ORIGIN)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "reference_model_busy"
        assert response.json()["error"]["retryable"] is True
    assert client.post("/api/v1/reference-model/predictions", json=request, headers=ORIGIN).status_code == 200


def test_unconfigured_missing_and_misbound_models_are_redacted_without_breaking_health(artifact, tmp_path):
    path, manifest, request = artifact
    for app, code in (
        (app_for(), "reference_model_unconfigured"),
        (app_for(tmp_path / "missing-private-path", manifest["model_id"]), "reference_model_unavailable"),
        (app_for(path, manifest["dataset_id"]), "reference_model_unavailable"),
    ):
        with TestClient(app, base_url="http://localhost") as client:
            assert client.get("/api/v1/health").status_code == 200
            response = client.get("/api/v1/reference-model")
            assert response.status_code == 503 and response.json()["error"]["code"] == code
            assert "private-path" not in response.text and str(path) not in response.text
            capabilities = client.get("/api/v1/workspace").json()["data"]["capabilities"]
            assert next(row for row in capabilities if row["capability_id"] == "reference_suitability")["state"] == "blocked"


def test_changed_real_checkpoint_disables_cached_predictions_until_restart(artifact, tmp_path):
    path, manifest, request = artifact
    copy = tmp_path / "immutable-model-copy"
    shutil.copytree(path, copy)
    weights = copy / "mlp.pt"
    original = weights.read_bytes()
    with TestClient(app_for(copy, manifest["model_id"]), base_url="http://localhost") as client:
        assert client.get("/api/v1/reference-model").status_code == 200
        weights.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        response = client.post("/api/v1/reference-model/predictions", json=request, headers=ORIGIN)
        assert response.status_code == 503 and response.json()["error"]["code"] == "reference_model_unavailable"
        assert str(copy) not in response.text
        weights.write_bytes(original)
        assert client.get("/api/v1/reference-model").status_code == 503
    with TestClient(app_for(copy, manifest["model_id"]), base_url="http://localhost") as restarted:
        assert restarted.post("/api/v1/reference-model/predictions", json=request, headers=ORIGIN).status_code == 200


def test_real_loopback_server_loads_operator_configuration_and_serves_saved_predictions(artifact, tmp_path):
    path, manifest, request = artifact
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("AGRI_API_", "AGRI_REFERENCE_", "AGRI_WORKSPACE_"))}
    environment.update(AGRI_API_HOST="127.0.0.1", AGRI_API_PORT=str(port),
                       AGRI_ALLOWED_ORIGINS=ORIGIN["Origin"], AGRI_REFERENCE_MODEL_DIR=str(path),
                       AGRI_REFERENCE_MODEL_ID=manifest["model_id"])
    root = f"http://127.0.0.1:{port}/api/v1"
    log_path = tmp_path / "reference-http.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "agri_data.api"], env=environment,
                                   stdout=log, stderr=log)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    pytest.fail("Reference API exited before readiness: " + log_path.read_text(encoding="utf-8"))
                try:
                    if requests.get(root + "/health", timeout=0.2).status_code == 200:
                        break
                except requests.ConnectionError:
                    pass
                time.sleep(0.05)
            else:
                pytest.fail("Reference API did not become responsive")
            metadata = requests.get(root + "/reference-model", timeout=30)
            assert metadata.status_code == 200, metadata.text
            assert metadata.json()["data"]["model_id"] == manifest["model_id"]
            data = metadata.json()["data"]
            checks = []
            for period in data["periods"]:
                page = requests.get(root + "/reference-model/contexts", params={
                    "model_id": data["model_id"], "period_id": period["period_id"], "limit": 1,
                }, timeout=15)
                assert page.status_code == 200, page.text
                context = page.json()["data"][0]
                systems = sorted({system for crop in data["crops"] for system in crop["production_systems"]})
                for system in systems:
                    selected = {**request, "context_id": context["context_id"],
                                "analysis_start": context["analysis_start"], "analysis_end": context["analysis_end"],
                                "production_system": system,
                                "crop_ids": [crop["crop_id"] for crop in data["crops"] if system in crop["production_systems"]]}
                    response = requests.post(root + "/reference-model/predictions", json=selected,
                                             headers=ORIGIN, timeout=15)
                    assert response.status_code == 200, response.text
                    expected = predict_reference(path, {key: value for key, value in selected.items() if key != "model_id"})
                    assert response.json()["data"] == expected
                    assert sum(row["relative_preference"] for row in expected["ranked"]) == pytest.approx(1)
                    checks.append({"period_id": period["period_id"], "production_system": system,
                                   "context_id": context["context_id"], "candidates": len(expected["ranked"]),
                                   "http_status": response.status_code, "cli_parity": "exact"})
            assert requests.get(root + "/health", timeout=2).status_code == 200
            proof = os.environ.get("AGRI_REFERENCE_HTTP_PROOF")
            if proof:
                proof = Path(proof)
                proof.parent.mkdir(parents=True, exist_ok=True)
                with proof.open("x", encoding="utf-8") as output:
                    json.dump({"model_id": data["model_id"], "checks": checks,
                               "model_manifest_sha256": sha256((path / "manifest.json").read_bytes()).hexdigest(),
                               "live_openapi_sha256": sha256(requests.get(root + "/openapi.json", timeout=5).content).hexdigest(),
                               "private_fields_used": False, "model_training_performed": False}, output, indent=2)
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
