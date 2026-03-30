"""Tests for POST /api/predict."""

SAMPLE_READING = {
    "al_x": 0.1, "al_y": 0.2, "al_z": 9.8,
    "gl_x": 0.0, "gl_y": 0.0, "gl_z": 0.0,
    "ar_x": 0.0, "ar_y": 0.0, "ar_z": 0.0,
    "gr_x": 0.0, "gr_y": 9.8, "gr_z": 0.0,
}


def test_predict_returns_cluster(client):
    resp = client.post("/api/predict", json=SAMPLE_READING)
    assert resp.status_code == 200
    data = resp.json()
    assert "cluster" in data
    assert data["cluster"] in [0, 1]


def test_predict_returns_anomaly_score(client):
    resp = client.post("/api/predict", json=SAMPLE_READING)
    data = resp.json()
    assert "anomaly_score" in data
    assert 0.0 <= data["anomaly_score"] <= 1.0
    assert isinstance(data["is_anomaly"], bool)


def test_predict_returns_magnitudes(client):
    resp = client.post("/api/predict", json=SAMPLE_READING)
    mags = resp.json()["magnitudes"]
    assert set(mags.keys()) == {"al_mag", "gl_mag", "ar_mag", "gr_mag"}
    for v in mags.values():
        assert v >= 0


def test_predict_returns_distances(client):
    resp = client.post("/api/predict", json=SAMPLE_READING)
    dists = resp.json()["distances_to_centroids"]
    assert "0" in dists and "1" in dists


def test_predict_missing_field(client):
    bad = {k: v for k, v in SAMPLE_READING.items() if k != "al_x"}
    resp = client.post("/api/predict", json=bad)
    assert resp.status_code == 422


def test_predict_extreme_values_clamped(client):
    """Values outside IQR bounds should be winsorized, not cause errors."""
    extreme = {k: 9999.0 for k in SAMPLE_READING}
    resp = client.post("/api/predict", json=extreme)
    assert resp.status_code == 200
