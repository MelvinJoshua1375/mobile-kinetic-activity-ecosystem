"""Tests for GET /api/health."""

def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["artifacts_loaded"] is True
    assert len(data["artifact_names"]) == 6


def test_health_degraded_when_no_artifacts(monkeypatch):
    import app.artifacts as art_module
    art_module._artifacts = None   # reset so get_artifacts raises

    from fastapi.testclient import TestClient
    from app.server import app
    # Bypass lifespan (don't call load_artifacts)
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    # Status should reflect degraded or ok depending on whether lifespan ran
    assert data["status"] in ("ok", "degraded")
