"""
hyderabad-3d | Step 2: Build Routing Graph
==========================================
Builds a NetworkX routing graph from the same OSM area used in fetch_data.py,
adds edge weights (length in meters), and pickles it to disk.

The graph is loaded ONCE at backend startup → queries are instant.

Outputs (written to ../data/):
  routing_graph.pkl  — pickled NetworkX MultiDiGraph

Usage:
  python build_graph.py

Upgrade path:
  Replace NetworkX Dijkstra with OSRM (Docker) for sub-10ms queries.
  Or use python-ch library for Contraction Hierarchy precomputation.
"""

import sys
import pickle
from pathlib import Path

# Fix Windows CP1252 encoding for Unicode output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Config ──────────────────────────────────────────────────────────────────
CENTER_LAT = 17.4474
CENTER_LON = 78.3762
RADIUS_M   = 5000      # Must match fetch_data.py

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_OUT = OUT_DIR / "routing_graph.pkl"

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    try:
        import osmnx as ox
        import networkx as nx
    except ImportError as e:
        print(f"ERROR: Missing package: {e}. Run: pip install osmnx networkx")
        sys.exit(1)

    ox.settings.log_console = False

    print(f"[graph] Downloading drive graph ({RADIUS_M}m around Madhapur)...")
    G = ox.graph_from_point(
        (CENTER_LAT, CENTER_LON),
        dist=RADIUS_M,
        network_type="drive",
        simplify=True,
    )

    # Add travel_time to each edge (assuming ~30 km/h avg in city)
    DEFAULT_SPEED_KMH = 30.0
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    print(f"[graph]  → {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # ── Sanity check: run a test route ──
    nodes = list(G.nodes())
    if len(nodes) >= 2:
        src = nodes[0]
        dst = nodes[len(nodes) // 2]
        try:
            path = nx.shortest_path(G, src, dst, weight="length")
            total_len = sum(
                G[path[i]][path[i+1]][0].get("length", 0)
                for i in range(len(path) - 1)
            )
            print(f"[graph]    Test route: {len(path)} nodes, {total_len/1000:.2f} km")
        except nx.NetworkXNoPath:
            print("[graph]    Test route: no path (graph may be disconnected)")

    # ── Save ──
    with open(GRAPH_OUT, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_mb = GRAPH_OUT.stat().st_size / (1024 * 1024)
    print(f"[graph]  → Saved to {GRAPH_OUT} ({size_mb:.1f} MB)")
    print()
    print("=" * 50)
    print(f"  routing_graph.pkl  {size_mb:.1f} MB")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print("=" * 50)
    print("Done! Now start the backend: cd ../backend && uvicorn main:app --reload")


if __name__ == "__main__":
    main()
