"""
Demographic join stage (second dataset add-on).

Merges BPS (Badan Pusat Statistik / Statistics Indonesia) population data
into region_features.parquet, producing per-capita metrics like road
length per 1,000 people. This is a genuinely separate dataset from
OpenStreetMap -- official government tabular statistics vs.
community-mapped geospatial data -- which is what gives this project
real Variety (different data types/sources) and Veracity (cross-
referencing an authoritative source against crowd-sourced data) beyond
OSM alone.

Because this project's province boundaries come from a community-
maintained OSM boundary source (see preprocess.py) that predates
Indonesia's 2022 Papua province split, matching by province name is
imperfect for a handful of provinces. Unmatched provinces get
population = null rather than a guessed value -- this is intentional
and documented on the About Dataset page, not a bug to hide.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import (  # noqa: E402
    DEMOGRAPHICS_PARQUET, POPULATION_CSV_PATH, PROVINCE_NAME_MAP_TO_BPS,
    REGION_FEATURES_PARQUET,
)
from app.utils.logging_utils import log  # noqa: E402

BPS_COLUMN_MAP = {
    "Provinsi": "province_bps",
    "Jumlah Penduduk (Ribu)": "population_thousands",
    "Laju Pertumbuhan Penduduk per Tahun": "population_growth_rate_pct",
    "Persentase Penduduk": "population_share_pct",
    "Kepadatan Penduduk per km persegi (Km2)": "population_density_bps",
    "Rasio Jenis Kelamin Penduduk": "sex_ratio",
}


def load_population_data() -> pd.DataFrame:
    if not POPULATION_CSV_PATH.exists():
        log(f"    Population CSV not found at {POPULATION_CSV_PATH}; "
            f"skipping demographic join.")
        return pd.DataFrame()

    df = pd.read_csv(POPULATION_CSV_PATH, encoding="utf-8-sig")
    df = df.rename(columns=BPS_COLUMN_MAP)

    df = df.dropna(subset=["province_bps"])
    df = df[df["province_bps"] != "Indonesia"]
    df = df[df["province_bps"] != "Keterangan"]
    df = df[~df["province_bps"].astype(str).str.match(r"^\d")]

    df["population"] = (df["population_thousands"].astype(float) * 1000).round(0)
    log(f"    Loaded {len(df)} province population records from "
        f"{POPULATION_CSV_PATH.name}.")
    return df


def join_demographics(region_features: pd.DataFrame) -> pd.DataFrame:
    pop_df = load_population_data()
    merged = region_features.copy()

    if pop_df.empty:
        merged["population"] = pd.NA
        merged["population_density_bps"] = pd.NA
        merged["population_growth_rate_pct"] = pd.NA
        merged["sex_ratio"] = pd.NA
        merged["road_km_per_1000_people"] = pd.NA
        merged.to_parquet(DEMOGRAPHICS_PARQUET, index=False)
        return merged

    def _bps_name(osm_province: str) -> str:
        return PROVINCE_NAME_MAP_TO_BPS.get(osm_province, osm_province)

    merged["_bps_join_name"] = merged["province"].apply(_bps_name).str.strip().str.lower()
    pop_df["_bps_join_name"] = pop_df["province_bps"].str.strip().str.lower()

    merged = merged.merge(
        pop_df[["_bps_join_name", "population", "population_density_bps",
                "population_growth_rate_pct", "sex_ratio"]],
        on="_bps_join_name", how="left",
    )
    merged = merged.drop(columns=["_bps_join_name"])

    unmatched = merged[merged["population"].isna()]["province"].tolist()
    if unmatched:
        log(f"    WARNING: no BPS population match for {len(unmatched)} province(s): "
            f"{unmatched}. Population will show as unavailable (null) for these -- "
            f"see About Dataset for why (Indonesia's 2022 Papua province split vs. "
            f"this project's OSM boundary source).")

    merged["road_km_per_1000_people"] = (
        merged["total_length_km"] / (merged["population"] / 1000)
    ).round(2)

    merged.to_parquet(DEMOGRAPHICS_PARQUET, index=False)
    matched = merged["population"].notna().sum()
    log(f"    Saved demographics.parquet -- {matched}/{len(merged)} provinces "
        f"successfully matched with population data.")
    return merged


if __name__ == "__main__":
    features = pd.read_parquet(REGION_FEATURES_PARQUET)
    result = join_demographics(features)
    cols = ["province", "population", "total_length_km", "road_km_per_1000_people"]
    print(result[cols].sort_values("population", ascending=False).to_string(index=False))