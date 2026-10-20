"""Shared geospatial helper functions used across the pipeline and API."""
from __future__ import annotations

import math
from typing import Iterable, Tuple

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def line_length_m(coords: Iterable[Tuple[float, float]]) -> float:
    """Geodesic length in meters of a line given (lon, lat) coordinate pairs."""
    coords = list(coords)
    if len(coords) < 2:
        return 0.0
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
        total += dist
    return total


def polygon_area_km2(geom) -> float:
    """Geodesic area in square kilometers of a shapely polygon/multipolygon."""
    if geom is None or geom.is_empty:
        return 0.0
    area_m2, _ = _GEOD.geometry_area_perimeter(geom)
    return abs(area_m2) / 1_000_000.0


def round_coord(value: float, precision: int = 6) -> float:
    """Round a coordinate to merge near-duplicate endpoints into one node."""
    return round(value, precision)


def node_key(lon: float, lat: float, precision: int = 6) -> str:
    """Stable string key identifying a graph node from a rounded coordinate."""
    return f"{round_coord(lon, precision)}_{round_coord(lat, precision)}"


def min_max_normalize(series):
    """Min-max normalize a pandas Series to the 0-1 range (safe on constant input)."""
    lo, hi = series.min(), series.max()
    if hi - lo == 0:
        return series * 0
    return (series - lo) / (hi - lo)
