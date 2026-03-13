"""
WalkWise — Sustainable Walkability Analyzer
Combines 5 metrics into a walkability score grid (0-100):
  25%  Tree Shade       (NDVI from existing service)
  25%  Heat Index       (Temperature + Humidity from Open-Meteo)
  20%  UV Index         (Open-Meteo Forecast API)
  15%  Air Quality      (Open-Meteo Air Quality API — NEW)
  15%  Terrain Slope    (OpenTopoData elevation API)

APIs used:
  - Open-Meteo Forecast   (free, no key)  https://api.open-meteo.com/v1/forecast
  - Open-Meteo Air Quality(free, no key)  https://air-quality-api.open-meteo.com/v1/air-quality
  - OpenTopoData          (free, no key)  https://api.opentopodata.org/v1/srtm90m
  - OSMnx for pedestrian graph (already installed)
"""

import sys
import json
import time
import numpy as np
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
WALK_CACHE_FILE = CACHE_DIR / "walkability_cache.json"
WALK_CACHE_TTL = 600   # 10 minutes


# ──────────────────────────────────────────────────────────────
# 1. UV + Heat Index Grid (Open-Meteo Forecast)
# ──────────────────────────────────────────────────────────────

def _fetch_uv_heat_grid(bounds, grid_size):
    from scipy.interpolate import griddata

    sample_n = 3  # 3×3 = 9 calls (fast)
    lats = np.linspace(bounds[0][0], bounds[1][0], sample_n)
    lons = np.linspace(bounds[0][1], bounds[1][1], sample_n)
    points, values = [], []
    current_hour = datetime.now().hour

    for lat in lats:
        for lon in lons:
            try:
                resp = requests.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat, "longitude": lon,
                        "hourly": "uv_index,apparent_temperature",
                        "forecast_days": 1, "timezone": "Asia/Kolkata",
                    },
                    timeout=8
                )
                if resp.status_code == 200:
                    h = resp.json().get("hourly", {})
                    uv = h.get("uv_index", [6])[current_hour]
                    feels = h.get("apparent_temperature", [32])[current_hour]
                    points.append([lat, lon])
                    values.append((uv, feels))
            except Exception:
                points.append([lat, lon])
                values.append((6.0, 32.0))

    if not points:
        return np.full((grid_size, grid_size), 6.0), np.full((grid_size, grid_size), 32.0)

    all_lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    all_lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)
    lon_g, lat_g = np.meshgrid(all_lons, all_lats)
    coords = np.column_stack([lat_g.ravel(), lon_g.ravel()])
    pts = np.array(points)

    def interp(vals):
        return griddata(pts, vals, coords, method='linear',
                        fill_value=float(np.mean(vals))).reshape(grid_size, grid_size)

    return interp([v[0] for v in values]), interp([v[1] for v in values])


# ──────────────────────────────────────────────────────────────
# 2. Air Quality Index Grid (Open-Meteo Air Quality API — NEW)
# ──────────────────────────────────────────────────────────────

def _fetch_aqi_grid(bounds, grid_size):
    """
    Fetch US AQI from Open-Meteo Air Quality API.
    Endpoint: https://air-quality-api.open-meteo.com/v1/air-quality
    Free, no API key. Returns hourly US AQI (0-500).
    """
    from scipy.interpolate import griddata

    sample_n = 3  # 3×3 = 9 calls (fast)
    lats = np.linspace(bounds[0][0], bounds[1][0], sample_n)
    lons = np.linspace(bounds[0][1], bounds[1][1], sample_n)
    points, aqi_values = [], []
    current_hour = datetime.now().hour

    for lat in lats:
        for lon in lons:
            try:
                resp = requests.get(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    params={
                        "latitude": lat, "longitude": lon,
                        "hourly": "us_aqi",
                        "forecast_days": 1, "timezone": "Asia/Kolkata",
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    h = resp.json().get("hourly", {})
                    aqi_list = h.get("us_aqi", [])
                    # Try current hour, then nearby hours, then fallback
                    aqi = None
                    for offset in [0, -1, 1, -2, 2]:
                        idx = current_hour + offset
                        if 0 <= idx < len(aqi_list) and aqi_list[idx] is not None:
                            aqi = aqi_list[idx]
                            break
                    if aqi is None:
                        # Use first non-None value in the list
                        aqi = next((v for v in aqi_list if v is not None), 50)
                    points.append([lat, lon])
                    aqi_values.append(float(aqi))
            except Exception:
                points.append([lat, lon])
                aqi_values.append(50.0)

    if not points:
        return np.full((grid_size, grid_size), 50.0)

    all_lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    all_lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)
    lon_g, lat_g = np.meshgrid(all_lons, all_lats)
    coords = np.column_stack([lat_g.ravel(), lon_g.ravel()])
    pts = np.array(points)

    return griddata(pts, np.array(aqi_values), coords, method='linear',
                    fill_value=float(np.mean(aqi_values))).reshape(grid_size, grid_size)


# ──────────────────────────────────────────────────────────────
# 3. Terrain Slope Grid (OpenTopoData SRTM)
# ──────────────────────────────────────────────────────────────

def _fetch_slope_grid(bounds, grid_size):
    from scipy.interpolate import griddata

    sample_n = 6  # 6×6 = 36 points, 1 batch request
    lats_s = np.linspace(bounds[0][0], bounds[1][0], sample_n)
    lons_s = np.linspace(bounds[0][1], bounds[1][1], sample_n)
    lat_g, lon_g = np.meshgrid(lats_s, lons_s, indexing='ij')
    all_pts = list(zip(lat_g.ravel(), lon_g.ravel()))

    elevations = {}
    batch_size = 100
    for i in range(0, len(all_pts), batch_size):
        batch = all_pts[i:i + batch_size]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        try:
            resp = requests.get(
                "https://api.opentopodata.org/v1/srtm90m",
                params={"locations": loc_str}, timeout=15
            )
            if resp.status_code == 200:
                for r, (lat, lon) in zip(resp.json().get("results", []), batch):
                    elevations[(lat, lon)] = r.get("elevation") or 0
        except Exception:
            for pt in batch:
                elevations[pt] = 500

    pts = np.array([[lat, lon] for lat, lon in all_pts])
    elev_vals = np.array([elevations.get(pt, 500) for pt in all_pts])

    full_lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    full_lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)
    full_lon_g, full_lat_g = np.meshgrid(full_lons, full_lats)
    full_coords = np.column_stack([full_lat_g.ravel(), full_lon_g.ravel()])

    elev_grid = griddata(pts, elev_vals, full_coords,
                         method='linear', fill_value=500.0
                         ).reshape(grid_size, grid_size)

    cell_size_m = (bounds[1][0] - bounds[0][0]) / grid_size * 111000
    dy, dx = np.gradient(elev_grid, cell_size_m)
    return np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))


# ──────────────────────────────────────────────────────────────
# 4. Combine ALL 5 metrics → Walkability Score
# ──────────────────────────────────────────────────────────────

def compute_walkability_grid(lst_data, ndvi_data):
    """
    Walkability Score (0–100) =
      25% × shade     (NDVI)
      25% × cool      (feels-like temp)
      20% × uv_safe   (UV index)
      15% × air_clean (US AQI)
      15% × flat      (terrain slope)
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if WALK_CACHE_FILE.exists():
        try:
            with open(WALK_CACHE_FILE) as f:
                cached = json.load(f)
            if time.time() - cached.get("timestamp", 0) < WALK_CACHE_TTL:
                print("[WalkWise] Using cached data")
                cached["grid"] = np.array(cached["grid"])
                return cached
        except Exception:
            pass

    print("[WalkWise] Computing fresh walkability grid (5 metrics)...")
    bounds = lst_data["bounds"]
    gs = config.HEATMAP_RESOLUTION

    # Metric 1: Shade (NDVI 0-1 → score)
    ndvi_grid = np.array(ndvi_data["grid"])
    shade_score = np.clip(ndvi_grid / 0.6, 0, 1)

    # Metric 2 + 3: Heat Index + UV (Open-Meteo Forecast)
    print("[WalkWise] Fetching UV + heat index from Open-Meteo...")
    uv_grid, feels_grid = _fetch_uv_heat_grid(bounds, gs)
    heat_score = 1.0 - np.clip((feels_grid - 25.0) / 20.0, 0, 1)
    uv_score = 1.0 - np.clip(uv_grid / 11.0, 0, 1)

    # Metric 4: Air Quality (Open-Meteo Air Quality — NEW)
    print("[WalkWise] Fetching AQI from Open-Meteo Air Quality API...")
    aqi_grid = _fetch_aqi_grid(bounds, gs)
    # US AQI: 0-50 good, 51-100 moderate, 101-150 unhealthy-sensitive, 151+ unhealthy
    aqi_score = 1.0 - np.clip(aqi_grid / 200.0, 0, 1)

    # Metric 5: Slope (OpenTopoData)
    print("[WalkWise] Fetching elevation from OpenTopoData...")
    slope_grid = _fetch_slope_grid(bounds, gs)
    slope_score = 1.0 - np.clip(slope_grid / 15.0, 0, 1)

    # Weighted combination
    walk_grid = (
        0.25 * shade_score +
        0.25 * heat_score +
        0.20 * uv_score +
        0.15 * aqi_score +
        0.15 * slope_score
    ) * 100
    walk_grid = np.clip(walk_grid, 0, 100)

    avg_aqi = float(np.mean(aqi_grid))

    result = {
        "grid": walk_grid.tolist(),
        "bounds": bounds,
        "stats": {
            "avg_score": round(float(np.mean(walk_grid)), 1),
            "max_uv": round(float(np.max(uv_grid)), 1),
            "avg_aqi": round(avg_aqi, 0),
            "avg_slope_deg": round(float(np.mean(slope_grid)), 1),
        },
        "timestamp": time.time(),
    }

    try:
        with open(WALK_CACHE_FILE, "w") as f:
            json.dump(result, f)
    except Exception:
        pass

    result["grid"] = walk_grid
    return result


# ──────────────────────────────────────────────────────────────
# 5. Find BEST Walking Path (single path output)
# ──────────────────────────────────────────────────────────────

def find_best_walk_path(origin_lat, origin_lon, dest_lat, dest_lon, walk_data):
    """
    Returns the single best walking path optimised for walkability score.
    Uses pedestrian graph from OSMnx (network_type='walk').
    """
    import osmnx as ox
    import networkx as nx

    walk_graph_file = CACHE_DIR / "walk_graph.graphml"
    if walk_graph_file.exists():
        G = ox.load_graphml(str(walk_graph_file))
    else:
        G = ox.graph_from_point(
            (config.CENTER_LAT, config.CENTER_LON),
            dist=6000, network_type='walk', simplify=True,
        )
        ox.save_graphml(G, str(walk_graph_file))

    walk_grid = np.array(walk_data["grid"])
    w_bounds = walk_data["bounds"]
    gs = walk_grid.shape[0]

    for u, v, key, data in G.edges(data=True, keys=True):
        mid_lat = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
        mid_lon = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
        length = data.get('length', 50)

        r = int(np.clip(
            (mid_lat - w_bounds[0][0]) / (w_bounds[1][0] - w_bounds[0][0]) * (gs - 1), 0, gs - 1))
        c = int(np.clip(
            (mid_lon - w_bounds[0][1]) / (w_bounds[1][1] - w_bounds[0][1]) * (gs - 1), 0, gs - 1))
        score = float(walk_grid[r, c])
        penalty = max(1.0, (100 - score) / 25)
        data['walk_weight'] = length * penalty

    source = ox.nearest_nodes(G, origin_lon, origin_lat)
    target = ox.nearest_nodes(G, dest_lon, dest_lat)

    try:
        best_path = nx.shortest_path(G, source, target, weight='walk_weight')
    except nx.NetworkXNoPath:
        return {"error": "No walking path found between these points."}

    coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in best_path]

    total_dist = 0
    scores = []
    for i in range(len(best_path) - 1):
        ed = G.get_edge_data(best_path[i], best_path[i+1])
        if ed:
            total_dist += min(d.get('length', 0) for d in ed.values())
        ml = (G.nodes[best_path[i]]['y'] + G.nodes[best_path[i+1]]['y']) / 2
        mlo = (G.nodes[best_path[i]]['x'] + G.nodes[best_path[i+1]]['x']) / 2
        r = int(np.clip((ml - w_bounds[0][0]) / (w_bounds[1][0] - w_bounds[0][0]) * (gs - 1), 0, gs - 1))
        c = int(np.clip((mlo - w_bounds[0][1]) / (w_bounds[1][1] - w_bounds[0][1]) * (gs - 1), 0, gs - 1))
        scores.append(float(walk_grid[r, c]))

    walk_score = round(float(np.mean(scores)), 1) if scores else 50.0

    return {
        "coords": coords,
        "distance_km": round(total_dist / 1000, 2),
        "walk_score": walk_score,
    }
