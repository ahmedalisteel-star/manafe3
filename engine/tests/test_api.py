# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""The HTTP API: /health versions and /peb/frame over HTTP (FastAPI TestClient, no server needed)."""

from importlib.metadata import version

from fastapi.testclient import TestClient

from engine import __version__
from engine.api import app

client = TestClient(app)


def test_health_reports_versions():
    r = client.get("/health")
    assert r.status_code == 200
    h = r.json()
    assert h["status"] == "ok"
    assert h["engine"] == __version__
    assert h["pynite"] == version("PyNiteFEA") == "3.0.0"
    assert h["bimsteelauto"] == version("bimsteelauto")
    assert h["bimsteelauto"] is not None
    assert set(h["private_peb"]) == {"configured", "found"}


def test_frame_endpoint():
    r = client.post("/peb/frame", json={"span": 20000, "eave_height": 6000, "roof_slope": 0.1, "bay_spacing": 6000, "n_bays": 2})
    assert r.status_code == 200
    f = r.json()
    assert len(f["members"]) == 12
    assert f["apex_height"] == 7000.0


def test_frame_endpoint_refuses_bad_input():
    r = client.post("/peb/frame", json={"span": 20000, "eave_height": 6000, "roof_slope": 0.1, "bay_spacing": 6000, "n_bays": 0})
    assert r.status_code == 422
    assert "bays" in r.json()["detail"]


def test_cors_allows_the_web_app_only():
    ok = client.options("/peb/frame", headers={"Origin": "http://localhost:8000", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:8000"
    bad = client.options("/peb/frame", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers
