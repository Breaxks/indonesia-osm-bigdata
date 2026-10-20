from fastapi import APIRouter

from app.api.deps import run_or_503
from app.services import ml_service

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])


@router.get("/metrics")
def ml_metrics():
    return run_or_503(ml_service.get_ml_metrics)


@router.get("/feature-importance")
def feature_importance():
    return run_or_503(ml_service.get_feature_importance)


@router.get("/predictions")
def predictions():
    return run_or_503(ml_service.get_predictions)
