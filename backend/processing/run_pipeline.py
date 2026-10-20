"""
Master processing pipeline.

Usage:
    python processing/run_pipeline.py --sample   # fast dev-mode (Jakarta bbox)
    python processing/run_pipeline.py --full     # full Indonesia extract

Executes all 13 stages described in the project spec, printing progress
as it goes, and writes `outputs/pipeline_status.json` so the API/frontend
can tell whether (and how) the dataset has been processed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import (  # noqa: E402
    PIPELINE_STATUS_JSON, RAW_PBF_FILE, REGION_FEATURES_PARQUET, ROADS_PARQUET,
)
from app.utils.logging_utils import log, stage, timed  # noqa: E402

TOTAL_STAGES = 13


def main():
    parser = argparse.ArgumentParser(description="Indonesia OSM road infrastructure pipeline")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--sample", action="store_true",
                       help="Development mode: process a small Jakarta-area subset only.")
    mode.add_argument("--full", action="store_true",
                       help="Full mode: process the entire indonesia-latest.osm.pbf.")
    parser.add_argument("--resume", action="store_true",
                        help="Skip extraction and preprocessing (stages 1-6) if "
                             "data/processed/roads.parquet already exists, and go "
                             "straight to aggregation/graph/ML/geojson (stages 7-13). "
                             "Use this to avoid re-paying the ~10 minute extraction+"
                             "preprocessing cost when only resuming/re-running the "
                             "later stages (e.g. after graph analytics was interrupted).")
    args = parser.parse_args()

    sample_mode = args.sample or not args.full  # default to sample if neither given
    if sample_mode and not args.sample and not args.resume:
        log("No mode flag given -- defaulting to --sample (fast dev mode). "
            "Use --full to process the entire national dataset.")

    run_start = time.time()
    log("=" * 70)
    log(f"Indonesia Road Infrastructure Pipeline -- mode: "
        f"{'RESUME' if args.resume else ('SAMPLE (dev)' if sample_mode else 'FULL (national)')}")
    log("=" * 70)

    import pandas as pd

    if args.resume and ROADS_PARQUET.exists():
        stage(1, TOTAL_STAGES, "Resuming: skipping extraction/preprocessing (--resume)...")
        from processing.preprocess import load_boundaries
        roads_df = pd.read_parquet(ROADS_PARQUET)
        boundaries = load_boundaries(None)  # loads the fallback GeoJSON from disk, if present
        log(f"    Loaded {len(roads_df):,} previously-processed road records from "
            f"{ROADS_PARQUET.name}.")
        log(f"    Loaded province boundaries: "
            f"{'none (densities will be 0)' if boundaries is None else f'{len(boundaries)} provinces'}.")
        for s in range(2, 7):
            log(f"[{s}/{TOTAL_STAGES}] (skipped -- using existing roads.parquet)")
    else:
        if args.resume:
            log(f"--resume requested but {ROADS_PARQUET} does not exist yet. "
                f"Running the full extraction/preprocessing stages first.")

        # ---- Stage 1: validate raw file ------------------------------------
        stage(1, TOTAL_STAGES, "Checking raw OSM file...")
        from processing.extract_osm import validate_raw_file
        validate_raw_file()

        # ---- Stage 2: extract roads + boundaries ---------------------------
        stage(2, TOTAL_STAGES, "Extracting roads and administrative boundaries...")
        from processing.extract_osm import extract_roads_and_boundaries
        with timed("extraction"):
            raw_roads, raw_boundaries = extract_roads_and_boundaries(RAW_PBF_FILE, sample=sample_mode)

        if len(raw_roads) == 0:
            log("No roads extracted. Check that the PBF file is valid and covers Indonesia.")
            sys.exit(1)

        # ---- Stage 3-6: clean, geometry/length, province join, save --------
        stage(3, TOTAL_STAGES, "Cleaning road records...")
        stage(4, TOTAL_STAGES, "Calculating geometry / road length...")
        stage(5, TOTAL_STAGES, "Extracting administrative region information (province join)...")
        stage(6, TOTAL_STAGES, "Saving processed Parquet (roads, nodes)...")
        from processing.preprocess import run_preprocessing
        with timed("preprocessing"):
            roads_gdf, nodes_df, boundaries = run_preprocessing(raw_roads, raw_boundaries)

        # roads_gdf still has geometry; build a plain DataFrame w/ WKT for
        # downstream stages that don't need a GeoDataFrame.
        roads_df = roads_gdf.drop(columns=["geometry"]).copy()
        roads_df["geometry_wkt"] = roads_gdf.geometry.apply(lambda g: g.wkt)

    # ---- Stage 7: aggregate province statistics (PySpark) ---------------
    stage(7, TOTAL_STAGES, "Aggregating province statistics (PySpark)...")
    from processing.aggregate_regions import run_aggregation
    with timed("Spark aggregation"):
        province_summary, road_type_summary, pivot_df, overview = run_aggregation()

    # ---- Stage 11 done early: Graph analytics needed for features ------
    stage(8, TOTAL_STAGES, "Running graph analytics (NetworkX, per province)...")
    from processing.graph_analysis import run_graph_analysis
    with timed("graph analysis"):
        graph_metrics, top_nodes = run_graph_analysis(roads_df)

    # ---- Stage 8-9: ML features + accessibility index -------------------
    stage(9, TOTAL_STAGES, "Creating ML features...")
    from processing.feature_engineering import build_region_features, compute_accessibility_index
    with timed("feature engineering"):
        region_features = build_region_features(boundaries)

    with timed("demographic join (BPS population, second dataset)"):
        from processing.demographic_join import join_demographics
        region_features = join_demographics(region_features)
        # Overwrite region_features.parquet so population columns flow
        # through to accessibility scoring, ML training, and the API.
        region_features.to_parquet(REGION_FEATURES_PARQUET, index=False)

    stage(10, TOTAL_STAGES, "Calculating accessibility scores...")
    with timed("accessibility index"):
        accessibility_scores = compute_accessibility_index(region_features)

    # ---- Stage 10: train/evaluate ML -------------------------------------
    stage(11, TOTAL_STAGES, "Training/evaluating ML model...")
    from processing.train_ml import train_and_evaluate
    with timed("ML training"):
        ml_metrics, feature_importance, predictions = train_and_evaluate()

    # ---- Stage 12: simplified GeoJSON ------------------------------------
    stage(12, TOTAL_STAGES, "Creating simplified GeoJSON for the map...")
    from processing.export_geojson import export_province_geojson
    with timed("GeoJSON export"):
        manifest = export_province_geojson(roads_df)

    # ---- Stage 13: status / dashboard outputs -----------------------------
    stage(13, TOTAL_STAGES, "Saving dashboard output datasets & pipeline status...")
    elapsed = time.time() - run_start

    # Preserve the original extraction mode (sample/full) across --resume
    # runs, since resuming doesn't re-run extraction and therefore doesn't
    # know which mode originally produced roads.parquet.
    resolved_mode = "sample" if sample_mode else "full"
    if args.resume and PIPELINE_STATUS_JSON.exists():
        try:
            prev_status = json.loads(PIPELINE_STATUS_JSON.read_text())
            resolved_mode = prev_status.get("mode", resolved_mode)
        except Exception:
            pass

    status = {
        "processed": True,
        "mode": resolved_mode,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "raw_file": str(RAW_PBF_FILE),
        "raw_file_size_mb": round(RAW_PBF_FILE.stat().st_size / (1024 * 1024), 1) if RAW_PBF_FILE.exists() else None,
        "road_records_extracted": int(len(roads_df)),
        "provinces_detected": int(province_summary["province"].nunique()),
        "note": (
            "DEVELOPMENT / SAMPLE MODE -- results only cover a small Jakarta-area "
            "subset and MUST NOT be presented as final Indonesia results."
        ) if resolved_mode == "sample" else None,
    }
    PIPELINE_STATUS_JSON.write_text(json.dumps(status, indent=2))

    log("=" * 70)
    log(f"[13/13] Processing complete in {elapsed:.1f}s "
        f"({resolved_mode.upper()} MODE{', RESUMED' if args.resume else ''}).")
    log("=" * 70)


if __name__ == "__main__":
    main()