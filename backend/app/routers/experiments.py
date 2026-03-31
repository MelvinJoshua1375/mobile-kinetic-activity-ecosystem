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

    # Best = elbow method (largest 2nd derivative of WSSSE) among KMeans runs
    kmeans_runs = sorted(
        [r for r in run_objects if r.algo == "KMeans" and r.wssse is not None],
        key=lambda r: r.k,
    )
    if len(kmeans_runs) >= 3:
        ws = [r.wssse for r in kmeans_runs]
        d2 = [ws[i-1] - 2*ws[i] + ws[i+1] for i in range(1, len(ws)-1)]
        elbow_idx = d2.index(max(d2)) + 1
        best = kmeans_runs[elbow_idx]
    elif kmeans_runs:
        best = max(kmeans_runs, key=lambda r: r.silhouette)
    else:
        best = max(run_objects, key=lambda r: r.silhouette)

    return ExperimentsResponse(runs=run_objects, best_run=best)
