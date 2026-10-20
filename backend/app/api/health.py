from fastapi import APIRouter

from app.config import API_VERSION
from app.services import data_service

router = APIRouter(tags=["Health"])


@router.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": API_VERSION,
        "dataset_processed": data_service.is_processed(),
    }


@router.get("/api/pipeline-status")
def pipeline_status():
    return data_service.get_pipeline_status()
