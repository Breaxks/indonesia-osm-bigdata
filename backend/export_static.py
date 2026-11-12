"""
export_static.py -- turn your finished pipeline results into plain JSON files.

Why: GitHub Pages can only host static files (no Python server). Instead of
the dashboard asking FastAPI for data, it will read the JSON files this
script writes into  frontend/public/data/.

How to run (from the backend folder, with your venv activated):

    python export_static.py

Optional knobs (defaults are fine to start with):

    --roads-per-province 1000     longest N roads kept per province (Data Explorer)
    --roads-national 3000         longest N roads kept nationwide (Data Explorer)
    --minor-roads-per-province 6000   cap on small roads per province map file
    --coord-decimals 5            rounding of map coordinates (5 = ~1 metre)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import GEOJSON_DIR, MAJOR_ROAD_TYPES  # noqa: E402
from app.services import data_service, graph_service, ml_service  # noqa: E402


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def slugify(name: str) -> str:
    """Must match slugify() in frontend/src/services/api.js and the backend."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def clean(o):
    """Make anything JSON-safe: numpy -> python, NaN/inf -> None."""
    if o is pd.NA or o is pd.NaT:
        return None
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean(obj), separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )


def step(title: str, fn) -> None:
    """Run one export step; a failure in one step won't stop the others."""
    print(f"-> {title}")
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        print(f"   !! SKIPPED ({type(exc).__name__}: {exc})")


def round_coords(c, nd):
    if isinstance(c, (int, float)):
        return round(c, nd)
    return [round_coords(x, nd) for x in c]


# ----------------------------------------------------------------------------
# export pieces
# ----------------------------------------------------------------------------
def export_overview(out: Path, provinces: list[str]) -> None:
    write(out / "pipeline_status.json", data_service.get_pipeline_status())
    write(out / "overview.json", data_service.get_overview())
    write(out / "provinces.json", provinces)
    write(out / "road_types.json", data_service.get_road_types())
    write(out / "province_rankings.json", data_service.get_province_rankings())
    write(out / "road_type_distribution.json", data_service.get_road_type_distribution())
    write(out / "top_density.json", data_service.get_top_provinces_by_density(limit=100))
    write(out / "top_per_capita.json", data_service.get_top_provinces_by_road_per_capita(limit=100))


def export_regions(out: Path, provinces: list[str]) -> None:
    for p in provinces:
        s = data_service.get_region_summary(p)
        if s is not None:
            write(out / "regions" / slugify(p) / "summary.json", s)


def export_roads(out: Path, provinces: list[str], per_province: int, national: int) -> None:
    top = data_service.get_roads(page=1, page_size=national)
    write(out / "roads" / "_top.json", top["items"])
    for p in provinces:
        r = data_service.get_roads(page=1, page_size=per_province, province=p)
        write(out / "roads" / f"{slugify(p)}.json", r["items"])


def export_geojson(out: Path, minor_cap: int, decimals: int) -> None:
    manifest_path = GEOJSON_DIR / "_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} not found - did the pipeline's GeoJSON stage run?")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    new_manifest = []
    rng = random.Random(42)
    for m in manifest:
        src = GEOJSON_DIR / f"{m['slug']}.geojson"
        if not src.exists():
            continue
        fc = json.loads(src.read_text(encoding="utf-8"))
        feats = fc.get("features", [])
        major = [f for f in feats if f.get("properties", {}).get("highway") in MAJOR_ROAD_TYPES]
        minor = [f for f in feats if f.get("properties", {}).get("highway") not in MAJOR_ROAD_TYPES]
        if len(minor) > minor_cap:
            minor = rng.sample(minor, minor_cap)
        feats = major + minor
        for f in feats:
            geom = f.get("geometry")
            if geom and "coordinates" in geom:
                geom["coordinates"] = round_coords(geom["coordinates"], decimals)
        fc["features"] = feats
        write(out / "geojson" / f"{m['slug']}.geojson", fc)
        new_manifest.append({**m, "feature_count": len(feats)})
    write(out / "geojson" / "_manifest.json", new_manifest)


def export_ml(out: Path) -> None:
    write(out / "ml" / "metrics.json", ml_service.get_ml_metrics())
    write(out / "ml" / "feature_importance.json", ml_service.get_feature_importance())
    write(out / "ml" / "predictions.json", ml_service.get_predictions())


def export_graph(out: Path) -> None:
    write(out / "graph" / "summary.json", graph_service.get_national_graph_summary())
    metrics = graph_service.get_all_province_graph_metrics()
    write(out / "graph" / "provinces.json", metrics)
    for row in metrics:
        p = row["province"]
        base = out / "graph" / slugify(p)
        write(base / "summary.json", graph_service.get_region_graph_summary(p))
        write(base / "centrality.json", graph_service.get_region_centrality(p, limit=20))
        write(base / "nodes.json", graph_service.get_region_nodes(p, limit=200))
        write(base / "degree_distribution.json", graph_service.get_degree_distribution(p))


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=BACKEND_DIR.parent / "frontend" / "public" / "data")
    ap.add_argument("--roads-per-province", type=int, default=1000)
    ap.add_argument("--roads-national", type=int, default=3000)
    ap.add_argument("--minor-roads-per-province", type=int, default=6000)
    ap.add_argument("--coord-decimals", type=int, default=5)
    args = ap.parse_args()
    out: Path = args.out

    if not data_service.is_processed():
        sys.exit("Pipeline results not found. Run:  python processing/run_pipeline.py --full   first.")

    if out.exists() and out.name == "data":
        shutil.rmtree(out)  # start clean so old files never linger
    out.mkdir(parents=True, exist_ok=True)

    provinces = data_service.get_provinces()
    print(f"Exporting {len(provinces)} provinces to {out}\n")

    step("overview, rankings, lists", lambda: export_overview(out, provinces))
    step("province summaries", lambda: export_regions(out, provinces))
    step("roads sample (Data Explorer)", lambda: export_roads(out, provinces, args.roads_per_province, args.roads_national))
    step("map GeoJSON (this one is slow)", lambda: export_geojson(out, args.minor_roads_per_province, args.coord_decimals))
    step("machine learning results", lambda: export_ml(out))
    step("graph analytics", lambda: export_graph(out))

    files = [f for f in out.rglob("*") if f.is_file()]
    total_mb = sum(f.stat().st_size for f in files) / 1e6
    print(f"\nDone. {len(files)} files, {total_mb:.1f} MB total in {out}")
    big = sorted((f for f in files if f.stat().st_size > 25e6), key=lambda f: -f.stat().st_size)
    for f in big:
        print(f"   WARNING: {f.relative_to(out)} is {f.stat().st_size/1e6:.0f} MB - "
              f"re-run with a smaller --minor-roads-per-province (e.g. 3000)")
    if total_mb > 600:
        print("   WARNING: total is large. GitHub Pages sites should stay under 1 GB; "
              "consider --minor-roads-per-province 3000.")


if __name__ == "__main__":
    main()
