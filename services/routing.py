"""
Climate-Aware Routing Service v3
- Downloads graph ONCE + saves to disk (GraphML) for instant reuse
- Dynamic graph sizing based on A→B distance
- High-contrast climate weights for genuinely different routes
"""

import sys
import numpy as np
import pickle
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

GRAPH_CACHE_DIR = Path(__file__).resolve().parent.parent / "data"


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance in km between two lat/lon points."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))


def get_cached_graph():
    """
    Load graph from disk cache, or download and cache it.
    Uses a SINGLE graph covering the Madhapur area (8km radius)
    which is enough for most intra-city routes.
    """
    import osmnx as ox

    cache_file = GRAPH_CACHE_DIR / "road_graph.graphml"
    GRAPH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        print(f"[Routing] Loading cached graph from {cache_file}")
        G = ox.load_graphml(str(cache_file))
        print(f"[Routing]  → {G.number_of_nodes()} nodes, {G.number_of_edges()} edges (cached)")
        return G

    # Download once — 8km radius covers most Madhapur/Banjara Hills/HITEC City routes
    print("[Routing] First-time download: 8km road graph around Madhapur...")
    G = ox.graph_from_point(
        (config.CENTER_LAT, config.CENTER_LON),
        dist=8000,
        network_type='drive',
        simplify=True,
    )
    print(f"[Routing]  → {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Save to disk
    ox.save_graphml(G, str(cache_file))
    print(f"[Routing]  → Saved to {cache_file} (future loads will be instant)")

    return G


def smart_graph_radius(origin_lat, origin_lon, dest_lat, dest_lon):
    """
    Calculate a context for graph — returns midpoint + estimated distance.
    Now just informational since we use a pre-cached graph.
    """
    dist_km = haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    mid_lat = (origin_lat + dest_lat) / 2
    mid_lon = (origin_lon + dest_lon) / 2
    print(f"[Routing] A→B straight = {dist_km:.1f}km")
    return mid_lat, mid_lon, dist_km


def get_edge_midpoint(G, u, v):
    """Midpoint of an edge."""
    return (
        (G.nodes[u]['y'] + G.nodes[v]['y']) / 2,
        (G.nodes[u]['x'] + G.nodes[v]['x']) / 2,
    )


def assign_climate_weights(G, lst_data=None, ndvi_data=None):
    """
    Assign climate-aware edge weights — VECTORIZED for speed.
    Batch-computes all edge midpoints + does numpy array indexing at once.
    ~2s for 116k edges instead of ~30s.
    """
    from services.surface_temp import fetch_lst_raster
    from services.ndvi import fetch_ndvi_raster

    if lst_data is None:
        lst_data = fetch_lst_raster()
    if ndvi_data is None:
        ndvi_data = fetch_ndvi_raster()

    # Get grids as numpy arrays
    temp_grid = np.array(lst_data["grid"]) if isinstance(lst_data["grid"], list) else lst_data["grid"]
    ndvi_grid = np.array(ndvi_data["grid"]) if isinstance(ndvi_data["grid"], list) else ndvi_data["grid"]
    t_bounds = lst_data["bounds"]
    n_bounds = ndvi_data["bounds"]
    t_gs = temp_grid.shape[0]
    n_gs = ndvi_grid.shape[0]
    t_min, t_max = lst_data["min_temp"], lst_data["max_temp"]
    t_range = t_max - t_min if t_max != t_min else 1.0

    shade_w = config.SHADE_WEIGHT * 8
    temp_w = config.TEMP_WEIGHT * 6

    # Collect all edges + midpoints in bulk
    edges = list(G.edges(data=True, keys=True))
    n_edges = len(edges)

    # Pre-compute all midpoints
    mid_lats = np.empty(n_edges)
    mid_lons = np.empty(n_edges)
    lengths = np.empty(n_edges)

    for i, (u, v, key, data) in enumerate(edges):
        mid_lats[i] = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
        mid_lons[i] = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
        lengths[i] = data.get('length', 100)

    # Vectorized grid index lookup for temperature
    t_lat_idx = np.clip(
        ((mid_lats - t_bounds[0][0]) / (t_bounds[1][0] - t_bounds[0][0]) * (t_gs - 1)).astype(int),
        0, t_gs - 1
    )
    t_lon_idx = np.clip(
        ((mid_lons - t_bounds[0][1]) / (t_bounds[1][1] - t_bounds[0][1]) * (t_gs - 1)).astype(int),
        0, t_gs - 1
    )
    temp_values = temp_grid[t_lat_idx, t_lon_idx]
    temp_scores = (temp_values - t_min) / t_range

    # Vectorized grid index lookup for NDVI
    n_lat_idx = np.clip(
        ((mid_lats - n_bounds[0][0]) / (n_bounds[1][0] - n_bounds[0][0]) * (n_gs - 1)).astype(int),
        0, n_gs - 1
    )
    n_lon_idx = np.clip(
        ((mid_lons - n_bounds[0][1]) / (n_bounds[1][1] - n_bounds[0][1]) * (n_gs - 1)).astype(int),
        0, n_gs - 1
    )
    ndvi_scores = ndvi_grid[n_lat_idx, n_lon_idx]

    # Vectorized cost computation
    exposure_penalty = (1 - ndvi_scores) ** 2
    heat_penalty = temp_scores ** 2
    factors = 1 + shade_w * exposure_penalty + temp_w * heat_penalty
    climate_weights = lengths * factors

    # Assign back to edges
    for i, (u, v, key, data) in enumerate(edges):
        data['climate_weight'] = float(climate_weights[i])
        data['temp_score'] = float(temp_scores[i])
        data['ndvi_score'] = float(ndvi_scores[i])

    return G


def geocode_location(query):
    """Geocode using Nominatim, bounded to Hyderabad region."""
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent="coolpath-hyd-v3")

    for search in [f"{query}, Hyderabad, Telangana, India", query]:
        try:
            loc = geolocator.geocode(search, viewbox=[
                (config.CENTER_LAT + 0.45, config.CENTER_LON - 0.45),
                (config.CENTER_LAT - 0.45, config.CENTER_LON + 0.45),
            ], bounded=True, timeout=10)
            if loc:
                return (loc.latitude, loc.longitude, loc.address)
        except Exception:
            pass

    return None


def is_within_region(lat, lon):
    """Check if within 50km of centre."""
    return haversine_km(lat, lon, config.CENTER_LAT, config.CENTER_LON) <= config.RADIUS_KM


def find_nearest_node(G, lat, lon):
    """Find nearest graph node."""
    import osmnx as ox
    return ox.nearest_nodes(G, lon, lat)


def route_distance(G, route):
    """Total distance in meters."""
    total = 0
    for i in range(len(route) - 1):
        edge_data = G.get_edge_data(route[i], route[i + 1])
        if edge_data:
            total += min(d.get('length', 0) for d in edge_data.values())
    return total


def route_climate_stats(G, route, lst_data=None, ndvi_data=None):
    """Climate stats along a route."""
    from services.surface_temp import get_temp_at
    from services.ndvi import get_ndvi_at

    temps, ndvis = [], []
    for i in range(len(route) - 1):
        mid = get_edge_midpoint(G, route[i], route[i + 1])
        temps.append(get_temp_at(mid[0], mid[1], lst_data))
        ndvis.append(get_ndvi_at(mid[0], mid[1], ndvi_data))

    if not temps:
        return {"avg_temp_score": 0.5, "avg_shade": 0.2, "shade_pct": 0}

    return {
        "avg_temp_score": round(np.mean(temps), 3),
        "avg_shade": round(np.mean(ndvis), 3),
        "shade_pct": round(sum(1 for n in ndvis if n > 0.25) / len(ndvis) * 100, 1),
    }


def route_coords(G, route):
    """Node list → (lat, lon) list."""
    return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]


def find_routes(G, origin_lat, origin_lon, dest_lat, dest_lon,
                lst_data=None, ndvi_data=None):
    """
    Find fastest and coolest routes.
    Coolest route constrained to MAX_DEVIATION × fastest distance.
    """
    import networkx as nx

    source = find_nearest_node(G, origin_lat, origin_lon)
    target = find_nearest_node(G, dest_lat, dest_lon)

    if source == target:
        return {"error": "Origin and destination are too close together (same road segment)"}

    # Assign climate weights
    assign_climate_weights(G, lst_data, ndvi_data)

    # Fastest route (pure distance)
    try:
        fast_route = nx.shortest_path(G, source, target, weight='length')
    except nx.NetworkXNoPath:
        return {"error": "No driveable path found between these two points. Try closer locations."}

    fast_dist = route_distance(G, fast_route)

    # Coolest route (climate-weighted)
    try:
        cool_route = nx.shortest_path(G, source, target, weight='climate_weight')
    except nx.NetworkXNoPath:
        cool_route = fast_route

    cool_dist = route_distance(G, cool_route)

    # Enforce deviation constraint
    max_allowed = fast_dist * config.MAX_DEVIATION

    if cool_dist > max_allowed:
        try:
            found = False
            for k, path in enumerate(nx.shortest_simple_paths(G, source, target,
                                                               weight='climate_weight')):
                d = route_distance(G, path)
                if d <= max_allowed:
                    cool_route = path
                    cool_dist = d
                    found = True
                    break
                if k > 15:
                    break

            if not found:
                cool_route = fast_route
                cool_dist = fast_dist
        except Exception:
            cool_route = fast_route
            cool_dist = fast_dist

    routes_identical = (fast_route == cool_route)
    fast_stats = route_climate_stats(G, fast_route, lst_data, ndvi_data)
    cool_stats = route_climate_stats(G, cool_route, lst_data, ndvi_data)

    return {
        "fastest": {
            "route": fast_route,
            "coords": route_coords(G, fast_route),
            "distance_m": round(fast_dist, 1),
            "distance_km": round(fast_dist / 1000, 2),
            "stats": fast_stats,
        },
        "coolest": {
            "route": cool_route,
            "coords": route_coords(G, cool_route),
            "distance_m": round(cool_dist, 1),
            "distance_km": round(cool_dist / 1000, 2),
            "stats": cool_stats,
            "deviation_pct": round((cool_dist / fast_dist - 1) * 100, 1) if fast_dist > 0 else 0,
        },
        "routes_identical": routes_identical,
    }


if __name__ == "__main__":
    print("Testing routing v3...")
    G = get_cached_graph()
    result = find_routes(G, 17.4474, 78.3762, 17.4138, 78.4460)
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Fastest: {result['fastest']['distance_km']} km (shade {result['fastest']['stats']['shade_pct']}%)")
        print(f"Coolest: {result['coolest']['distance_km']} km (shade {result['coolest']['stats']['shade_pct']}%)")
        print(f"Same route? {result['routes_identical']}")
