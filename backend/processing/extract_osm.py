"""
Extraction stage of the pipeline.

Reads `indonesia-latest.osm.pbf` and pulls out:
  1. The road network (ways tagged `highway=<relevant type>`), as a
     GeoDataFrame with the tags described in the project spec.
  2. Province-level administrative boundaries (admin_level=4 relations),
     used later for the spatial join that assigns each road to a province.

Two extraction backends are supported:

  - `pyrosm` (preferred): reads the PBF once into memory-mapped structures
    and returns GeoDataFrames directly. Fast and simple, but loads the
    filtered network for the requested area into memory, so it is used
    with bounding-box filtering for very large runs.

  - `osmium` (streaming fallback): a hand-written `osmium.SimpleHandler`
    that streams over the file way-by-way and only keeps ways whose
    `highway` tag is relevant. This uses effectively constant memory
    regardless of file size and is the backend used automatically if
    pyrosm is not installed or fails to import.

Both backends ignore every OSM element that is not a relevant highway,
which is what keeps memory usage bounded on a 1.6 GB national extract.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import RAW_PBF_FILE, RELEVANT_HIGHWAY_TYPES  # noqa: E402
from app.utils.geo_utils import line_length_m  # noqa: E402
from app.utils.logging_utils import fatal, log  # noqa: E402

# Regional bounding boxes used for chunked / development-mode extraction.
# (min_lon, min_lat, max_lon, max_lat). These roughly cover Indonesia's
# main islands and can be extended for finer chunking.
REGIONAL_BBOXES = {
    "sumatra": (95.0, -6.5, 106.5, 6.5),
    "jawa": (105.0, -8.9, 114.7, -5.5),
    "kalimantan": (108.5, -4.5, 119.5, 4.5),
    "sulawesi": (118.5, -6.2, 125.5, 2.0),
    "bali_nusa": (114.3, -10.9, 125.5, -7.5),
    "maluku": (124.0, -8.5, 135.0, 3.5),
    "papua": (130.0, -9.5, 141.5, 0.5),
}

# Development-mode sample: a small bounding box around DKI Jakarta so
# `--sample` runs finish in seconds instead of hours.
SAMPLE_BBOX = (106.65, -6.37, 106.95, -6.08)  # DKI Jakarta

ROAD_TAGS_OF_INTEREST = [
    "highway", "name", "maxspeed", "lanes", "bridge", "tunnel",
    "oneway", "surface", "ref",
]


def validate_raw_file() -> Path:
    """Confirm the raw PBF exists before doing any work."""
    if not RAW_PBF_FILE.exists():
        fatal(
            f"Raw OSM file not found.\n\n"
            f"Place 'indonesia-latest.osm.pbf' inside:\n"
            f"  {RAW_PBF_FILE.parent}\n\n"
            f"Download it from Geofabrik:\n"
            f"  https://download.geofabrik.de/asia/indonesia-latest.osm.pbf\n"
        )
    size_mb = RAW_PBF_FILE.stat().st_size / (1024 * 1024)
    log(f"    Found raw file: {RAW_PBF_FILE.name} ({size_mb:.1f} MB)")
    return RAW_PBF_FILE


# ---------------------------------------------------------------------------
# Backend 1: pyrosm (preferred, simplest)
# ---------------------------------------------------------------------------
def _extract_with_pyrosm(pbf_path: Path, bbox: Optional[tuple] = None):
    from pyrosm import OSM

    osm = OSM(str(pbf_path), bounding_box=list(bbox) if bbox else None)

    log("    Extracting driving network via pyrosm ...")
    roads = osm.get_network(network_type="driving")
    if roads is None or roads.empty:
        return gpd.GeoDataFrame(columns=["osm_id", "geometry"]), None

    roads = roads[roads["highway"].isin(RELEVANT_HIGHWAY_TYPES)].copy()

    keep_cols = [c for c in ["id", "geometry"] + ROAD_TAGS_OF_INTEREST if c in roads.columns]
    roads = roads[keep_cols].rename(columns={"id": "osm_id"})

    log("    Extracting administrative boundaries (admin_level=4) via pyrosm ...")
    boundaries = None
    try:
        boundaries = osm.get_boundaries(boundary_type="administrative")
        if boundaries is not None and not boundaries.empty:
            if "admin_level" in boundaries.columns:
                boundaries = boundaries[boundaries["admin_level"].astype(str) == "4"].copy()
            name_col = "name" if "name" in boundaries.columns else None
            boundaries = boundaries[[c for c in ["name", "geometry"] if c in boundaries.columns]]
            if name_col:
                boundaries = boundaries.rename(columns={"name": "province"})
    except Exception as exc:  # pragma: no cover - defensive
        log(f"    Warning: could not extract boundaries via pyrosm ({exc}).")
        boundaries = None

    return roads, boundaries


# ---------------------------------------------------------------------------
# Backend 2: pyosmium streaming handler (constant-memory fallback)
# ---------------------------------------------------------------------------
def _extract_with_osmium(pbf_path: Path, bbox: Optional[tuple] = None):
    import osmium

    class RoadHandler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.records = []
            self.wkbfab = osmium.geom.WKBFactory()

        def way(self, w):
            tags = w.tags
            highway = tags.get("highway")
            if highway not in RELEVANT_HIGHWAY_TYPES:
                return
            try:
                wkb = self.wkbfab.create_linestring(w)
            except Exception:
                return
            from shapely import wkb as shapely_wkb
            geom = shapely_wkb.loads(wkb, hex=True)

            if bbox is not None:
                minx, miny, maxx, maxy = bbox
                gminx, gminy, gmaxx, gmaxy = geom.bounds
                if gmaxx < minx or gminx > maxx or gmaxy < miny or gminy > maxy:
                    return

            row = {"osm_id": w.id, "geometry": geom}
            for tag in ROAD_TAGS_OF_INTEREST:
                row[tag] = tags.get(tag)
            self.records.append(row)

    log("    Extracting road network via pyosmium (streaming) ...")
    handler = RoadHandler()
    handler.apply_file(str(pbf_path), locations=True)

    roads = gpd.GeoDataFrame(handler.records, geometry="geometry", crs="EPSG:4326")
    log("    Note: administrative boundary extraction via pyosmium relations is "
        "not implemented in the streaming fallback; province assignment will "
        "fall back to a bundled simplified province boundary file if present.")
    return roads, None


def extract_roads_and_boundaries(pbf_path: Path, sample: bool = False):
    """
    Extract the road network (and province boundaries when available).

    sample=True restricts extraction to SAMPLE_BBOX (a small Jakarta-area
    bounding box) so development iterations finish in seconds. This never
    fabricates data -- it is a smaller real extract of the same PBF.
    """
    bbox = SAMPLE_BBOX if sample else None

    try:
        roads, boundaries = _extract_with_pyrosm(pbf_path, bbox=bbox)
        backend = "pyrosm"
    except Exception as exc:
        log(f"    pyrosm extraction failed or unavailable ({exc}); "
            f"falling back to pyosmium streaming extraction.")
        roads, boundaries = _extract_with_osmium(pbf_path, bbox=bbox)
        backend = "osmium"

    log(f"    Extraction backend used: {backend}")
    log(f"    Raw extracted road ways: {len(roads):,}")
    if boundaries is not None:
        log(f"    Raw extracted province boundaries: {len(boundaries):,}")

    return roads, boundaries


if __name__ == "__main__":
    validate_raw_file()
    r, b = extract_roads_and_boundaries(RAW_PBF_FILE, sample=True)
    log(f"Sample extraction complete: {len(r)} roads, "
        f"{0 if b is None else len(b)} boundaries.")
