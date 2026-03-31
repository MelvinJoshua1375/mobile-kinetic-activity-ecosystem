"""Shared test fixtures."""

import json
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Minimal mock artifacts
# ---------------------------------------------------------------------------

MOCK_CLUSTER_STATS = {
    "0": {
        "cluster_id": 0,
        "size": 500000,
        "pct": 40.0,
        "feature_means": {
            "al_x": 0.1, "al_y": 0.2, "al_z": 9.8,
            "gl_x": 0.0, "gl_y": 0.0, "gl_z": 0.0,
            "ar_x": 0.0, "ar_y": 0.0, "ar_z": 0.0,
            "gr_x": 0.0, "gr_y": 9.8, "gr_z": 0.0,
            "al_mag": 9.81, "gl_mag": 0.01, "ar_mag": 0.01, "gr_mag": 9.8,
        },
        "top_activities": [{"activity": 0, "count": 400000}],
    },
    "1": {
        "cluster_id": 1,
        "size": 300000,
        "pct": 24.0,
        "feature_means": {
            "al_x": 1.0, "al_y": 2.0, "al_z": 8.0,
            "gl_x": 0.5, "gl_y": 0.5, "gl_z": 0.5,
            "ar_x": 0.1, "ar_y": 0.1, "ar_z": 0.1,
            "gr_x": 0.1, "gr_y": 9.5, "gr_z": 0.1,
            "al_mag": 8.31, "gl_mag": 0.87, "ar_mag": 0.17, "gr_mag": 9.51,
        },
        "top_activities": [{"activity": 1, "count": 200000}],
    },
}

MOCK_ANOMALY_RECORD = {
    "activity": 3, "subject": "subject1", "cluster": 0,
    "anomaly_score": 0.95, "iso_score": -0.3, "lof_score": -0.4,
    "al_x": 5.0, "al_y": 5.0, "al_z": 5.0,
    "gl_x": 5.0, "gl_y": 5.0, "gl_z": 5.0,
    "ar_x": 5.0, "ar_y": 5.0, "ar_z": 5.0,
    "gr_x": 5.0, "gr_y": 5.0, "gr_z": 5.0,
    "al_mag": 8.66, "gl_mag": 8.66, "ar_mag": 8.66, "gr_mag": 8.66,
}

MOCK_ANOMALIES = {
    "total_anomalies": 1,
    "records": [MOCK_ANOMALY_RECORD],
}

MOCK_THRESHOLDS = {
    "iso_threshold": -0.1,
    "lof_threshold": -0.1,
    "combined_threshold": 0.9,
}

MOCK_CENTROIDS = {
    "0": MOCK_CLUSTER_STATS["0"]["feature_means"],
    "1": MOCK_CLUSTER_STATS["1"]["feature_means"],
}

MOCK_IQR_BOUNDS = {
    col: [-50.0, 50.0]
    for col in [
        "al_x","al_y","al_z","gl_x","gl_y","gl_z",
        "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z",
    ]
}

MOCK_EXPERIMENT_RESULTS = [
    {"algo": "KMeans", "k": 2, "silhouette": 0.25, "wssse": 5000000},
    {"algo": "KMeans", "k": 3, "silhouette": 0.24, "wssse": 4000000},
    {"algo": "KMeans", "k": 5, "silhouette": 0.28, "wssse": 2500000},
    {"algo": "KMeans", "k": 7, "silhouette": 0.22, "wssse": 2200000},
    {"algo": "BisectingKMeans", "k": 5, "silhouette": 0.26},
    {"algo": "GaussianMixture", "k": 5, "silhouette": 0.22},
]


@pytest.fixture
def mock_artifacts(tmp_path, monkeypatch):
    """Write mock JSON files to a temp dir and patch load_artifacts."""
    files = {
        "cluster_stats.json": MOCK_CLUSTER_STATS,
        "anomalies.json": MOCK_ANOMALIES,
        "anomaly_thresholds.json": MOCK_THRESHOLDS,
        "centroids.json": MOCK_CENTROIDS,
        "iqr_bounds.json": MOCK_IQR_BOUNDS,
        "experiment_results.json": MOCK_EXPERIMENT_RESULTS,
    }
    for name, data in files.items():
        (tmp_path / name).write_text(json.dumps(data))

    import app.artifacts as art_module
    art_module._artifacts = None  # reset singleton
    art_module.load_artifacts(artifacts_dir=tmp_path)

    # Prevent the lifespan from overwriting our mock artifacts
    monkeypatch.setattr(art_module, "load_artifacts", lambda artifacts_dir=None: art_module._artifacts)

    yield
    art_module._artifacts = None


@pytest.fixture
def client(mock_artifacts):
    from app.server import app
    with TestClient(app) as c:
        yield c
