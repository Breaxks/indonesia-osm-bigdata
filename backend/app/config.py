"""
Central configuration for the Indonesia OSM Big Data backend.

All paths, thresholds, and tunable parameters live here so that the
processing pipeline and the FastAPI app always agree on where data lives.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
GEOJSON_DIR = DATA_DIR / "geojson"
MODELS_DIR = DATA_DIR / "models"
OUTPUTS_DIR = DATA_DIR / "outputs"

RAW_PBF_FILE = RAW_DIR / "indonesia-latest.osm.pbf"

for d in (RAW_DIR, PROCESSED_DIR, GEOJSON_DIR, MODELS_DIR, OUTPUTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Processed artifact file paths (kept in one place so pipeline + API agree)
ROADS_PARQUET = PROCESSED_DIR / "roads.parquet"
NODES_PARQUET = PROCESSED_DIR / "nodes.parquet"
PROVINCE_SUMMARY_PARQUET = PROCESSED_DIR / "province_summary.parquet"
ROAD_TYPE_SUMMARY_PARQUET = PROCESSED_DIR / "road_type_summary.parquet"
REGION_FEATURES_PARQUET = PROCESSED_DIR / "region_features.parquet"
ACCESSIBILITY_SCORES_PARQUET = PROCESSED_DIR / "accessibility_scores.parquet"
GRAPH_METRICS_PARQUET = PROCESSED_DIR / "graph_metrics.parquet"
GRAPH_NODE_CENTRALITY_PARQUET = PROCESSED_DIR / "graph_node_centrality.parquet"

OVERVIEW_JSON = OUTPUTS_DIR / "overview.json"
PROVINCE_RANKINGS_JSON = OUTPUTS_DIR / "province_rankings.json"
ROAD_TYPE_DISTRIBUTION_JSON = OUTPUTS_DIR / "road_type_distribution.json"
ML_METRICS_JSON = OUTPUTS_DIR / "ml_metrics.json"
FEATURE_IMPORTANCE_JSON = OUTPUTS_DIR / "feature_importance.json"
GRAPH_SUMMARY_JSON = OUTPUTS_DIR / "graph_summary.json"
PIPELINE_STATUS_JSON = OUTPUTS_DIR / "pipeline_status.json"

ACCESSIBILITY_MODEL_PKL = MODELS_DIR / "accessibility_model.pkl"

# ---------------------------------------------------------------------------
# Highway categories considered "the road network" for this project.
# Anything not in this list is ignored during extraction to save memory.
# ---------------------------------------------------------------------------
RELEVANT_HIGHWAY_TYPES = [
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "residential", "service",
    "unclassified", "living_street",
]

MAJOR_ROAD_TYPES = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
}

# ---------------------------------------------------------------------------
# Accessibility index configuration.
#
# The composite score is a weighted sum of min-max normalized regional
# metrics. Weights sum to 1.0. They are intentionally isolated here so
# they can be tuned without touching pipeline logic, and so the
# methodology is transparent and reviewable.
#
# Rationale for weights:
#  - road_density (0.25): more road per km^2 generally indicates denser,
#    more accessible infrastructure.
#  - intersection_density (0.20): more intersections per km^2 indicates a
#    finer-grained, more connected street grid.
#  - major_road_ratio (0.20): a higher share of primary/secondary/trunk
#    roads suggests stronger inter-regional connectivity.
#  - network_density (0.15): graph-theoretic density of the road graph.
#  - avg_degree (0.20): average node degree approximates how well
#    connected individual intersections are on average.
# ---------------------------------------------------------------------------
ACCESSIBILITY_WEIGHTS = {
    "road_density_norm": 0.25,
    "intersection_density_norm": 0.20,
    "major_road_ratio_norm": 0.20,
    "network_density_norm": 0.15,
    "avg_degree_norm": 0.20,
}

# Score thresholds (0-100 scale), configurable.
ACCESSIBILITY_THRESHOLDS = {
    "low_max": 39,
    "medium_max": 69,
    # 70-100 => High
}

def accessibility_label(score: float) -> str:
    if score <= ACCESSIBILITY_THRESHOLDS["low_max"]:
        return "Low"
    if score <= ACCESSIBILITY_THRESHOLDS["medium_max"]:
        return "Medium"
    return "High"

# ---------------------------------------------------------------------------
# Big-graph safety limits (see PAGE 6 / graph_analysis.py).
# Betweenness centrality is O(V*E) and unreasonable nationwide, so it is
# only computed at province/city scale, and only exactly below this node
# count -- above it, an approximate (k-sampled) betweenness is used.
# ---------------------------------------------------------------------------
EXACT_BETWEENNESS_NODE_LIMIT = 3000
APPROX_BETWEENNESS_SAMPLE_K = 500

# ---------------------------------------------------------------------------
# Demographic (BPS population) join -- optional second dataset.
# See processing/demographic_join.py.
# ---------------------------------------------------------------------------
POPULATION_CSV_PATH = RAW_DIR / "population_bps_2026.csv"
DEMOGRAPHICS_PARQUET = PROCESSED_DIR / "demographics.parquet"

# Maps this project's OSM-derived province names (left) to the BPS
# population CSV's province names (right), only where they differ.
# Provinces not listed here are matched by exact (case-insensitive) name.
#
# Some OSM provinces use old, pre-2022 Papua-region naming (this project's
# community-maintained boundary source predates Indonesia's 2022 Papua
# province split into 6 provinces). Where a reasonable historical
# equivalent exists it is mapped below; "Irian Jaya Timur" has no safe
# 1:1 equivalent among the current Papua/Papua Selatan/Papua Pegunungan
# split and is intentionally left unmapped rather than guessed --
# population will show as unavailable (null) for it, not a wrong number.
PROVINCE_NAME_MAP_TO_BPS = {
    "Dki Jakarta": "DKI Jakarta",
    "Probanten": "Banten",
    "Daerah Istimewa Yogyakarta": "DI Yogyakarta",
    "Di. Aceh": "Aceh",
    "Nusatenggara Barat": "Nusa Tenggara Barat",
    "Bangka Belitung": "Kepulauan Bangka Belitung",
    "Irian Jaya Barat": "Papua Barat",
    "Irian Jaya Tengah": "Papua Tengah",
}

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
API_TITLE = "Indonesia Road Infrastructure & Accessibility API"
API_VERSION = "1.0.0"

CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
