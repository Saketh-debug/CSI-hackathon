"""
Temperature Service — Open-Meteo API Integration
Fetches real-time + forecast temperature data for a grid of points
around Madhapur, Hyderabad (50km radius).
"""

import os
import sys
import json
import time
import requests
import numpy as np
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "temp_cache.json"


def generate_grid(center_lat, center_lon, radius_km, n_points=50):
    """Generate a grid of (lat, lon) points within a circular area."""
    points = []
    # Create a square grid, then filter to circle
    deg_per_km = 1 / 111.0  # rough conversion
    radius_deg = radius_km * deg_per_km
    
    side = int(np.sqrt(n_points)) + 1
    lats = np.linspace(center_lat - radius_deg, center_lat + radius_deg, side)
    lons = np.linspace(center_lon - radius_deg, center_lon + radius_deg, side)
    
    for lat in lats:
        for lon in lons:
            dist = np.sqrt((lat - center_lat)**2 + (lon - center_lon)**2) / deg_per_km
            if dist <= radius_km:
                points.append((round(lat, 4), round(lon, 4)))
            if len(points) >= n_points:
                break
        if len(points) >= n_points:
            break
    
    return points


def fetch_temperature_grid(center_lat=None, center_lon=None, radius_km=None, 
                           n_points=None, force_refresh=False):
    """
    Fetch temperature data for a grid of points from Open-Meteo API.
    Returns list of dicts: [{lat, lon, current_temp, apparent_temp, hourly_temps, ...}]
    """
    center_lat = center_lat or config.CENTER_LAT
    center_lon = center_lon or config.CENTER_LON
    radius_km = radius_km or config.RADIUS_KM
    n_points = n_points or config.GRID_POINTS
    
    # Check cache
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                cached = json.load(f)
            if time.time() - cached.get("timestamp", 0) < config.TEMP_CACHE_TTL:
                return cached["data"]
        except (json.JSONDecodeError, KeyError):
            pass
    
    grid = generate_grid(center_lat, center_lon, radius_km, n_points)
    results = []
    
    # Open-Meteo supports multi-point in a single call
    lats = ",".join(str(p[0]) for p in grid)
    lons = ",".join(str(p[1]) for p in grid)
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": "temperature_2m,apparent_temperature",
        "current": "temperature_2m,apparent_temperature",
        "forecast_days": 7,
        "timezone": "Asia/Kolkata"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Open-Meteo returns array when multiple coordinates
        if isinstance(data, list):
            entries = data
        else:
            entries = [data]
        
        for i, entry in enumerate(entries):
            lat = grid[i][0] if i < len(grid) else entry.get("latitude", 0)
            lon = grid[i][1] if i < len(grid) else entry.get("longitude", 0)
            
            current = entry.get("current", {})
            hourly = entry.get("hourly", {})
            
            current_temp = current.get("temperature_2m", 0)
            apparent_temp = current.get("apparent_temperature", 0)
            
            # Classify danger level
            if apparent_temp >= config.TEMP_DANGER:
                level = "DANGER"
            elif apparent_temp >= config.TEMP_CAUTION:
                level = "CAUTION"
            else:
                level = "SAFE"
            
            results.append({
                "lat": lat,
                "lon": lon,
                "current_temp": current_temp,
                "apparent_temp": apparent_temp,
                "level": level,
                "hourly_temps": hourly.get("temperature_2m", []),
                "hourly_apparent": hourly.get("apparent_temperature", []),
                "hourly_time": hourly.get("time", []),
            })
    
    except requests.RequestException as e:
        print(f"[Temperature] API error: {e}")
        # Return empty with grid coords so map still renders
        for lat, lon in grid:
            results.append({
                "lat": lat, "lon": lon,
                "current_temp": 30, "apparent_temp": 30,
                "level": "SAFE",
                "hourly_temps": [], "hourly_apparent": [], "hourly_time": [],
            })
    
    # Save cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"timestamp": time.time(), "data": results}, f)
    
    return results


def get_temp_at(lat, lon, temp_data=None):
    """
    Get normalised temperature score (0-1) for a given point.
    Uses nearest-neighbor interpolation from grid data.
    1.0 = hottest point in grid, 0.0 = coolest.
    """
    if temp_data is None:
        temp_data = fetch_temperature_grid()
    
    if not temp_data:
        return 0.5
    
    temps = [d["current_temp"] for d in temp_data]
    min_t, max_t = min(temps), max(temps)
    temp_range = max_t - min_t if max_t != min_t else 1
    
    # Find nearest grid point
    min_dist = float("inf")
    nearest_temp = sum(temps) / len(temps)
    
    for d in temp_data:
        dist = (d["lat"] - lat)**2 + (d["lon"] - lon)**2
        if dist < min_dist:
            min_dist = dist
            nearest_temp = d["current_temp"]
    
    return (nearest_temp - min_t) / temp_range


# ── Self-test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching temperature grid for Madhapur, Hyderabad...")
    data = fetch_temperature_grid(force_refresh=True)
    print(f"Got {len(data)} points")
    for d in data[:3]:
        print(f"  ({d['lat']}, {d['lon']}) → {d['current_temp']}°C "
              f"(feels {d['apparent_temp']}°C) [{d['level']}]")
