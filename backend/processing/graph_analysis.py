"""
Graph analytics stage.

The road network is naturally a graph: intersection/endpoint nodes are
graph nodes, road segments are edges. Building and analyzing ONE graph
for all of Indonesia is not computationally reasonable for expensive
metrics like betweenness centrality (O(V*E)), so this stage builds one
graph PER PROVINCE and aggregates national totals from the per-province
results. This is documented explicitly wherever an approximation is
used, per the project's requirement to never silently approximate.

For provinces whose graph has more nodes than
`EXACT_BETWEENNESS_NODE_LIMIT`, betweenness centrality is estimated using
NetworkX's `k`-sampled approximation (`k=APPROX_BETWEENNESS_SAMPLE_K`)
instead of the exact algorithm, and the result is flagged
`betweenness_approximate=True` in the output so the frontend can show
that clearly.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import networkx as nx
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config import (  # noqa: E402
    APPROX_BETWEENNESS_SAMPLE_K, EXACT_BETWEENNESS_NODE_LIMIT,
    GRAPH_METRICS_PARQUET, GRAPH_NODE_CENTRALITY_PARQUET, GRAPH_SUMMARY_JSON,
    PROCESSED_DIR,
)
from app.utils.geo_utils import node_key  # noqa: E402
from app.utils.logging_utils import log  # noqa: E402
from shapely import wkt as shapely_wkt  # noqa: E402

# Per-province checkpoints live here. If the pipeline is interrupted during
# graph analytics (the most expensive stage on large datasets), re-running
# it skips any province whose checkpoint already exists instead of
# recomputing from scratch. Delete this folder (or a specific province's
# files inside it) to force a recompute.
CHECKPOINT_DIR = PROCESSED_DIR / "graph_checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def _checkpoint_paths(slug: str):
    return (
        CHECKPOINT_DIR / f"{slug}_summary.json",
        CHECKPOINT_DIR / f"{slug}_nodes.parquet",
    )


def _slugify(name: str) -> str:
    import re
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def _build_province_graph(province_roads: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    for _, row in province_roads.iterrows():
        geom = shapely_wkt.loads(row["geometry_wkt"])
        lines = [geom] if geom.geom_type == "LineString" else list(geom.geoms)
        for line in lines:
            coords = list(line.coords)
            if len(coords) < 2:
                continue
            a = node_key(coords[0][0], coords[0][1])
            b = node_key(coords[-1][0], coords[-1][1])
            if a == b:
                continue
            G.add_node(a, lon=coords[0][0], lat=coords[0][1])
            G.add_node(b, lon=coords[-1][0], lat=coords[-1][1])
            G.add_edge(
                a, b,
                length_m=row.get("length_m", 0.0),
                osm_id=row.get("osm_id"),
                highway=row.get("highway"),
            )
    return G


def _analyze_graph(G: nx.Graph, province: str) -> tuple[dict, pd.DataFrame]:
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    if n_nodes == 0:
        return {
            "province": province, "nodes": 0, "edges": 0, "avg_degree": 0.0,
            "connected_components": 0, "largest_component_size": 0,
            "network_density": 0.0, "dead_end_nodes": 0,
            "betweenness_approximate": False,
        }, pd.DataFrame(columns=["province", "node_id", "lon", "lat", "degree",
                                   "degree_centrality", "betweenness_centrality"])

    degrees = dict(G.degree())
    avg_degree = sum(degrees.values()) / n_nodes
    components = list(nx.connected_components(G))
    largest_cc = max((len(c) for c in components), default=0)
    density = nx.density(G)
    dead_ends = sum(1 for d in degrees.values() if d == 1)

    degree_centrality = nx.degree_centrality(G)

    approximate = n_nodes > EXACT_BETWEENNESS_NODE_LIMIT
    if approximate:
        k = min(APPROX_BETWEENNESS_SAMPLE_K, n_nodes)
        betweenness = nx.betweenness_centrality(G, k=k, weight="length_m", seed=42)
    else:
        betweenness = nx.betweenness_centrality(G, weight="length_m")

    summary = {
        "province": province,
        "nodes": n_nodes,
        "edges": n_edges,
        "avg_degree": round(avg_degree, 3),
        "connected_components": len(components),
        "largest_component_size": largest_cc,
        "network_density": round(density, 6),
        "dead_end_nodes": dead_ends,
        "betweenness_approximate": approximate,
    }

    node_rows = []
    for node, attrs in G.nodes(data=True):
        node_rows.append({
            "province": province,
            "node_id": node,
            "lon": attrs.get("lon"),
            "lat": attrs.get("lat"),
            "degree": degrees.get(node, 0),
            "degree_centrality": round(degree_centrality.get(node, 0.0), 6),
            "betweenness_centrality": round(betweenness.get(node, 0.0), 6),
        })
    node_df = pd.DataFrame(node_rows)
    return summary, node_df


def run_graph_analysis(roads: pd.DataFrame, min_roads_per_province: int = 5):
    provinces = [p for p in roads["province"].dropna().unique() if p != "Unknown"]
    total = len(provinces)
    log(f"    Building graphs for {total} provinces ...")
    log(f"    Checkpoints saved to: {CHECKPOINT_DIR}")
    log(f"    (If this run is interrupted, re-running will skip provinces "
        f"already checkpointed here instead of recomputing them.)")

    summaries = []
    top_nodes_frames = []
    run_start = time.time()

    for idx, province in enumerate(provinces, start=1):
        slug = _slugify(province)
        summary_path, nodes_path = _checkpoint_paths(slug)

        if summary_path.exists() and nodes_path.exists():
            summary = json.loads(summary_path.read_text())
            node_df = pd.read_parquet(nodes_path)
            summaries.append(summary)
            if not node_df.empty:
                top_nodes_frames.append(node_df)
            log(f"    [{idx}/{total}] {province}: already computed -- "
                f"loaded from checkpoint, skipping recomputation.")
            continue

        prov_roads = roads[roads["province"] == province]
        if len(prov_roads) < min_roads_per_province:
            log(f"    [{idx}/{total}] {province}: too few roads ({len(prov_roads)}), skipping.")
            continue

        province_start = time.time()
        log(f"    [{idx}/{total}] {province}: building graph "
            f"({len(prov_roads):,} road records) ...")

        G = _build_province_graph(prov_roads)
        summary, node_df = _analyze_graph(G, province)
        elapsed = time.time() - province_start
        total_elapsed = time.time() - run_start

        top = (
            node_df.sort_values("betweenness_centrality", ascending=False).head(20)
            if not node_df.empty else node_df
        )

        # Save this province's result immediately so progress survives a
        # crash or manual interruption (Ctrl+C) partway through the run.
        summary_path.write_text(json.dumps(summary))
        top.to_parquet(nodes_path, index=False)

        summaries.append(summary)
        if not top.empty:
            top_nodes_frames.append(top)

        flag = " (approx. betweenness)" if summary.get("betweenness_approximate") else ""
        avg_per_province = total_elapsed / idx
        remaining = avg_per_province * (total - idx)
        log(f"        -> {summary['nodes']:,} nodes, {summary['edges']:,} edges{flag}, "
            f"done in {elapsed:.1f}s. Checkpoint saved. "
            f"Est. remaining: ~{remaining / 60:.1f} min for {total - idx} provinces.")

    graph_metrics = pd.DataFrame(summaries)
    graph_metrics.to_parquet(GRAPH_METRICS_PARQUET, index=False)

    top_nodes_df = (
        pd.concat(top_nodes_frames, ignore_index=True)
        if top_nodes_frames else
        pd.DataFrame(columns=["province", "node_id", "lon", "lat", "degree",
                                "degree_centrality", "betweenness_centrality"])
    )
    top_nodes_df.to_parquet(GRAPH_NODE_CENTRALITY_PARQUET, index=False)

    if not graph_metrics.empty:
        national = {
            "total_nodes": int(graph_metrics["nodes"].sum()),
            "total_edges": int(graph_metrics["edges"].sum()),
            "avg_degree_national": round(float(graph_metrics["avg_degree"].mean()), 3),
            "provinces_analyzed": int(len(graph_metrics)),
            "provinces_with_approximate_betweenness": int(
                graph_metrics["betweenness_approximate"].sum()
            ),
            "note": (
                "Graph metrics are computed per-province rather than for a single "
                "nationwide graph, because nationwide exact betweenness centrality "
                "is not computationally reasonable. Provinces whose road graph "
                f"exceeds {EXACT_BETWEENNESS_NODE_LIMIT} nodes use k-sampled "
                f"approximate betweenness (k={APPROX_BETWEENNESS_SAMPLE_K})."
            ),
        }
    else:
        national = {"total_nodes": 0, "total_edges": 0, "provinces_analyzed": 0}

    GRAPH_SUMMARY_JSON.write_text(json.dumps(national, indent=2))

    log(f"    Saved graph_metrics.parquet ({len(graph_metrics)} provinces) "
        f"and graph_node_centrality.parquet ({len(top_nodes_df)} top nodes).")

    return graph_metrics, top_nodes_df