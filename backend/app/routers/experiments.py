"""GET /api/experiments — elbow/silhouette sweep results."""

from fastapi import APIRouter, Query
from ..artifacts import get_artifacts
from ..schemas import ExperimentsResponse, ExperimentRun

router = APIRouter(prefix="/api", tags=["experiments"])


@router.get("/experiments", response_model=ExperimentsResponse)
def get_experiments(
    algo: str | None = Query(None, description="Filter by algorithm name"),
):
    art = get_artifacts()
    runs = art.experiment_results

    if algo:
        runs = [r for r in runs if r["algo"].lower() == algo.lower()]

    run_objects = [ExperimentRun(**r) for r in runs]

    # Best = highest silhouette among KMeans runs
    kmeans_runs = [r for r in run_objects if r.algo == "KMeans"]
    best = max(kmeans_runs, key=lambda r: r.silhouette) if kmeans_runs else max(run_objects, key=lambda r: r.silhouette)

    return ExperimentsResponse(runs=run_objects, best_run=best)
