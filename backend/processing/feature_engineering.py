"""
Feature engineering + accessibility index stage.

Combines:
  - province_summary.parquet   (road totals, from PySpark aggregation)
  - graph_metrics.parquet      (per-province graph structure, from NetworkX)
  - province boundaries        (for area -> density calculations)

into `region_features.parquet`: one row per province with the feature
set used both for display (Road Infrastructure / Regional Comparison
pages) and as ML input features.

It then computes the composite accessibility index described in
`app/config.py::ACCESSIBILITY_WEIGHTS` and buckets it into Low/Medium/
High using `app/config.py::ACCESSIBILITY_THRESHOLDS`, saving
`accessibility_scores.parquet`.

Methodology note (also surfaced in the API/UI): because OSM provides no
official accessibility ground truth, this pipeline uses **Approach B**
from the project spec -- a transparent, explainable composite index
built from normalized road-network metrics, with configurable weights.
The ML stage (train_ml.py) then trains a supervised classifier to
reproduce/explain these index-derived classes, which is what makes the
model's predictions and feature importances meaningful and auditable.
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import (  # noqa: E402
    ACCESSIBILITY_SCORES_PARQUET, ACCESSIBILITY_WEIGHTS, GRAPH_METRICS_PARQUET,
    MAJOR_ROAD_TYPES, PROVINCE_SUMMARY_PARQUET, REGION_FEATURES_PARQUET,
    ROADS_PARQUET, accessibility_label,
)
from app.utils.geo_utils import min_max_normalize, polygon_area_km2  # noqa: E402
from app.utils.logging_utils import log  # noqa: E402


def _province_areas_km2(boundaries: gpd.GeoDataFrame | None) -> dict:
    if boundaries is None or boundaries.empty or "province" not in boundaries.columns:
        return {}
    areas = {}
    for _, row in boundaries.iterrows():
        areas[row["province"]] = polygon_area_km2(row.geometry)
    return areas


def build_region_features(boundaries: gpd.GeoDataFrame | None = None) -> pd.DataFrame:
    province_summary = pd.read_parquet(PROVINCE_SUMMARY_PARQUET)
    roads = pd.read_parquet(ROADS_PARQUET)

    graph_metrics = (
        pd.read_parquet(GRAPH_METRICS_PARQUET)
        if GRAPH_METRICS_PARQUET.exists() else pd.DataFrame()
    )

    areas = _province_areas_km2(boundaries)

    sums = roads.groupby(["province", "highway"])["length_m"].sum()
    totals = sums.groupby(level=0).transform("sum")
    highway_pct = (sums / totals * 100).rename("pct").reset_index()
    
    pct_pivot = highway_pct.pivot(index="province", columns="highway", values="pct").fillna(0)
    pct_pivot.columns = [f"{c}_pct" for c in pct_pivot.columns]
    pct_pivot = pct_pivot.reset_index()

    features = province_summary.merge(pct_pivot, on="province", how="left")
    if not graph_metrics.empty:
        features = features.merge(
            graph_metrics[["province", "nodes", "edges", "avg_degree",
                            "connected_components", "largest_component_size",
                            "network_density", "dead_end_nodes"]],
            on="province", how="left",
        )
    else:
        for col in ["nodes", "edges", "avg_degree", "connected_components",
                    "largest_component_size", "network_density", "dead_end_nodes"]:
            features[col] = 0.0

    features["area_km2"] = features["province"].map(areas).fillna(pd.NA)
    features["road_density_km_per_km2"] = (
        features["total_length_km"] / features["area_km2"]
    )
    features["intersection_density_per_km2"] = (
        features["nodes"] / features["area_km2"]
    )
    # Where area is unavailable, density columns will be NaN -- handled
    # downstream (normalization treats NaN as 0 after fillna).
    features["road_density_km_per_km2"] = features["road_density_km_per_km2"].fillna(0)
    features["intersection_density_per_km2"] = features["intersection_density_per_km2"].fillna(0)

    features["major_road_ratio"] = features["major_road_pct"] / 100.0
    features["residential_pct"] = features.get("residential_pct", 0.0)

    features = features[features["province"] != "Unknown"].reset_index(drop=True)
    features.to_parquet(REGION_FEATURES_PARQUET, index=False)
    log(f"    Saved region_features.parquet ({len(features)} provinces).")
    return features


def compute_accessibility_index(features: pd.DataFrame) -> pd.DataFrame:
    df = features.copy()

    df["road_density_norm"] = min_max_normalize(df["road_density_km_per_km2"])
    df["intersection_density_norm"] = min_max_normalize(df["intersection_density_per_km2"])
    df["major_road_ratio_norm"] = min_max_normalize(df["major_road_ratio"])
    df["network_density_norm"] = min_max_normalize(df["network_density"].fillna(0))
    df["avg_degree_norm"] = min_max_normalize(df["avg_degree"].fillna(0))

    df["accessibility_score"] = sum(
        df[col] * weight for col, weight in ACCESSIBILITY_WEIGHTS.items()
    ) * 100
    df["accessibility_score"] = df["accessibility_score"].round(2)
    df["accessibility_class"] = df["accessibility_score"].apply(accessibility_label)

    out = df[[
        "province", "accessibility_score", "accessibility_class",
        "road_density_norm", "intersection_density_norm",
        "major_road_ratio_norm", "network_density_norm", "avg_degree_norm",
    ]].sort_values("accessibility_score", ascending=False).reset_index(drop=True)

    out.to_parquet(ACCESSIBILITY_SCORES_PARQUET, index=False)
    log(f"    Saved accessibility_scores.parquet ({len(out)} provinces). "
        f"Class distribution: {out['accessibility_class'].value_counts().to_dict()}")
    return out
