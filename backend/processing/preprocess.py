"""
Preprocessing stage.

Takes the raw extracted road GeoDataFrame and:
  1. Cleans invalid / empty geometries and duplicate ways.
  2. Computes geodesic road length in meters.
  3. Normalizes tag values (oneway, bridge, tunnel to booleans; lanes,
     maxspeed to numeric).
  4. Assigns each road to a province via spatial join against admin
     boundaries (extracted from the PBF, or a bundled fallback file).
  5. Detects intersection nodes (endpoints shared by 2+ road ways).
  6. Saves `roads.parquet` and `nodes.parquet`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import GEOJSON_DIR, NODES_PARQUET, ROADS_PARQUET  # noqa: E402
from app.utils.geo_utils import line_length_m, node_key  # noqa: E402
from app.utils.logging_utils import log  # noqa: E402

FALLBACK_PROVINCE_BOUNDARIES = GEOJSON_DIR / "_province_boundaries_fallback.geojson"


def _parse_bool_tag(value) -> bool:
    if value is None:
        return False
    v = str(value).strip().lower()
    return v in {"yes", "true", "1"}


def clean_roads(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    log(f"    Rows before cleaning: {len(roads):,}")

    roads = roads[roads.geometry.notnull()].copy()
    roads = roads[~roads.geometry.is_empty].copy()
    roads = roads[roads.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()

    if "osm_id" in roads.columns:
        roads = roads.drop_duplicates(subset=["osm_id"])

    roads["highway"] = roads.get("highway", pd.Series(dtype=object)).astype(str).str.lower()
    roads["name"] = roads.get("name", pd.Series(dtype=object)).fillna("Unnamed road")
    roads["surface"] = roads.get("surface", pd.Series(dtype=object)).fillna("unknown")
    roads["oneway"] = roads.get("oneway", pd.Series(dtype=object)).apply(_parse_bool_tag)
    roads["bridge"] = roads.get("bridge", pd.Series(dtype=object)).apply(_parse_bool_tag)
    roads["tunnel"] = roads.get("tunnel", pd.Series(dtype=object)).apply(_parse_bool_tag)

    def _to_numeric_lanes(v):
        try:
            return float(str(v).split(";")[0])
        except (TypeError, ValueError):
            return None

    def _to_numeric_speed(v):
        try:
            return float(str(v).split(" ")[0])
        except (TypeError, ValueError):
            return None

    roads["lanes"] = roads.get("lanes", pd.Series(dtype=object)).apply(_to_numeric_lanes)
    roads["maxspeed"] = roads.get("maxspeed", pd.Series(dtype=object)).apply(_to_numeric_speed)

    log(f"    Rows after cleaning: {len(roads):,}")
    return roads


def compute_lengths(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    def _length(geom):
        if geom.geom_type == "LineString":
            return line_length_m(list(geom.coords))
        total = 0.0
        for part in geom.geoms:
            total += line_length_m(list(part.coords))
        return total

    roads["length_m"] = roads.geometry.apply(_length)
    roads = roads[roads["length_m"] > 0].copy()
    log(f"    Computed geodesic length for {len(roads):,} roads.")
    return roads


def load_boundaries(extracted_boundaries: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame | None:
    if extracted_boundaries is not None and not extracted_boundaries.empty:
        return extracted_boundaries
    if FALLBACK_PROVINCE_BOUNDARIES.exists():
        log(f"    Using bundled fallback province boundaries: "
            f"{FALLBACK_PROVINCE_BOUNDARIES.name}")
        return gpd.read_file(FALLBACK_PROVINCE_BOUNDARIES)
    log("    WARNING: No province boundaries available (neither extracted from "
        "the PBF nor a fallback file). Roads will be saved with province='Unknown'. "
        "See README for how to supply a province boundary GeoJSON.")
    return None


def assign_provinces(roads: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    if boundaries is None or boundaries.empty or "province" not in boundaries.columns:
        roads["province"] = "Unknown"
        return roads

    roads = roads.set_crs("EPSG:4326", allow_override=True) if roads.crs is None else roads
    boundaries = boundaries.set_crs("EPSG:4326", allow_override=True) if boundaries.crs is None else boundaries

    roads["centroid"] = roads.geometry.centroid
    points = gpd.GeoDataFrame(roads[["osm_id"]], geometry=roads["centroid"], crs="EPSG:4326")

    joined = gpd.sjoin(points, boundaries[["province", "geometry"]], how="left", predicate="within")
    joined = joined.drop_duplicates(subset=["osm_id"])

    roads = roads.merge(joined[["osm_id", "province"]], on="osm_id", how="left")
    roads["province"] = roads["province"].fillna("Unknown")
    roads = roads.drop(columns=["centroid"])
    log(f"    Assigned provinces to roads. Unique provinces found: "
        f"{roads['province'].nunique()}")
    return roads


def detect_intersections(roads: gpd.GeoDataFrame) -> pd.DataFrame:
    """A node is an intersection if 2+ distinct road ways share an endpoint."""
    endpoint_counts: dict[str, int] = {}
    endpoint_coords: dict[str, tuple] = {}

    def _endpoints(geom):
        if geom.geom_type == "LineString":
            coords = list(geom.coords)
            return [coords[0], coords[-1]]
        pts = []
        for part in geom.geoms:
            c = list(part.coords)
            pts.extend([c[0], c[-1]])
        return pts

    for geom in roads.geometry:
        for lon, lat, *_ in _endpoints(geom):
            key = node_key(lon, lat)
            endpoint_counts[key] = endpoint_counts.get(key, 0) + 1
            endpoint_coords[key] = (lon, lat)

    records = [
        {"node_id": k, "lon": v[0], "lat": v[1], "degree": endpoint_counts[k],
         "is_intersection": endpoint_counts[k] >= 2}
        for k, v in endpoint_coords.items()
    ]
    nodes = pd.DataFrame(records)
    n_intersections = int(nodes["is_intersection"].sum())
    log(f"    Detected {len(nodes):,} unique nodes, {n_intersections:,} intersections.")
    return nodes


def run_preprocessing(roads: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame | None):
    roads = clean_roads(roads)
    roads = compute_lengths(roads)
    boundaries = load_boundaries(boundaries)
    roads = assign_provinces(roads, boundaries)
    nodes = detect_intersections(roads)

    roads_out = roads.drop(columns=["geometry"]).copy()
    roads_out["geometry_wkt"] = roads.geometry.apply(lambda g: g.wkt)
    roads_out.to_parquet(ROADS_PARQUET, index=False)
    nodes.to_parquet(NODES_PARQUET, index=False)

    log(f"    Saved {ROADS_PARQUET.name} ({len(roads_out):,} rows) "
        f"and {NODES_PARQUET.name} ({len(nodes):,} rows).")
    return roads, nodes, boundaries
