from fastapi import APIRouter, HTTPException, Query

from app.api.deps import run_or_503
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.services import data_service

router = APIRouter(prefix="/api", tags=["Regions"])


@router.get("/regions/{region}/summary")
def region_summary(region: str):
    result = run_or_503(data_service.get_region_summary, region)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found.")
    return result


@router.get("/regions/{region}/roads")
def region_roads(
    region: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    return run_or_503(data_service.get_region_roads, region, page=page, page_size=page_size)


@router.get("/regions/{region}/geojson")
def region_geojson(region: str):
    result = run_or_503(data_service.get_region_geojson, region)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No GeoJSON available for region '{region}'. "
                   f"It may have too few roads or an unrecognized name.",
        )
    return result


@router.get("/geojson-manifest")
def geojson_manifest():
    return run_or_503(data_service.get_geojson_manifest)


@router.get("/compare")
def compare(region_a: str, region_b: str):
    try:
        return run_or_503(data_service.compare_regions, region_a, region_b)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
