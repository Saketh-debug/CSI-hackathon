"""
Surface Temperature Service — GEE MODIS LST
Fetches Land Surface Temperature from MODIS satellite data via Google Earth Engine
and generates a continuous raster heatmap image (red=hot, yellow=mid, green=cool).
"""

import sys
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "lst_cache.json"
IMAGE_FILE = Path(__file__).resolve().parent.parent / "data" / "lst_heatmap.png"
CREDS_FILE = Path(__file__).resolve().parent.parent / config.GEE_CREDENTIALS_FILE

_ee_initialized = False


def init_gee():
    """Initialize GEE with service account."""
    global _ee_initialized
    if _ee_initialized:
        return True
    try:
        import ee
        credentials = ee.ServiceAccountCredentials(
            config.GEE_SERVICE_ACCOUNT, str(CREDS_FILE)
        )
        ee.Initialize(credentials, project=config.GEE_PROJECT)
        _ee_initialized = True
        return True
    except Exception as e:
        print(f"[LST] GEE init failed: {e}")
        return False


def fetch_lst_raster(force_refresh=False):
    """
    Fetch MODIS Land Surface Temperature as a 2D numpy array + bounds.
    Returns dict: {grid, bounds, min_temp, max_temp, timestamp}
    - grid: 2D numpy array of temperatures in °C
    - bounds: [[south, west], [north, east]]
    """
    # Check cache
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                cached = json.load(f)
            if time.time() - cached.get("timestamp", 0) < config.TEMP_CACHE_TTL:
                cached["grid"] = np.array(cached["grid"])
                return cached
        except Exception:
            pass

    grid = None
    bounds = _get_bounds()

    try:
        if init_gee():
            grid = _fetch_from_gee(bounds)
    except Exception as e:
        print(f"[LST] GEE fetch failed: {e}")

    if grid is None:
        print("[LST] Using simulated surface temperature")
        grid = _simulate_lst(bounds)

    result = {
        "grid": grid,
        "bounds": bounds,
        "min_temp": float(np.nanmin(grid)),
        "max_temp": float(np.nanmax(grid)),
        "timestamp": time.time(),
    }

    # Cache (convert numpy to list for JSON)
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {**result, "grid": grid.tolist()}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f)

    # Generate PNG heatmap image
    _save_heatmap_image(grid, bounds)

    return result


def _get_bounds():
    """Get lat/lon bounds for the 50km radius area."""
    deg_per_km = 1 / 111.0
    r = config.RADIUS_KM * deg_per_km
    south = config.CENTER_LAT - r
    north = config.CENTER_LAT + r
    west = config.CENTER_LON - r
    east = config.CENTER_LON + r
    return [[south, west], [north, east]]


def _fetch_from_gee(bounds):
    """Fetch MODIS LST from GEE as a sampled grid."""
    import ee

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    aoi = ee.Geometry.Rectangle([bounds[0][1], bounds[0][0], bounds[1][1], bounds[1][0]])

    # MODIS 8-day LST at 1km resolution
    dataset = (ee.ImageCollection('MODIS/061/MOD11A2')
               .filterBounds(aoi)
               .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
               .select('LST_Day_1km')
               .mean())

    # Convert from MODIS scale (K * 0.02) to Celsius
    lst_celsius = dataset.multiply(0.02).subtract(273.15)

    # Sample at a grid resolution for the raster
    grid_size = config.HEATMAP_RESOLUTION
    lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)

    # Create sample points
    points = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            points.append(ee.Feature(ee.Geometry.Point([lon, lat]), {"r": i, "c": j}))

    fc = ee.FeatureCollection(points)
    sampled = lst_celsius.sampleRegions(collection=fc, scale=1000, geometries=False).getInfo()

    grid = np.full((grid_size, grid_size), np.nan)
    for feat in sampled.get("features", []):
        props = feat["properties"]
        r, c = props.get("r", 0), props.get("c", 0)
        val = props.get("LST_Day_1km", None)
        if val is not None:
            grid[r, c] = val

    # Fill NaN with nearest neighbor interpolation
    from scipy.ndimage import generic_filter
    mask = np.isnan(grid)
    if mask.any() and not mask.all():
        from scipy.interpolate import griddata
        valid = ~mask
        coords_valid = np.array(np.where(valid)).T
        values_valid = grid[valid]
        coords_all = np.array(np.where(np.ones_like(grid, dtype=bool))).T
        grid_filled = griddata(coords_valid, values_valid, coords_all, method='nearest')
        grid = grid_filled.reshape(grid.shape)

    return grid


def _simulate_lst(bounds):
    """
    Simulate realistic LST for Hyderabad area.
    Urban core = hotter, green areas = cooler, elevation effects.
    """
    grid_size = config.HEATMAP_RESOLUTION
    np.random.seed(int(time.time()) % 1000)

    lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)

    # Base temperature varies by time of day
    hour = datetime.now().hour
    if 6 <= hour < 10:
        base_temp = 28
    elif 10 <= hour < 14:
        base_temp = 36
    elif 14 <= hour < 17:
        base_temp = 38
    elif 17 <= hour < 20:
        base_temp = 33
    else:
        base_temp = 26

    grid = np.full((grid_size, grid_size), base_temp, dtype=float)

    # Urban heat island — hotter near city centre
    urban_centers = [
        (17.385, 78.486, 4.0),   # Hyderabad old city
        (17.440, 78.350, 3.0),   # HITEC City / Madhapur
        (17.430, 78.500, 2.5),   # Secunderabad
        (17.360, 78.530, 2.0),   # Dilsukhnagar
    ]

    for ctr_lat, ctr_lon, intensity in urban_centers:
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                dist = np.sqrt((lat - ctr_lat)**2 + (lon - ctr_lon)**2)
                grid[i, j] += intensity * np.exp(-dist / 0.08)

    # Cool zones near water/parks
    cool_zones = [
        (17.426, 78.448, -3.5),  # KBR Park
        (17.423, 78.420, -2.5),  # Durgam Cheruvu lake
        (17.440, 78.480, -4.0),  # Hussain Sagar lake
        (17.362, 78.475, -2.0),  # Osman Sagar
        (17.380, 78.460, -2.5),  # Nehru Zoo Park
        (17.395, 78.300, -1.5),  # Shamirpet outskirts
    ]

    for cz_lat, cz_lon, cooling in cool_zones:
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                dist = np.sqrt((lat - cz_lat)**2 + (lon - cz_lon)**2)
                grid[i, j] += cooling * np.exp(-dist / 0.04)

    # Add random noise for realism
    grid += np.random.normal(0, 0.8, grid.shape)

    return grid


def _save_heatmap_image(grid, bounds):
    """Save the LST grid as a transparent PNG heatmap image for Folium overlay."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    # Custom colormap: green (cool) → yellow (mid) → red (hot)
    colors = ['#15803d', '#22c55e', '#a3e635', '#eab308', '#f97316', '#ef4444', '#b91c1c']
    cmap = mcolors.LinearSegmentedColormap.from_list('temp_heatmap', colors, N=256)

    # Normalize
    vmin = np.nanmin(grid)
    vmax = np.nanmax(grid)
    if vmin == vmax:
        vmax = vmin + 1

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    colored = cmap(norm(grid))

    # Set alpha for transparency (semi-transparent overlay)
    colored[:, :, 3] = 0.65

    IMAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(str(IMAGE_FILE), colored, origin='lower')


def get_temp_at(lat, lon, lst_data=None):
    """
    Get normalised temperature score (0-1) for routing.
    1.0 = hottest, 0.0 = coolest.
    """
    if lst_data is None:
        lst_data = fetch_lst_raster()

    grid = lst_data["grid"]
    if isinstance(grid, list):
        grid = np.array(grid)

    bounds = lst_data["bounds"]
    grid_size = grid.shape[0]

    # Map lat/lon to grid indices
    lat_idx = int((lat - bounds[0][0]) / (bounds[1][0] - bounds[0][0]) * (grid_size - 1))
    lon_idx = int((lon - bounds[0][1]) / (bounds[1][1] - bounds[0][1]) * (grid_size - 1))

    lat_idx = max(0, min(grid_size - 1, lat_idx))
    lon_idx = max(0, min(grid_size - 1, lon_idx))

    temp = grid[lat_idx, lon_idx]
    min_t = lst_data["min_temp"]
    max_t = lst_data["max_temp"]
    rng = max_t - min_t if max_t != min_t else 1

    return (temp - min_t) / rng


# ── Self-test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching LST raster for Hyderabad...")
    data = fetch_lst_raster(force_refresh=True)
    grid = data["grid"]
    print(f"Grid shape: {grid.shape}")
    print(f"Temp range: {data['min_temp']:.1f}°C — {data['max_temp']:.1f}°C")
    print(f"Heatmap saved to: {IMAGE_FILE}")
