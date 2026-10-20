from fastapi import APIRouter

from app.api.deps import run_or_503
from app.services import data_service

router = APIRouter(prefix="/api", tags=["Overview"])


@router.get("/overview")
def overview():
    return run_or_503(data_service.get_overview)


@router.get("/provinces")
def provinces():
    return run_or_503(data_service.get_provinces)


@router.get("/cities")
def cities():
    # Placeholder scope note: city/regency-level (admin_level=6) breakdown
    # is not extracted by default -- province-level is the implemented
    # minimum required by the project spec. Extend extract_osm.py's
    # boundary extraction to admin_level=6 to populate this.
    return []


@router.get("/road-types")
def road_types():
    return run_or_503(data_service.get_road_types)


@router.get("/province-rankings")
def province_rankings():
    return run_or_503(data_service.get_province_rankings)


@router.get("/road-type-distribution")
def road_type_distribution():
    return run_or_503(data_service.get_road_type_distribution)


@router.get("/top-provinces-by-density")
def top_provinces_by_density(limit: int = 10):
    return run_or_503(data_service.get_top_provinces_by_density, limit=limit)


@router.get("/top-provinces-by-road-per-capita")
def top_provinces_by_road_per_capita(limit: int = 10):
    return run_or_503(data_service.get_top_provinces_by_road_per_capita, limit=limit)
