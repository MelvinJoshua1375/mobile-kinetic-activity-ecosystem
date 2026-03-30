"""Tests for GET /api/anomalies."""


def test_anomalies_default(client):
    resp = client.get("/api/anomalies")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_anomalies" in data
    assert "records" in data
    assert data["page"] == 1
    assert data["page_size"] == 50


def test_anomalies_pagination(client):
    resp = client.get("/api/anomalies?page=1&page_size=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["records"]) <= 1


def test_anomalies_filter_cluster(client):
    resp = client.get("/api/anomalies?cluster=0")
    assert resp.status_code == 200
    for rec in resp.json()["records"]:
        assert rec["cluster"] == 0


def test_anomalies_filter_activity(client):
    resp = client.get("/api/anomalies?activity=3")
    assert resp.status_code == 200
    for rec in resp.json()["records"]:
        assert rec["activity"] == 3


def test_anomalies_filter_min_score(client):
    resp = client.get("/api/anomalies?min_score=0.9")
    assert resp.status_code == 200
    for rec in resp.json()["records"]:
        assert rec["anomaly_score"] >= 0.9


def test_anomalies_record_fields(client):
    resp = client.get("/api/anomalies")
    rec = resp.json()["records"][0]
    required = ["activity", "subject", "cluster", "anomaly_score",
                "iso_score", "lof_score", "al_x", "al_y", "al_z"]
    for field in required:
        assert field in rec, f"Missing field: {field}"
