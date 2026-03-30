"""GET /api/anomalies — paginated anomaly records."""

from fastapi import APIRouter, Query
from ..artifacts import get_artifacts
from ..schemas import AnomaliesResponse, AnomalyRecord

router = APIRouter(prefix="/api", tags=["anomalies"])


@router.get("/anomalies", response_model=AnomaliesResponse)
def get_anomalies(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Records per page"),
    cluster: int | None = Query(None, description="Filter by cluster id"),
    activity: int | None = Query(None, description="Filter by activity id (0–12)"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum anomaly score"),
):
    art = get_artifacts()
    records = art.anomalies["records"]

    # Filter
    if cluster is not None:
        records = [r for r in records if r["cluster"] == cluster]
    if activity is not None:
        records = [r for r in records if r["activity"] == activity]
    if min_score > 0.0:
        records = [r for r in records if r["anomaly_score"] >= min_score]

    total = art.anomalies["total_anomalies"]
    start = (page - 1) * page_size
    page_records = records[start : start + page_size]

    return AnomaliesResponse(
        total_anomalies=total,
        page=page,
        page_size=page_size,
        records=[AnomalyRecord(**r) for r in page_records],
    )
