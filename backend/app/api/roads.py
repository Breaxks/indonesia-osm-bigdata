from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import run_or_503
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.services import data_service

router = APIRouter(prefix="/api", tags=["Roads"])


@router.get("/roads")
def list_roads(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    province: Optional[str] = None,
    road_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "length_m",
    sort_desc: bool = True,
):
    return run_or_503(
        data_service.get_roads,
        page=page, page_size=page_size, province=province, road_type=road_type,
        search=search, sort_by=sort_by, sort_desc=sort_desc,
    )


@router.get("/roads/{osm_id}")
def get_road(osm_id: str):
    result = run_or_503(data_service.get_road_by_id, osm_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Road with osm_id={osm_id} not found.")
    return result
