"""Pydantic schemas for API responses (validation + OpenAPI docs)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class PipelineStatus(BaseModel):
    processed: bool
    mode: Optional[str] = None
    processed_at_utc: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    road_records_extracted: Optional[int] = None
    provinces_detected: Optional[int] = None
    note: Optional[str] = None


class OverviewResponse(BaseModel):
    total_road_segments: int = 0
    total_road_length_km: float = 0
    average_segment_length_m: float = 0
    number_of_provinces: int = 0
    number_of_road_types: int = 0
    major_road_percentage: float = 0
    accessibility_score_avg: Optional[float] = None
    processed: bool = True


class RoadRecord(BaseModel):
    osm_id: Any
    name: Optional[str] = None
    highway: Optional[str] = None
    length_m: Optional[float] = None
    province: Optional[str] = None
    oneway: Optional[bool] = None
    lanes: Optional[float] = None
    surface: Optional[str] = None
    maxspeed: Optional[float] = None
    bridge: Optional[bool] = None
    tunnel: Optional[bool] = None


class PaginatedRoads(BaseModel):
    items: list[RoadRecord]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class ErrorResponse(BaseModel):
    detail: str
