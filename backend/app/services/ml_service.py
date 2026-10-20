"""Service layer exposing ML training results (Page 5 - Machine Learning)."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from app.config import (
    FEATURE_IMPORTANCE_JSON, ML_METRICS_JSON, PROCESSED_DIR,
)
from app.services.data_service import NotProcessedError, is_processed

PREDICTIONS_PARQUET = PROCESSED_DIR / "ml_predictions.parquet"


def _require():
    if not (is_processed() and ML_METRICS_JSON.exists()):
        raise NotProcessedError(
            "ML results not available yet. Run the processing pipeline "
            "(`python processing/run_pipeline.py`) to train the accessibility model."
        )


def get_ml_metrics() -> dict:
    _require()
    return json.loads(ML_METRICS_JSON.read_text())


def get_feature_importance() -> list[dict]:
    _require()
    if not FEATURE_IMPORTANCE_JSON.exists():
        return []
    return json.loads(FEATURE_IMPORTANCE_JSON.read_text())


@lru_cache(maxsize=1)
def _predictions_df() -> pd.DataFrame:
    _require()
    if not PREDICTIONS_PARQUET.exists():
        return pd.DataFrame()
    return pd.read_parquet(PREDICTIONS_PARQUET)


def get_predictions() -> list[dict]:
    df = _predictions_df()
    if df.empty:
        return []
    df = df.copy()
    df = df[[c for c in [
        "province", "accessibility_score", "accessibility_class", "predicted_class"
    ] if c in df.columns]]
    return df.to_dict(orient="records")


def clear_cache():
    _predictions_df.cache_clear()
