"""
hyderabad-3d | FastAPI Backend
================================
Serves:
  GET /buildings         → buildings.geojson (CORS enabled)
  GET /roads             → roads.geojson
  GET /route             → shortest path via NetworkX Dijkstra
  GET /geocode           → Nominatim address → lat/lon

The routing graph is loaded ONCE at startup into memory.
Subsequent /route calls hit the in-memory graph → ~1-2s response.

Usage:
  uvicorn main:app --reload --port 8000

Upgrade path:
  Replace nx.shortest_path with OSRM HTTP API for <50ms queries.
  Add PostGIS for spatial queries.
  Add /shadow endpoint for shade analysis.
"""

import os
import json
import pickle
import time
from math import radians, cos, sin, asin, sqrt
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response

# ── Config ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BUILDINGS_FILE = DATA_DIR / "buildings.geojson"
ROADS_FILE     = DATA_DIR / "roads.geojson"
GRAPH_FILE     = DATA_DIR / "routing_graph.pkl"

CENTER_LAT = 17.4474
CENTER_LON = 78.3762

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Hyderabad 3D -- Backend API",
    description="Buildings, roads, routing for the 3D city demo",
    version="1.0.0",
)

# GZip compression for large GeoJSON responses (21MB -> ~3MB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # local dev -- restrict in production
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Load data at startup ──────────────────────────────────────────────────────
G = None           # NetworkX graph (loaded once)
_buildings_bytes = None   # Pre-serialised JSON bytes
_roads_bytes = None


@app.on_event("startup")
def load_data():
    global G, _buildings_bytes, _roads_bytes

    # -- Graph --
    if GRAPH_FILE.exists():
        print(f"[startup] Loading routing graph from {GRAPH_FILE}...")
        t0 = time.time()
        with open(GRAPH_FILE, "rb") as f:
            G = pickle.load(f)
        print(f"[startup]  -> {G.number_of_nodes()} nodes, {G.number_of_edges()} edges "
              f"({time.time()-t0:.2f}s)")
    else:
        print("[startup] WARNING: routing_graph.pkl not found. Run precompute/build_graph.py first.")

    # -- Buildings (pre-serialise to bytes for fast serving) --
    if BUILDINGS_FILE.exists():
        print(f"[startup] Loading buildings...")
        with open(BUILDINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _buildings_bytes = json.dumps(data).encode("utf-8")
        print(f"[startup]  -> {len(data['features'])} buildings ({len(_buildings_bytes)//1024} KB)")
    else:
        print("[startup] WARNING: buildings.geojson not found. Run precompute/fetch_data.py first.")

    # -- Roads (pre-serialise to bytes for fast serving) --
    if ROADS_FILE.exists():
        print(f"[startup] Loading roads...")
        with open(ROADS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _roads_bytes = json.dumps(data).encode("utf-8")
        print(f"[startup]  -> {len(data['features'])} road segments ({len(_roads_bytes)//1024} KB)")
    else:
        print("[startup] WARNING: roads.geojson not found. Run precompute/fetch_data.py first.")


# ── Utilities ────────────────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))


def nearest_node(lat: float, lon: float):
    """Find the nearest graph node to a lat/lon coordinate."""
    import osmnx as ox
    return ox.nearest_nodes(G, lon, lat)


def nominatim_geocode(query: str) -> Optional[dict]:
    """Geocode using Nominatim, bounded to Hyderabad region."""
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="hyderabad-3d-v1")
        loc = geolocator.geocode(
            f"{query}, Hyderabad, Telangana, India",
            viewbox=[
                (CENTER_LAT + 0.45, CENTER_LON - 0.45),
                (CENTER_LAT - 0.45, CENTER_LON + 0.45),
            ],
            bounded=True,
            timeout=10,
        )
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "name": loc.address}
    except Exception as e:
        print(f"[geocode] Error: {e}")
    return None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status": "ok",
        "endpoints": ["/buildings", "/roads", "/route", "/geocode"],
        "data_ready": {
            "buildings": _buildings_bytes is not None,
            "roads":     _roads_bytes is not None,
            "graph":     G is not None,
        }
    }


@app.get("/buildings")
def get_buildings():
    """Return building footprints as GeoJSON (gzip-compressed automatically)."""
    if _buildings_bytes is None:
        raise HTTPException(503, "buildings.geojson not loaded. Run precompute/fetch_data.py first.")
    return Response(
        content=_buildings_bytes,
        media_type="application/json",
    )


@app.get("/roads")
def get_roads():
    """Return road network as GeoJSON (gzip-compressed automatically)."""
    if _roads_bytes is None:
        raise HTTPException(503, "roads.geojson not loaded. Run precompute/fetch_data.py first.")
    return Response(
        content=_roads_bytes,
        media_type="application/json",
    )


@app.get("/geocode")
def geocode(q: str = Query(..., description="Address or place name in Hyderabad")):
    """Geocode a place name → {lat, lon, name}."""
    result = nominatim_geocode(q)
    if result is None:
        raise HTTPException(404, f"Could not geocode: '{q}'. Try a more specific Hyderabad address.")
    return result


@app.get("/route")
def get_route(
    from_lat: float = Query(..., alias="from_lat"),
    from_lon: float = Query(..., alias="from_lon"),
    to_lat:   float = Query(..., alias="to_lat"),
    to_lon:   float = Query(..., alias="to_lon"),
):
    """
    Find shortest path between two lat/lon coordinates.
    Returns: GeoJSON LineString + distance_km + duration_min + node_count
    """
    if G is None:
        raise HTTPException(503, "Routing graph not loaded. Run precompute/build_graph.py first.")

    import networkx as nx

    t0 = time.time()

    # Find nearest graph nodes
    try:
        src = nearest_node(from_lat, from_lon)
        dst = nearest_node(to_lat, to_lon)
    except Exception as e:
        raise HTTPException(400, f"Could not find nearest road nodes: {e}")

    if src == dst:
        raise HTTPException(400, "Origin and destination are on the same road segment. Try further apart.")

    # Shortest path by distance
    try:
        path_nodes = nx.shortest_path(G, src, dst, weight="length")
    except nx.NetworkXNoPath:
        raise HTTPException(404, "No driveable route found between these two points.")
    except Exception as e:
        raise HTTPException(500, f"Routing error: {e}")

    # Build coordinate list + calculate distance
    coords = []
    total_distance_m = 0.0
    total_time_s = 0.0

    for i, node in enumerate(path_nodes):
        nd = G.nodes[node]
        coords.append([nd["x"], nd["y"]])  # GeoJSON: [lon, lat]

        if i > 0:
            edge_data = G.get_edge_data(path_nodes[i-1], node)
            if edge_data:
                best = min(edge_data.values(), key=lambda d: d.get("length", 9999))
                total_distance_m += best.get("length", 0)
                total_time_s += best.get("travel_time", best.get("length", 0) / 8.33)  # ~30km/h

    elapsed = time.time() - t0

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {
            "distance_km":   round(total_distance_m / 1000, 2),
            "duration_min":  round(total_time_s / 60, 1),
            "node_count":    len(path_nodes),
            "query_time_ms": round(elapsed * 1000, 1),
        }
    }


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
