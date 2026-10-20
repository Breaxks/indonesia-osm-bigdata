"""
GeoJSON export stage.

Rather than one huge national GeoJSON (which would freeze the browser),
this writes one simplified GeoJSON file per province. Geometries are
simplified with a small tolerance to keep file sizes manageable, and
only the fields the Map Explorer actually needs are included.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from shapely import wkt as shapely_wkt

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import GEOJSON_DIR, MAJOR_ROAD_TYPES  # noqa: E402
from app.utils.logging_utils import log  # noqa: E402

SIMPLIFY_TOLERANCE_DEG = 0.0003  # ~30m, keeps shapes recognizable but light
MAX_FEATURES_PER_FILE = 20000  # safety cap per province file


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def _select_features(prov_roads: pd.DataFrame, province: str) -> pd.DataFrame:
    """
    Keep the province's feature count under MAX_FEATURES_PER_FILE without
    randomly gutting major roads (motorway/trunk/primary/secondary).

    Major roads are numerically a small share of the network but are what
    the "Major roads only" filter and per-type filtering on the Map
    Explorer rely on to show a coherent, connected route -- randomly
    sampling across ALL road types (the old behaviour) could keep only a
    handful of scattered fragments of any one major road, since
    residential/service roads vastly outnumber them. So: major roads are
    always kept in full; only the numerous minor roads (residential,
    service, unclassified, etc.) are randomly subsampled to fit the cap.
    """
    if len(prov_roads) <= MAX_FEATURES_PER_FILE:
        return prov_roads

    major_mask = prov_roads["highway"].isin(MAJOR_ROAD_TYPES)
    major_roads = prov_roads[major_mask]
    minor_roads = prov_roads[~major_mask]

    remaining_budget = max(MAX_FEATURES_PER_FILE - len(major_roads), 0)
    if remaining_budget > 0 and len(minor_roads) > remaining_budget:
        minor_sample = minor_roads.sample(remaining_budget, random_state=42)
    else:
        minor_sample = minor_roads

    if len(major_roads) > MAX_FEATURES_PER_FILE:
        log(f"    Note: {province} has {len(major_roads):,} major-road segments, "
            f"more than the {MAX_FEATURES_PER_FILE:,} nominal cap. Keeping all of "
            f"them anyway (file will exceed the nominal cap) since a complete, "
            f"connected major-road network matters more here than a strict "
            f"file-size ceiling.")

    return pd.concat([major_roads, minor_sample], ignore_index=True)


def _clean(v):
    """Turn pandas NaN into None so it serializes as valid JSON null."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    return v


def export_province_geojson(roads: pd.DataFrame):
    provinces = [p for p in roads["province"].dropna().unique() if p != "Unknown"]
    log(f"    Writing simplified GeoJSON for {len(provinces)} provinces ...")

    manifest = []
    for province in provinces:
        prov_roads = roads[roads["province"] == province]
        prov_roads = _select_features(prov_roads, province)

        features = []
        for _, row in prov_roads.iterrows():
            geom = shapely_wkt.loads(row["geometry_wkt"]).simplify(
                SIMPLIFY_TOLERANCE_DEG, preserve_topology=True
            )
            features.append({
                "type": "Feature",
                "geometry": geom.__geo_interface__,
                "properties": {
                    "osm_id": _clean(row.get("osm_id")),
                    "name": _clean(row.get("name")),
                    "highway": _clean(row.get("highway")),
                    "length_m": round(float(row.get("length_m", 0)), 1),
                    "oneway": bool(row.get("oneway", False)),
                    "lanes": _clean(row.get("lanes")),
                    "surface": _clean(row.get("surface")),
                    "maxspeed": _clean(row.get("maxspeed")),
                },
            })

        fc = {"type": "FeatureCollection", "features": features}
        slug = _slugify(province)
        out_path = GEOJSON_DIR / f"{slug}.geojson"
        import json
        out_path.write_text(json.dumps(fc))
        manifest.append({"province": province, "slug": slug, "feature_count": len(features)})

    import json
    (GEOJSON_DIR / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    log(f"    Saved {len(manifest)} province GeoJSON files + _manifest.json.")
    return manifest