"""
NDVI / Tree Canopy Service — Google Earth Engine
Computes NDVI from Sentinel-2 as a continuous raster overlay (density map).
Shows tree canopy density across the entire region, not individual points.
"""

import sys
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "ndvi_cache.json"
IMAGE_FILE = Path(__file__).resolve().parent.parent / "data" / "ndvi_overlay.png"
CREDS_FILE = Path(__file__).resolve().parent.parent / config.GEE_CREDENTIALS_FILE

_ee_initialized = False


def init_gee():
    """Initialize Google Earth Engine with service account credentials."""
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
        print(f"[NDVI] GEE init failed: {e}")
        return False


def fetch_ndvi_raster(force_refresh=False):
    """
    Fetch NDVI as a continuous 2D raster grid + save as overlay image.
    Returns dict: {grid, bounds, min_ndvi, max_ndvi, timestamp}
    """
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                cached = json.load(f)
            if time.time() - cached.get("timestamp", 0) < config.NDVI_CACHE_TTL:
                cached["grid"] = np.array(cached["grid"])
                return cached
        except Exception:
            pass

    bounds = _get_bounds()
    grid = None

    try:
        if init_gee():
            grid = _fetch_ndvi_from_gee(bounds)
    except Exception as e:
        print(f"[NDVI] GEE fetch failed: {e}")

    if grid is None:
        print("[NDVI] Using simulated NDVI data")
        grid = _simulate_ndvi(bounds)

    result = {
        "grid": grid,
        "bounds": bounds,
        "min_ndvi": float(np.nanmin(grid)),
        "max_ndvi": float(np.nanmax(grid)),
        "timestamp": time.time(),
    }

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {**result, "grid": grid.tolist()}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f)

    _save_ndvi_image(grid)
    return result


def _get_bounds():
    deg_per_km = 1 / 111.0
    r = config.RADIUS_KM * deg_per_km
    return [
        [config.CENTER_LAT - r, config.CENTER_LON - r],
        [config.CENTER_LAT + r, config.CENTER_LON + r],
    ]


def _fetch_ndvi_from_gee(bounds):
    """Fetch NDVI from Sentinel-2 via GEE as a sampled grid."""
    import ee

    aoi = ee.Geometry.Rectangle([bounds[0][1], bounds[0][0], bounds[1][1], bounds[1][0]])

    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
          .filterBounds(aoi)
          .filterDate('2024-01-01', '2024-12-31')
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
          .median())

    ndvi_image = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')

    grid_size = config.HEATMAP_RESOLUTION
    lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)

    points = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            points.append(ee.Feature(ee.Geometry.Point([lon, lat]), {"r": i, "c": j}))

    fc = ee.FeatureCollection(points)
    sampled = ndvi_image.sampleRegions(collection=fc, scale=500, geometries=False).getInfo()

    grid = np.full((grid_size, grid_size), np.nan)
    for feat in sampled.get("features", []):
        props = feat["properties"]
        r, c = props.get("r", 0), props.get("c", 0)
        val = props.get("NDVI", None)
        if val is not None:
            grid[r, c] = val

    # Fill NaN
    mask = np.isnan(grid)
    if mask.any() and not mask.all():
        from scipy.interpolate import griddata
        valid = ~mask
        coords_valid = np.array(np.where(valid)).T
        values_valid = grid[valid]
        coords_all = np.array(np.where(np.ones_like(grid, dtype=bool))).T
        grid = griddata(coords_valid, values_valid, coords_all, method='nearest').reshape(grid.shape)

    return np.clip(grid, 0, 1)


def _simulate_ndvi(bounds):
    """
    Simulate realistic NDVI for Hyderabad area.
    Parks/lakes = high NDVI, urban = low NDVI.
    """
    grid_size = config.HEATMAP_RESOLUTION
    np.random.seed(42)

    lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)

    # Base: low NDVI (urban)
    grid = np.full((grid_size, grid_size), 0.12)

    # Green zones with influence radius
    green_areas = [
        (17.4260, 78.4480, 0.70, 0.030),  # KBR National Park
        (17.4100, 78.4200, 0.55, 0.020),  # Durgam Cheruvu lake
        (17.4400, 78.4800, 0.50, 0.025),  # Hussain Sagar
        (17.3800, 78.4600, 0.65, 0.025),  # Nehru Zoo Park
        (17.4340, 78.3500, 0.45, 0.020),  # Shilparamam
        (17.3950, 78.3000, 0.55, 0.030),  # Shamirpet forests
        (17.5000, 78.3000, 0.60, 0.040),  # Northern outskirts
        (17.3200, 78.3500, 0.55, 0.035),  # Southern outskirts
        (17.4700, 78.3400, 0.40, 0.020),  # Gachibowli green belt
        (17.4100, 78.3600, 0.35, 0.015),  # Botanical garden area
        (17.3600, 78.3800, 0.45, 0.025),  # Rajendranagar
        (17.4800, 78.4200, 0.38, 0.020),  # Begumpet gardens
        # Road tree corridors
        (17.4400, 78.4100, 0.35, 0.010),  # Road 1 jubilee hills
        (17.4300, 78.4300, 0.40, 0.012),  # Road 36 jubilee hills
        (17.4200, 78.4400, 0.42, 0.010),  # Banjara Hills main road
    ]

    for gz_lat, gz_lon, ndvi_val, radius in green_areas:
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                dist = np.sqrt((lat - gz_lat)**2 + (lon - gz_lon)**2)
                influence = ndvi_val * np.exp(-(dist**2) / (2 * radius**2))
                grid[i, j] = max(grid[i, j], grid[i, j] + influence)

    # Add noise
    grid += np.random.normal(0, 0.03, grid.shape)
    grid = np.clip(grid, 0.0, 0.85)

    return grid


def _save_ndvi_image(grid):
    """Save NDVI grid as a transparent PNG overlay image."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    # Colormap: brown (no trees) → yellow → green (dense canopy)
    colors = ['#92400e', '#d97706', '#eab308', '#84cc16', '#22c55e', '#15803d', '#064e3b']
    cmap = mcolors.LinearSegmentedColormap.from_list('ndvi_cmap', colors, N=256)

    vmin, vmax = 0.0, 0.7
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    colored = cmap(norm(np.clip(grid, vmin, vmax)))
    colored[:, :, 3] = 0.60  # semi-transparent

    IMAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(str(IMAGE_FILE), colored, origin='lower')


def get_ndvi_at(lat, lon, ndvi_data=None):
    """
    Get NDVI value (0-1) at a point using bilinear interpolation.
    Used by routing to assign shade score per road segment.
    """
    if ndvi_data is None:
        ndvi_data = fetch_ndvi_raster()

    grid = ndvi_data["grid"]
    if isinstance(grid, list):
        grid = np.array(grid)

    bounds = ndvi_data["bounds"]
    gs = grid.shape[0]

    lat_idx = int((lat - bounds[0][0]) / (bounds[1][0] - bounds[0][0]) * (gs - 1))
    lon_idx = int((lon - bounds[0][1]) / (bounds[1][1] - bounds[0][1]) * (gs - 1))
    lat_idx = max(0, min(gs - 1, lat_idx))
    lon_idx = max(0, min(gs - 1, lon_idx))

    return float(grid[lat_idx, lon_idx])


if __name__ == "__main__":
    print("Computing NDVI raster for Hyderabad...")
    data = fetch_ndvi_raster(force_refresh=True)
    grid = data["grid"]
    print(f"Grid shape: {grid.shape}")
    print(f"NDVI range: {data['min_ndvi']:.3f} — {data['max_ndvi']:.3f}")
    print(f"Image saved to: {IMAGE_FILE}")
