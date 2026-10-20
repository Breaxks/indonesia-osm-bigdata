from fastapi import APIRouter, HTTPException

from app.api.deps import run_or_503
from app.services import graph_service

router = APIRouter(prefix="/api/graph", tags=["Graph Analytics"])


@router.get("/summary")
def national_summary():
    return run_or_503(graph_service.get_national_graph_summary)


@router.get("/provinces")
def all_province_metrics():
    return run_or_503(graph_service.get_all_province_graph_metrics)


@router.get("/{region}/summary")
def region_summary(region: str):
    result = run_or_503(graph_service.get_region_graph_summary, region)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No graph computed for region '{region}'.")
    return result


@router.get("/{region}/centrality")
def region_centrality(region: str, limit: int = 10):
    return run_or_503(graph_service.get_region_centrality, region, limit=limit)


@router.get("/{region}/nodes")
def region_nodes(region: str, limit: int = 200):
    return run_or_503(graph_service.get_region_nodes, region, limit=limit)


@router.get("/{region}/degree-distribution")
def region_degree_distribution(region: str):
    return run_or_503(graph_service.get_degree_distribution, region)
