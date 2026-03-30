"""Tests for GET /api/clusters."""


def test_clusters_returns_all(client):
    resp = client.get("/api/clusters")
    assert resp.status_code == 200
    data = resp.json()
    assert data["k"] == 2
    assert len(data["clusters"]) == 2


def test_cluster_structure(client):
    resp = client.get("/api/clusters")
    c0 = resp.json()["clusters"][0]
    assert "cluster_id" in c0
    assert "size" in c0
    assert "pct" in c0
    assert "feature_means" in c0
    assert "top_activities" in c0
    assert isinstance(c0["feature_means"], dict)
    assert len(c0["feature_means"]) == 16  # 12 sensors + 4 magnitudes


def test_clusters_sorted_by_id(client):
    resp = client.get("/api/clusters")
    ids = [c["cluster_id"] for c in resp.json()["clusters"]]
    assert ids == sorted(ids)
