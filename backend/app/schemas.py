"""Pydantic models for request/response validation."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

SENSOR_COLS = [
    "al_x", "al_y", "al_z",
    "gl_x", "gl_y", "gl_z",
    "ar_x", "ar_y", "ar_z",
    "gr_x", "gr_y", "gr_z",
]


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    artifacts_loaded: bool
    artifact_names: list[str]


# ---------------------------------------------------------------------------
# /api/clusters
# ---------------------------------------------------------------------------

class ClusterActivity(BaseModel):
    activity: int
    count: int


class ClusterDetail(BaseModel):
    cluster_id: int
    size: int
    pct: float
    feature_means: dict[str, float]
    top_activities: list[ClusterActivity]


class ClustersResponse(BaseModel):
    k: int
    clusters: list[ClusterDetail]


# ---------------------------------------------------------------------------
# /api/anomalies
# ---------------------------------------------------------------------------

class AnomalyRecord(BaseModel):
    activity: int
    subject: str
    cluster: int
    anomaly_score: float
    iso_score: float
    lof_score: float
    al_x: float
    al_y: float
    al_z: float
    gl_x: float
    gl_y: float
    gl_z: float
    ar_x: float
    ar_y: float
    ar_z: float
    gr_x: float
    gr_y: float
    gr_z: float
    al_mag: float
    gl_mag: float
    ar_mag: float
    gr_mag: float


class AnomaliesResponse(BaseModel):
    total_anomalies: int
    page: int
    page_size: int
    records: list[AnomalyRecord]


# ---------------------------------------------------------------------------
# /api/predict
# ---------------------------------------------------------------------------

class SensorReading(BaseModel):
    al_x: float = Field(..., description="Accelerometer X")
    al_y: float = Field(..., description="Accelerometer Y")
    al_z: float = Field(..., description="Accelerometer Z")
    gl_x: float = Field(..., description="Gyroscope X")
    gl_y: float = Field(..., description="Gyroscope Y")
    gl_z: float = Field(..., description="Gyroscope Z")
    ar_x: float = Field(..., description="Rotation acceleration X")
    ar_y: float = Field(..., description="Rotation acceleration Y")
    ar_z: float = Field(..., description="Rotation acceleration Z")
    gr_x: float = Field(..., description="Rotation gravity X")
    gr_y: float = Field(..., description="Rotation gravity Y")
    gr_z: float = Field(..., description="Rotation gravity Z")


class PredictResponse(BaseModel):
    cluster: int
    anomaly_score: float
    is_anomaly: bool
    distances_to_centroids: dict[str, float]
    magnitudes: dict[str, float]


# ---------------------------------------------------------------------------
# /api/experiments
# ---------------------------------------------------------------------------

class ExperimentRun(BaseModel):
    algo: str
    k: int
    silhouette: float
    wssse: float | None = None


class ExperimentsResponse(BaseModel):
    runs: list[ExperimentRun]
    best_run: ExperimentRun
