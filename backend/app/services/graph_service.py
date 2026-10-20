"""Service layer exposing NetworkX graph analytics results (Page 6)."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from app.config import GRAPH_METRICS_PARQUET, GRAPH_NODE_CENTRALITY_PARQUET, GRAPH_SUMMARY_JSON
from app.services.data_service import NotProcessedError, is_processed


def _require():
    if not (is_processed() and GRAPH_METRICS_PARQUET.exists()):
        raise NotProcessedError(
            "Graph analytics not available yet. Run the processing pipeline "
            "(`python processing/run_pipeline.py`) to compute graph metrics."
        )


@lru_cache(maxsize=1)
def _graph_metrics_df() -> pd.DataFrame:
    _require()
    return pd.read_parquet(GRAPH_METRICS_PARQUET)


@lru_cache(maxsize=1)
def _centrality_df() -> pd.DataFrame:
    _require()
    return pd.read_parquet(GRAPH_NODE_CENTRALITY_PARQUET)


def get_national_graph_summary() -> dict:
    _require()
    if not GRAPH_SUMMARY_JSON.exists():
        return {}
    return json.loads(GRAPH_SUMMARY_JSON.read_text())


def get_region_graph_summary(region: str) -> dict | None:
    df = _graph_metrics_df()
    row = df[df["province"] == region]
    if row.empty:
        return None
    return {k: (None if pd.isna(v) else v) for k, v in row.iloc[0].to_dict().items()}


def get_region_centrality(region: str, limit: int = 10) -> list[dict]:
    df = _centrality_df()
    sub = df[df["province"] == region].sort_values("betweenness_centrality", ascending=False)
    return sub.head(limit).to_dict(orient="records")


def get_region_nodes(region: str, limit: int = 200) -> list[dict]:
    df = _centrality_df()
    sub = df[df["province"] == region].sort_values("degree_centrality", ascending=False)
    return sub.head(limit).to_dict(orient="records")


def get_degree_distribution(region: str) -> list[dict]:
    df = _centrality_df()
    sub = df[df["province"] == region]
    if sub.empty:
        return []
    dist = sub["degree"].value_counts().sort_index()
    return [{"degree": int(k), "count": int(v)} for k, v in dist.items()]


def get_all_province_graph_metrics() -> list[dict]:
    df = _graph_metrics_df()
    return df.to_dict(orient="records")


def clear_cache():
    _graph_metrics_df.cache_clear()
    _centrality_df.cache_clear()
