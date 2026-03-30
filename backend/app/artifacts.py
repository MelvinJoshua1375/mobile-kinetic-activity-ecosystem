"""
Singleton artifact loader.

Loads all 4 JSON files exactly once at startup and exposes them through
`get_artifacts()`.  Raises a clear RuntimeError if a file is missing so
the service fails fast rather than returning wrong data.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Default location — override with ARTIFACTS_DIR env var
_DEFAULT_DIR = Path(__file__).parent.parent.parent / "artifacts"


@dataclass
class Artifacts:
    cluster_stats: dict[str, Any]
    anomalies: dict[str, Any]
    anomaly_thresholds: dict[str, Any]
    centroids: dict[str, Any]          # {cluster_id_str: {feature: mean}}
    iqr_bounds: dict[str, list[float]] # {col: [lo, hi]}
    experiment_results: list[dict]

    # Derived helpers (computed after load)
    k: int = field(init=False)
    feature_cols: list[str] = field(init=False)

    def __post_init__(self):
        self.k = len(self.cluster_stats)
        # Infer feature list from the first centroid entry
        first = next(iter(self.centroids.values()))
        self.feature_cols = list(first.keys())


_artifacts: Artifacts | None = None


def load_artifacts(artifacts_dir: str | Path | None = None) -> Artifacts:
    """Load JSON artifacts from *artifacts_dir* (or env ARTIFACTS_DIR)."""
    global _artifacts

    base = Path(
        artifacts_dir
        or os.environ.get("ARTIFACTS_DIR", str(_DEFAULT_DIR))
    )

    def _read(name: str) -> Any:
        path = base / name
        if not path.exists():
            raise RuntimeError(
                f"Artifact not found: {path}\n"
                f"Run the Databricks notebooks first and copy JSON files to {base}"
            )
        with open(path) as f:
            return json.load(f)

    _artifacts = Artifacts(
        cluster_stats=_read("cluster_stats.json"),
        anomalies=_read("anomalies.json"),
        anomaly_thresholds=_read("anomaly_thresholds.json"),
        centroids=_read("centroids.json"),
        iqr_bounds=_read("iqr_bounds.json"),
        experiment_results=_read("experiment_results.json"),
    )
    return _artifacts


def get_artifacts() -> Artifacts:
    """Return the loaded artifacts; raises if not yet loaded."""
    if _artifacts is None:
        raise RuntimeError("Artifacts not loaded. Call load_artifacts() first.")
    return _artifacts


# ---------------------------------------------------------------------------
# Inference helpers (pure numpy — no Spark at runtime)
# ---------------------------------------------------------------------------

def _euclidean(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in a))


def _winsorize_value(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_prediction(reading: dict[str, float], art: Artifacts) -> dict:
    """
    Given raw sensor readings, return:
    - cluster assignment (nearest centroid in raw-feature space)
    - anomaly_score (0–1, higher = more anomalous)
    - distances_to_centroids
    - magnitudes
    """
    # 1. Winsorize
    clean = {}
    for col in ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
                "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z"]:
        lo, hi = art.iqr_bounds[col]
        clean[col] = _winsorize_value(reading[col], lo, hi)

    # 2. Magnitudes
    mags = {
        "al_mag": math.sqrt(clean["al_x"]**2 + clean["al_y"]**2 + clean["al_z"]**2),
        "gl_mag": math.sqrt(clean["gl_x"]**2 + clean["gl_y"]**2 + clean["gl_z"]**2),
        "ar_mag": math.sqrt(clean["ar_x"]**2 + clean["ar_y"]**2 + clean["ar_z"]**2),
        "gr_mag": math.sqrt(clean["gr_x"]**2 + clean["gr_y"]**2 + clean["gr_z"]**2),
    }
    point = {**clean, **mags}

    # 3. Nearest centroid
    distances: dict[str, float] = {}
    for cid, centroid in art.centroids.items():
        distances[cid] = _euclidean(point, centroid)

    cluster = int(min(distances, key=distances.get))
    min_dist = distances[str(cluster)]

    # 4. Anomaly score — distance relative to threshold
    threshold = art.anomaly_thresholds["combined_threshold"]
    # Normalise: distance beyond the 95th percentile threshold → anomalous
    max_dist = max(distances.values())
    anomaly_score = min(min_dist / (max_dist + 1e-9), 1.0)
    is_anomaly = anomaly_score > threshold

    return {
        "cluster": cluster,
        "anomaly_score": round(anomaly_score, 4),
        "is_anomaly": bool(is_anomaly),
        "distances_to_centroids": {k: round(v, 6) for k, v in distances.items()},
        "magnitudes": {k: round(v, 6) for k, v in mags.items()},
    }
