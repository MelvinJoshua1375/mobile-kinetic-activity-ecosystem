"""Tests for GET /api/experiments."""


def test_experiments_all(client):
    resp = client.get("/api/experiments")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert "best_run" in data
    assert len(data["runs"]) == 6   # matches MOCK_EXPERIMENT_RESULTS


def test_experiments_filter_algo(client):
    resp = client.get("/api/experiments?algo=KMeans")
    data = resp.json()
    for run in data["runs"]:
        assert run["algo"] == "KMeans"


def test_experiments_best_is_kmeans(client):
    resp = client.get("/api/experiments")
    best = resp.json()["best_run"]
    assert best["algo"] == "KMeans"
    assert best["k"] == 5   # elbow method picks k=5 from mock data


def test_experiments_run_structure(client):
    resp = client.get("/api/experiments")
    run = resp.json()["runs"][0]
    assert "algo" in run
    assert "k" in run
    assert "silhouette" in run


def test_experiments_filter_case_insensitive(client):
    resp = client.get("/api/experiments?algo=kmeans")
    data = resp.json()
    for run in data["runs"]:
        assert run["algo"] == "KMeans"
