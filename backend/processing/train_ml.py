"""
Machine learning stage.

Methodology (Approach B from the project spec): since OpenStreetMap has
no official accessibility ground truth, we do NOT invent labels. Instead:

  1. `feature_engineering.py` computes a transparent composite
     accessibility index from normalized road-network metrics
     (see `app/config.py::ACCESSIBILITY_WEIGHTS`), and buckets it into
     Low / Medium / High classes with configurable thresholds.
  2. This stage trains a supervised classifier (Random Forest by default)
     to REPRODUCE those index-derived classes from the underlying raw
     features (road density, intersection density, road-type mix, graph
     metrics, etc.) -- NOT from the index itself.

The point of training a classifier on the raw features (rather than just
using the index directly) is that it yields feature importances: which
underlying network characteristics best explain accessibility class
membership, and a reusable model that generalizes the scoring
methodology to future/partial data. Because Indonesia has 34 provinces,
this is a small-N classification problem -- the metrics reported here
should be read as diagnostic of the index's internal consistency, not
as a claim of large-sample statistical power. This caveat is surfaced
in `ml_metrics.json` and displayed in the UI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import (  # noqa: E402
    ACCESSIBILITY_MODEL_PKL, ACCESSIBILITY_SCORES_PARQUET,
    FEATURE_IMPORTANCE_JSON, ML_METRICS_JSON, REGION_FEATURES_PARQUET,
)
from app.utils.logging_utils import log  # noqa: E402

FEATURE_COLUMNS = [
    "road_density_km_per_km2", "intersection_density_per_km2",
    "total_length_km", "avg_length_m", "major_road_pct",
    "avg_degree", "network_density", "connected_components",
    "dead_end_nodes", "population_density_bps",
]

CLASS_ORDER = ["Low", "Medium", "High"]


def _select_available_features(df: pd.DataFrame) -> list[str]:
    return [c for c in FEATURE_COLUMNS if c in df.columns]


def train_and_evaluate():
    features = pd.read_parquet(REGION_FEATURES_PARQUET)
    scores = pd.read_parquet(ACCESSIBILITY_SCORES_PARQUET)

    data = features.merge(scores[["province", "accessibility_score", "accessibility_class"]],
                           on="province", how="inner")
    feature_cols = _select_available_features(data)
    data = data.dropna(subset=feature_cols + ["accessibility_class"])

    n = len(data)
    log(f"    Training on {n} province records with {len(feature_cols)} features.")

    class_counts = data["accessibility_class"].value_counts()
    min_class_count = int(class_counts.min()) if len(class_counts) > 0 else 0
    can_stratify = min_class_count >= 2 and data["accessibility_class"].nunique() > 1

    if n < 6:
        log("    WARNING: too few provinces to hold out a meaningful test set; "
            "training on all available data and reporting in-sample metrics only. "
            "This is expected for small development-mode extracts, not the full "
            "national dataset.")
        X_train = X_test = data[feature_cols]
        y_train = y_test = data["accessibility_class"]
    elif not can_stratify:
        log(f"    WARNING: accessibility class distribution is too imbalanced to "
            f"stratify safely ({class_counts.to_dict()} -- at least one class has "
            f"fewer than 2 members). Using a plain (non-stratified) train/test "
            f"split instead. With this few examples of the minority class(es), "
            f"treat per-class precision/recall for High/Medium as illustrative "
            f"rather than statistically reliable -- consider revisiting the "
            f"ACCESSIBILITY_THRESHOLDS in app/config.py if this imbalance seems "
            f"too extreme for your analysis.")
        X_train, X_test, y_train, y_test = train_test_split(
            data[feature_cols], data["accessibility_class"],
            test_size=0.3, random_state=42,
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            data[feature_cols], data["accessibility_class"],
            test_size=0.3, random_state=42,
            stratify=data["accessibility_class"],
        )

    model = RandomForestClassifier(
        n_estimators=200, max_depth=6, random_state=42, class_weight="balanced"
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    labels_present = sorted(set(y_test) | set(y_pred), key=lambda c: CLASS_ORDER.index(c) if c in CLASS_ORDER else 99)

    metrics = {
        "algorithm": "RandomForestClassifier",
        "methodology": (
            "Supervised classifier trained to reproduce classes derived from a "
            "transparent composite accessibility index (not official ground "
            "truth). See ACCESSIBILITY_WEIGHTS in app/config.py."
        ),
        "n_provinces_total": int(n),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision_macro": round(float(precision_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "class_labels": labels_present,
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=labels_present).tolist(),
        "class_distribution": data["accessibility_class"].value_counts().to_dict(),
    }
    ML_METRICS_JSON.write_text(json.dumps(metrics, indent=2))

    importances = dict(zip(feature_cols, model.feature_importances_.tolist()))
    importances = dict(sorted(importances.items(), key=lambda kv: kv[1], reverse=True))
    FEATURE_IMPORTANCE_JSON.write_text(json.dumps(
        [{"feature": k, "importance": round(v, 4)} for k, v in importances.items()],
        indent=2,
    ))

    joblib.dump({"model": model, "feature_columns": feature_cols}, ACCESSIBILITY_MODEL_PKL)

    # Predictions table for every province (province ranking + predicted class)
    data["predicted_class"] = model.predict(data[feature_cols])
    predictions = data[["province", "accessibility_score", "accessibility_class",
                         "predicted_class"] + feature_cols].sort_values(
        "accessibility_score", ascending=False
    )
    predictions.to_parquet(Path(REGION_FEATURES_PARQUET).parent / "ml_predictions.parquet", index=False)

    log(f"    Model trained. Accuracy={metrics['accuracy']}, F1(macro)={metrics['f1_macro']}.")
    log(f"    Saved ml_metrics.json, feature_importance.json, accessibility_model.pkl, "
        f"ml_predictions.parquet.")

    return metrics, importances, predictions