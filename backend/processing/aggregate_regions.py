"""
Aggregation stage -- this is the PySpark stage of the pipeline.

`roads.parquet` is read into a Spark DataFrame and used to compute:
  - road-type distribution (national)
  - per-province road statistics (total length, count, avg length,
    major/local split, road-type breakdown)
  - overall national KPIs

PySpark is used here (rather than plain pandas) because this is the step
that scans and aggregates the full national road table, which is exactly
the kind of group-by/aggregate workload Spark is built for, and it keeps
the pipeline scalable if a future run uses the full multi-GB extract
across many provinces/road types.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import (  # noqa: E402
    MAJOR_ROAD_TYPES, OUTPUTS_DIR, OVERVIEW_JSON, PROVINCE_RANKINGS_JSON,
    PROVINCE_SUMMARY_PARQUET, ROAD_TYPE_DISTRIBUTION_JSON,
    ROAD_TYPE_SUMMARY_PARQUET, ROADS_PARQUET,
)
from app.utils.logging_utils import log  # noqa: E402


def _get_spark():
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName("IndonesiaRoadAggregation")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def run_aggregation():
    if not ROADS_PARQUET.exists():
        raise FileNotFoundError(
            f"{ROADS_PARQUET} not found. Run preprocessing before aggregation."
        )

    spark = _get_spark()
    from pyspark.sql import functions as F

    df = spark.read.parquet(str(ROADS_PARQUET))
    df = df.withColumn(
        "is_major",
        F.col("highway").isin(list(MAJOR_ROAD_TYPES)),
    )
    total_rows = df.count()
    log(f"    Loaded {total_rows:,} road records into Spark.")

    # --- National road-type distribution -----------------------------
    road_type_df = (
        df.groupBy("highway")
        .agg(
            F.count("*").alias("segment_count"),
            F.sum("length_m").alias("total_length_m"),
            F.avg("length_m").alias("avg_length_m"),
        )
        .orderBy(F.desc("total_length_m"))
    )
    road_type_pd = road_type_df.toPandas()
    road_type_pd.to_parquet(ROAD_TYPE_SUMMARY_PARQUET, index=False)

    # --- Per-province summary -----------------------------------------
    province_df = (
        df.groupBy("province")
        .agg(
            F.count("*").alias("segment_count"),
            F.sum("length_m").alias("total_length_m"),
            F.avg("length_m").alias("avg_length_m"),
            F.sum(F.when(F.col("is_major"), 1).otherwise(0)).alias("major_segment_count"),
            F.countDistinct("highway").alias("road_type_count"),
        )
        .orderBy(F.desc("total_length_m"))
    )
    province_pd = province_df.toPandas()
    province_pd["major_road_pct"] = (
        province_pd["major_segment_count"] / province_pd["segment_count"] * 100
    ).round(2)
    province_pd["total_length_km"] = (province_pd["total_length_m"] / 1000).round(2)
    province_pd.to_parquet(PROVINCE_SUMMARY_PARQUET, index=False)

    # --- Road type x province matrix (for stacked charts) -------------
    pivot_df = (
        df.groupBy("province", "highway")
        .agg(F.sum("length_m").alias("length_m"))
        .toPandas()
    )

    spark.stop()

    # --- National KPIs (outputs/overview.json) -------------------------
    total_length_km = float(province_pd["total_length_m"].sum() / 1000)
    total_segments = int(province_pd["segment_count"].sum())
    total_major = int(province_pd["major_segment_count"].sum())

    overview = {
        "total_road_segments": total_segments,
        "total_road_length_km": round(total_length_km, 2),
        "average_segment_length_m": round(
            float(province_pd["total_length_m"].sum() / max(total_segments, 1)), 2
        ),
        "number_of_provinces": int(province_pd[province_pd["province"] != "Unknown"]["province"].nunique()),
        "number_of_road_types": int(road_type_pd["highway"].nunique()),
        "major_road_percentage": round(total_major / max(total_segments, 1) * 100, 2),
    }
    OVERVIEW_JSON.write_text(json.dumps(overview, indent=2))

    # --- Top provinces by length (province_rankings.json) --------------
    rankings = {
        "by_total_length_km": province_pd.sort_values("total_length_m", ascending=False)
        .head(10)[["province", "total_length_km", "segment_count", "major_road_pct"]]
        .to_dict(orient="records"),
    }
    PROVINCE_RANKINGS_JSON.write_text(json.dumps(rankings, indent=2))

    # --- Road-type distribution json ------------------------------------
    ROAD_TYPE_DISTRIBUTION_JSON.write_text(
        json.dumps(road_type_pd.to_dict(orient="records"), indent=2)
    )

    log(f"    Saved province_summary.parquet ({len(province_pd)} provinces), "
        f"road_type_summary.parquet ({len(road_type_pd)} types).")
    log(f"    Saved overview.json, province_rankings.json, road_type_distribution.json.")

    return province_pd, road_type_pd, pivot_df, overview
