"""GET /api/health — liveness + artifact status."""

from fastapi import APIRouter
from ..artifacts import get_artifacts
from ..schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    try:
        art = get_artifacts()
        return HealthResponse(
            status="ok",
            artifacts_loaded=True,
            artifact_names=[
                "cluster_stats",
                "anomalies",
                "anomaly_thresholds",
                "centroids",
                "iqr_bounds",
                "experiment_results",
            ],
        )
    except RuntimeError:
        return HealthResponse(
            status="degraded",
            artifacts_loaded=False,
            artifact_names=[],
        )
