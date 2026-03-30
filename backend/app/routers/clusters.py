"""GET /api/clusters — per-cluster statistics."""

from fastapi import APIRouter
from ..artifacts import get_artifacts
from ..schemas import ClustersResponse, ClusterDetail, ClusterActivity

router = APIRouter(prefix="/api", tags=["clusters"])


@router.get("/clusters", response_model=ClustersResponse)
def get_clusters():
    art = get_artifacts()
    clusters = []
    for cid_str, stats in art.cluster_stats.items():
        clusters.append(
            ClusterDetail(
                cluster_id=int(cid_str),
                size=stats["size"],
                pct=stats["pct"],
                feature_means=stats["feature_means"],
                top_activities=[
                    ClusterActivity(**a) for a in stats["top_activities"]
                ],
            )
        )
    clusters.sort(key=lambda c: c.cluster_id)
    return ClustersResponse(k=art.k, clusters=clusters)
