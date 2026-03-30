"""POST /api/predict — nearest-centroid cluster assignment + anomaly score."""

from fastapi import APIRouter
from ..artifacts import get_artifacts, compute_prediction
from ..schemas import SensorReading, PredictResponse

router = APIRouter(prefix="/api", tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(reading: SensorReading):
    art = get_artifacts()
    result = compute_prediction(reading.model_dump(), art)
    return PredictResponse(**result)
