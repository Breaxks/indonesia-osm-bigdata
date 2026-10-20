"""
Core data access layer for the API.

Everything here reads from the pre-processed artifacts written by the
pipeline (`processing/run_pipeline.py`). Nothing in this module invents
or fabricates data -- if a processed file does not exist, functions
return an explicit "not processed" state that the API surfaces as a
clear message rather than a stack trace or fake numbers.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from app.config import (
    GEOJSON_DIR, MAJOR_ROAD_TYPES, OVERVIEW_JSON, PIPELINE_STATUS_JSON,
    PROVINCE_RANKINGS_JSON, PROVINCE_SUMMARY_PARQUET, ROAD_TYPE_DISTRIBUTION_JSON,
    ROAD_TYPE_SUMMARY_PARQUET, ROADS_PARQUET, ACCESSIBILITY_SCORES_PARQUET,
    REGION_FEATURES_PARQUET,
)


class NotProcessedError(Exception):
    """Raised when the caller needs a processed artifact that doesn't exist yet."""


def is_processed() -> bool:
    return PIPELINE_STATUS_JSON.exists() and ROADS_PARQUET.exists()


def get_pipeline_status() -> dict:
    if not PIPELINE_STATUS_JSON.exists():
        return {"processed": False}
    return json.loads(PIPELINE_STATUS_JSON.read_text())


def _require_processed():
    if not is_processed():
        raise NotProcessedError(
            "Dataset has not been processed yet. Run the processing pipeline "
            "first: `python processing/run_pipeline.py --sample` (fast dev "
            "mode) or `--full` (entire Indonesia dataset)."
        )


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


# ---------------------------------------------------------------------------
# Cached parquet loaders. Cleared automatically only on process restart --
# that's fine, since re-running the pipeline is expected to be followed by
# an API restart in this project's workflow (documented in the README).
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _roads_df() -> pd.DataFrame:
    _require_processed()
    return pd.read_parquet(ROADS_PARQUET)


@lru_cache(maxsize=1)
def _province_summary_df() -> pd.DataFrame:
    _require_processed()
    return pd.read_parquet(PROVINCE_SUMMARY_PARQUET)


@lru_cache(maxsize=1)
def _road_type_summary_df() -> pd.DataFrame:
    _require_processed()
    return pd.read_parquet(ROAD_TYPE_SUMMARY_PARQUET)


@lru_cache(maxsize=1)
def _accessibility_scores_df() -> pd.DataFrame:
    _require_processed()
    return pd.read_parquet(ACCESSIBILITY_SCORES_PARQUET)


@lru_cache(maxsize=1)
def _region_features_df() -> pd.DataFrame:
    _require_processed()
    return pd.read_parquet(REGION_FEATURES_PARQUET)


def clear_cache():
    _roads_df.cache_clear()
    _province_summary_df.cache_clear()
    _road_type_summary_df.cache_clear()
    _accessibility_scores_df.cache_clear()
    _region_features_df.cache_clear()


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
def get_overview() -> dict:
    _require_processed()
    overview = json.loads(OVERVIEW_JSON.read_text()) if OVERVIEW_JSON.exists() else {}
    try:
        scores = _accessibility_scores_df()
        overview["accessibility_score_avg"] = round(float(scores["accessibility_score"].mean()), 2)
    except Exception:
        overview["accessibility_score_avg"] = None
    try:
        features = _region_features_df()
        if "population" in features.columns and features["population"].notna().any():
            valid = features.dropna(subset=["population"])
            total_pop = valid["population"].sum()
            total_km = valid["total_length_km"].sum()
            overview["road_km_per_1000_people_avg"] = round(float(total_km / (total_pop / 1000)), 2)
            overview["population_matched_provinces"] = int(len(valid))
            overview["population_total_provinces"] = int(len(features))
        else:
            overview["road_km_per_1000_people_avg"] = None
    except Exception:
        overview["road_km_per_1000_people_avg"] = None
    overview["processed"] = True
    return overview


def get_province_rankings() -> dict:
    _require_processed()
    if not PROVINCE_RANKINGS_JSON.exists():
        return {}
    return json.loads(PROVINCE_RANKINGS_JSON.read_text())


def get_road_type_distribution() -> list[dict]:
    _require_processed()
    if not ROAD_TYPE_DISTRIBUTION_JSON.exists():
        return []
    return json.loads(ROAD_TYPE_DISTRIBUTION_JSON.read_text())


def get_top_provinces_by_density(limit: int = 10) -> list[dict]:
    _require_processed()
    features = _region_features_df()
    if "road_density_km_per_km2" not in features.columns:
        return []
    top = features.sort_values("road_density_km_per_km2", ascending=False).head(limit)
    return top[["province", "road_density_km_per_km2"]].to_dict(orient="records")


def get_top_provinces_by_road_per_capita(limit: int = 10) -> list[dict]:
    """Provinces with the most road length per 1,000 people (BPS population join)."""
    _require_processed()
    features = _region_features_df()
    if "road_km_per_1000_people" not in features.columns:
        return []
    valid = features.dropna(subset=["road_km_per_1000_people"])
    top = valid.sort_values("road_km_per_1000_people", ascending=False).head(limit)
    return top[["province", "road_km_per_1000_people", "population"]].to_dict(orient="records")


# ---------------------------------------------------------------------------
# Provinces / cities
# ---------------------------------------------------------------------------
def get_provinces() -> list[str]:
    _require_processed()
    df = _province_summary_df()
    return sorted(df["province"].tolist())


def get_road_types() -> list[str]:
    _require_processed()
    df = _road_type_summary_df()
    return sorted(df["highway"].tolist())


# ---------------------------------------------------------------------------
# Roads (paginated data explorer + map explorer)
# ---------------------------------------------------------------------------
def get_roads(
    page: int = 1,
    page_size: int = 50,
    province: Optional[str] = None,
    road_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "length_m",
    sort_desc: bool = True,
) -> dict:
    _require_processed()
    df = _roads_df()

    if province:
        df = df[df["province"] == province]
    if road_type:
        df = df[df["highway"] == road_type]
    if search:
        df = df[df["name"].astype(str).str.contains(search, case=False, na=False)]

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=not sort_desc)

    total_items = len(df)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    page_df = df.iloc[start:start + page_size]

    cols = ["osm_id", "name", "highway", "length_m", "province", "oneway",
            "lanes", "surface", "maxspeed", "bridge", "tunnel"]
    cols = [c for c in cols if c in page_df.columns]
    items = page_df[cols].fillna(value=pd.NA).to_dict(orient="records")
    # Replace pandas NA with None for JSON
    items = [{k: (None if pd.isna(v) else v) for k, v in row.items()} for row in items]

    return {
        "items": items, "page": page, "page_size": page_size,
        "total_items": total_items, "total_pages": total_pages,
    }


def get_road_by_id(osm_id) -> Optional[dict]:
    _require_processed()
    df = _roads_df()
    try:
        osm_id_val = int(osm_id)
    except ValueError:
        osm_id_val = osm_id
    match = df[df["osm_id"] == osm_id_val]
    if match.empty:
        return None
    row = match.iloc[0].to_dict()
    return {k: (None if pd.isna(v) else v) for k, v in row.items() if k != "geometry_wkt"}


# ---------------------------------------------------------------------------
# Region summaries / comparisons
# ---------------------------------------------------------------------------
def get_region_summary(region: str) -> Optional[dict]:
    _require_processed()
    summary = _province_summary_df()
    row = summary[summary["province"] == region]
    if row.empty:
        return None
    result = {k: (None if pd.isna(v) else v) for k, v in row.iloc[0].to_dict().items()}

    features = _region_features_df()
    frow = features[features["province"] == region]
    if not frow.empty:
        extra = {k: (None if pd.isna(v) else v) for k, v in frow.iloc[0].to_dict().items()}
        result.update({k: v for k, v in extra.items() if k not in result})

    scores = _accessibility_scores_df()
    srow = scores[scores["province"] == region]
    if not srow.empty:
        result["accessibility_score"] = float(srow.iloc[0]["accessibility_score"])
        result["accessibility_class"] = srow.iloc[0]["accessibility_class"]

    return result


def get_region_roads(region: str, page: int = 1, page_size: int = 50) -> dict:
    return get_roads(page=page, page_size=page_size, province=region)


def get_region_geojson(region: str) -> Optional[dict]:
    _require_processed()
    slug = _slugify(region)
    path = GEOJSON_DIR / f"{slug}.geojson"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def get_geojson_manifest() -> list[dict]:
    _require_processed()
    path = GEOJSON_DIR / "_manifest.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def compare_regions(region_a: str, region_b: str) -> dict:
    a = get_region_summary(region_a)
    b = get_region_summary(region_b)
    if a is None or b is None:
        missing = region_a if a is None else region_b
        raise ValueError(f"Region '{missing}' not found in processed data.")
    return {"region_a": a, "region_b": b}
