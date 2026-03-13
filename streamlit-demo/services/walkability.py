"""
Walkability service for CoolPath backend.

Builds a 0-100 walkability grid from:
- NDVI shade
- apparent temperature
- UV index
- AQI
- terrain slope

Also provides best walking path search on OSM pedestrian network.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WALK_CACHE_FILE = DATA_DIR / "walkability_cache.json"
WALK_IMAGE_FILE = DATA_DIR / "walkability_overlay.png"
WALK_GRAPH_FILE = DATA_DIR / "walk_graph.graphml"
WALK_CACHE_TTL = 600  # 10 minutes
WALK_CACHE_VERSION = 2


def _pick_hour_value(values, hour, fallback):
    """Pick the value for the current hour with nearby fallback."""
    if not values:
        return fallback

    for offset in (0, -1, 1, -2, 2):
        idx = hour + offset
        if 0 <= idx < len(values) and values[idx] is not None:
            return float(values[idx])

    for value in values:
        if value is not None:
            return float(value)

    return fallback


def _interpolate_grid(points, values, bounds, grid_size, fill_value):
    """Interpolate sparse sampled values into a dense grid."""
    from scipy.interpolate import griddata

    if not points:
        return np.full((grid_size, grid_size), float(fill_value), dtype=float)

    all_lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    all_lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)
    lon_grid, lat_grid = np.meshgrid(all_lons, all_lats)
    coords = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
    pts = np.array(points, dtype=float)
    vals = np.array(values, dtype=float)

    dense = griddata(
        pts,
        vals,
        coords,
        method="linear",
        fill_value=float(np.nanmean(vals) if len(vals) else fill_value),
    )
    return dense.reshape(grid_size, grid_size)


def _fetch_uv_heat_grid(bounds, grid_size):
    """
    Fetch UV index and apparent temperature from Open-Meteo.
    Uses sparse sampling then interpolation to full grid.
    """
    sample_n = 3  # 3x3 = 9 calls
    lats = np.linspace(bounds[0][0], bounds[1][0], sample_n)
    lons = np.linspace(bounds[0][1], bounds[1][1], sample_n)
    current_hour = datetime.now().hour

    points = []
    uv_values = []
    feels_values = []

    for lat in lats:
        for lon in lons:
            try:
                resp = requests.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "hourly": "uv_index,apparent_temperature",
                        "forecast_days": 1,
                        "timezone": "Asia/Kolkata",
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                hourly = resp.json().get("hourly", {})
                uv = _pick_hour_value(hourly.get("uv_index", []), current_hour, 6.0)
                feels = _pick_hour_value(hourly.get("apparent_temperature", []), current_hour, 32.0)
            except Exception:
                uv, feels = 6.0, 32.0

            points.append([float(lat), float(lon)])
            uv_values.append(uv)
            feels_values.append(feels)

            # Keep API pressure low
            time.sleep(0.05)

    uv_grid = _interpolate_grid(points, uv_values, bounds, grid_size, fill_value=6.0)
    feels_grid = _interpolate_grid(points, feels_values, bounds, grid_size, fill_value=32.0)
    return uv_grid, feels_grid


def _fetch_aqi_grid(bounds, grid_size):
    """
    Fetch US AQI from Open-Meteo air-quality API.
    """
    sample_n = 3  # 3x3 = 9 calls
    lats = np.linspace(bounds[0][0], bounds[1][0], sample_n)
    lons = np.linspace(bounds[0][1], bounds[1][1], sample_n)
    current_hour = datetime.now().hour

    points = []
    aqi_values = []

    for lat in lats:
        for lon in lons:
            try:
                resp = requests.get(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    params={
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "hourly": "us_aqi",
                        "forecast_days": 1,
                        "timezone": "Asia/Kolkata",
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                hourly = resp.json().get("hourly", {})
                aqi = _pick_hour_value(hourly.get("us_aqi", []), current_hour, 50.0)
            except Exception:
                aqi = 50.0

            points.append([float(lat), float(lon)])
            aqi_values.append(float(aqi))
            time.sleep(0.05)

    return _interpolate_grid(points, aqi_values, bounds, grid_size, fill_value=50.0)


def _fetch_slope_grid(bounds, grid_size):
    """
    Fetch terrain slope in degrees using OpenTopoData SRTM elevations.
    """
    from scipy.interpolate import griddata

    sample_n = 6  # 6x6 = 36 points, safe in one request
    lats_sample = np.linspace(bounds[0][0], bounds[1][0], sample_n)
    lons_sample = np.linspace(bounds[0][1], bounds[1][1], sample_n)
    lat_grid, lon_grid = np.meshgrid(lats_sample, lons_sample, indexing="ij")
    all_points = list(zip(lat_grid.ravel(), lon_grid.ravel()))

    locations = "|".join(f"{lat},{lon}" for lat, lon in all_points)
    elevations = {}

    try:
        resp = requests.get(
            "https://api.opentopodata.org/v1/srtm90m",
            params={"locations": locations},
            timeout=20,
        )
        resp.raise_for_status()
        for item, (lat, lon) in zip(resp.json().get("results", []), all_points):
            elevations[(lat, lon)] = float(item.get("elevation") or 0.0)
    except Exception:
        for point in all_points:
            elevations[point] = 500.0

    pts = np.array([[lat, lon] for lat, lon in all_points], dtype=float)
    elev_vals = np.array([elevations[(lat, lon)] for lat, lon in all_points], dtype=float)

    full_lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    full_lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)
    lon_dense, lat_dense = np.meshgrid(full_lons, full_lats)
    dense_coords = np.column_stack([lat_dense.ravel(), lon_dense.ravel()])

    elev_dense = griddata(
        pts,
        elev_vals,
        dense_coords,
        method="linear",
        fill_value=float(np.nanmean(elev_vals) if len(elev_vals) else 500.0),
    ).reshape(grid_size, grid_size)

    # Approx meters per lat degree
    cell_size_m = max((bounds[1][0] - bounds[0][0]) / grid_size * 111000, 1.0)
    dlat, dlon = np.gradient(elev_dense, cell_size_m)
    slope_deg = np.degrees(np.arctan(np.sqrt(dlat**2 + dlon**2)))
    return slope_deg


def _compute_best_hours(bounds):
    """
    Best walking hours where UV < 3 and apparent temp < 32 C.
    """
    center_lat = (bounds[0][0] + bounds[1][0]) / 2
    center_lon = (bounds[0][1] + bounds[1][1]) / 2

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": center_lat,
                "longitude": center_lon,
                "hourly": "uv_index,apparent_temperature",
                "forecast_days": 1,
                "timezone": "Asia/Kolkata",
            },
            timeout=10,
        )
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        uv = hourly.get("uv_index", []) or []
        feels = hourly.get("apparent_temperature", []) or []
        count = min(len(uv), len(feels), 24)
        return [h for h in range(count) if uv[h] is not None and feels[h] is not None and uv[h] < 3 and feels[h] < 32]
    except Exception:
        return []


def _save_walkability_image(walk_grid):
    """Save walkability grid as transparent PNG for map overlay."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    cmap = cm.get_cmap("RdYlGn")
    norm = mcolors.Normalize(vmin=0, vmax=100)
    colored = cmap(norm(np.clip(walk_grid, 0, 100)))
    colored[:, :, 3] = 0.55  # overlay alpha

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    plt.imsave(str(WALK_IMAGE_FILE), colored, origin="lower")


def compute_walkability_grid(lst_data, ndvi_data, force_refresh=False):
    """
    Compute or load walkability grid.

    Score (0-100):
    - 25% NDVI shade
    - 25% apparent temperature comfort
    - 20% UV safety
    - 15% AQI cleanliness
    - 15% terrain flatness
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not force_refresh and WALK_CACHE_FILE.exists():
        try:
            with open(WALK_CACHE_FILE, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
            if (
                cached.get("cache_version") == WALK_CACHE_VERSION
                and time.time() - cached.get("timestamp", 0) < WALK_CACHE_TTL
            ):
                cached["grid"] = np.array(cached["grid"], dtype=float)
                return cached
        except Exception:
            pass

    bounds = lst_data["bounds"]
    grid_size = config.HEATMAP_RESOLUTION

    ndvi_grid = np.array(ndvi_data["grid"], dtype=float)
    shade_score = np.clip(ndvi_grid / 0.6, 0, 1)

    uv_grid, feels_grid = _fetch_uv_heat_grid(bounds, grid_size)
    heat_score = 1.0 - np.clip((feels_grid - 25.0) / 20.0, 0, 1)
    uv_score = 1.0 - np.clip(uv_grid / 11.0, 0, 1)

    aqi_grid = _fetch_aqi_grid(bounds, grid_size)
    aqi_score = 1.0 - np.clip(aqi_grid / 200.0, 0, 1)

    slope_grid = _fetch_slope_grid(bounds, grid_size)
    slope_score = 1.0 - np.clip(slope_grid / 15.0, 0, 1)

    walk_grid = (
        0.25 * shade_score
        + 0.25 * heat_score
        + 0.20 * uv_score
        + 0.15 * aqi_score
        + 0.15 * slope_score
    ) * 100.0
    walk_grid = np.clip(walk_grid, 0, 100)

    # Calibrated city-scale bands to avoid collapsing everything into "Moderate".
    # Current Hyderabad grid usually ranges ~41-62.
    good_threshold = 52.5
    poor_threshold = 47.5
    pct_good = float(np.mean(walk_grid >= good_threshold) * 100)
    pct_moderate = float(np.mean((walk_grid >= poor_threshold) & (walk_grid < good_threshold)) * 100)
    pct_poor = float(np.mean(walk_grid < poor_threshold) * 100)

    result = {
        "grid": walk_grid.tolist(),
        "bounds": bounds,
        "stats": {
            "avg_score": round(float(np.mean(walk_grid)), 1),
            "pct_good": round(pct_good, 1),
            "pct_moderate": round(pct_moderate, 1),
            "pct_poor": round(pct_poor, 1),
            "max_uv": round(float(np.nanmax(uv_grid)), 1),
            "avg_aqi": round(float(np.nanmean(aqi_grid)), 0),
            "avg_slope_deg": round(float(np.nanmean(slope_grid)), 1),
        },
        "best_hours": _compute_best_hours(bounds),
        "timestamp": time.time(),
        "cache_version": WALK_CACHE_VERSION,
    }

    try:
        with open(WALK_CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(result, fh)
    except Exception:
        pass

    _save_walkability_image(walk_grid)
    result["grid"] = walk_grid
    return result


def _score_at(lat, lon, walk_grid, bounds):
    """Sample walkability score from grid for given coordinate."""
    gs = walk_grid.shape[0]
    row = int(np.clip((lat - bounds[0][0]) / (bounds[1][0] - bounds[0][0]) * (gs - 1), 0, gs - 1))
    col = int(np.clip((lon - bounds[0][1]) / (bounds[1][1] - bounds[0][1]) * (gs - 1), 0, gs - 1))
    return float(walk_grid[row, col])


def find_best_walk_path(origin_lat, origin_lon, dest_lat, dest_lon, walk_data):
    """
    Return a single best walking path optimized for walkability.
    """
    import networkx as nx
    import osmnx as ox

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if WALK_GRAPH_FILE.exists():
        graph = ox.load_graphml(str(WALK_GRAPH_FILE))
    else:
        graph = ox.graph_from_point(
            (config.CENTER_LAT, config.CENTER_LON),
            dist=6000,
            network_type="walk",
            simplify=True,
        )
        ox.save_graphml(graph, str(WALK_GRAPH_FILE))

    walk_grid = np.array(walk_data["grid"], dtype=float)
    bounds = walk_data["bounds"]

    for u, v, key, data in graph.edges(data=True, keys=True):
        mid_lat = (graph.nodes[u]["y"] + graph.nodes[v]["y"]) / 2
        mid_lon = (graph.nodes[u]["x"] + graph.nodes[v]["x"]) / 2
        length_m = float(data.get("length", 50.0))
        score = _score_at(mid_lat, mid_lon, walk_grid, bounds)
        penalty = max(1.0, (100.0 - score) / 25.0)
        data["walk_weight"] = length_m * penalty

    source = ox.nearest_nodes(graph, origin_lon, origin_lat)
    target = ox.nearest_nodes(graph, dest_lon, dest_lat)

    try:
        route = nx.shortest_path(graph, source, target, weight="walk_weight")
    except nx.NetworkXNoPath:
        return {"error": "No walking path found between these locations."}

    coords = [[float(graph.nodes[n]["y"]), float(graph.nodes[n]["x"])] for n in route]

    total_dist_m = 0.0
    route_scores = []
    for idx in range(len(route) - 1):
        edge_data = graph.get_edge_data(route[idx], route[idx + 1])
        if edge_data:
            total_dist_m += min(float(edge.get("length", 0.0)) for edge in edge_data.values())

        mid_lat = (graph.nodes[route[idx]]["y"] + graph.nodes[route[idx + 1]]["y"]) / 2
        mid_lon = (graph.nodes[route[idx]]["x"] + graph.nodes[route[idx + 1]]["x"]) / 2
        route_scores.append(_score_at(mid_lat, mid_lon, walk_grid, bounds))

    walk_score = round(float(np.mean(route_scores)), 1) if route_scores else 50.0

    return {
        "coords": coords,
        "distance_km": round(total_dist_m / 1000.0, 2),
        "walk_score": walk_score,
    }
