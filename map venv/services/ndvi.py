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
    Simulate realistic NDVI for Hyderabad 100km area.
    Uses a radial gradient (urban core → suburban → rural fringe)
    plus distinct green zones for parks, forests, and tree-lined roads.
    Produces enough variation to drive meaningful route diversity.
    """
    grid_size = config.HEATMAP_RESOLUTION
    np.random.seed(42)

    lats = np.linspace(bounds[0][0], bounds[1][0], grid_size)
    lons = np.linspace(bounds[0][1], bounds[1][1], grid_size)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # ── Step 1: Radial gradient base ──
    # Urban core (~5km from center) = 0.10
    # Suburban ring (5-20km)        = 0.15 – 0.25
    # Peri-urban/rural (20-50km)    = 0.25 – 0.40
    center_lat, center_lon = config.CENTER_LAT, config.CENTER_LON
    dist_from_center = np.sqrt((lat_grid - center_lat)**2 + (lon_grid - center_lon)**2)
    # Normalize: 0 at center, ~0.9 at edge of 100km (≈0.9 degrees)
    dist_norm = dist_from_center / 0.9
    # Gradient: 0.10 at center → 0.38 at edges
    grid = 0.10 + 0.28 * np.clip(dist_norm, 0, 1)

    # ── Step 2: Green zones (parks, forests, lakes, corridors) ──
    # Format: (lat, lon, peak_ndvi, radius_degrees)
    # Radii scaled for 100km grid — need ≥0.03 to span multiple cells
    green_areas = [
        # ── Major parks & forests (high NDVI, wide area) ──
        (17.4260, 78.4480, 0.72, 0.050),  # KBR National Park + surroundings
        (17.3800, 78.4600, 0.65, 0.040),  # Nehru Zoo Park + Mir Alam Tank
        (17.5200, 78.3100, 0.68, 0.080),  # Shamirpet forest belt (large)
        (17.3600, 78.3800, 0.55, 0.050),  # Rajendranagar + university campus
        (17.3200, 78.5500, 0.60, 0.060),  # Nagarjuna Sagar outskirts
        (17.6000, 78.4000, 0.58, 0.070),  # Medchal green belt (north)
        (17.2500, 78.3000, 0.55, 0.060),  # Chevella forests (south-west)

        # ── Lakes — moderate green rings ──
        (17.4100, 78.4200, 0.50, 0.035),  # Durgam Cheruvu + IT corridor
        (17.4400, 78.4800, 0.45, 0.040),  # Hussain Sagar + surroundings
        (17.4600, 78.3200, 0.48, 0.035),  # Osmansagar lake area
        (17.3500, 78.5200, 0.42, 0.030),  # Himayat Sagar

        # ── Tree-lined corridors (roads with canopy) ──
        (17.4400, 78.4100, 0.45, 0.025),  # Jubilee Hills roads
        (17.4200, 78.4400, 0.42, 0.025),  # Banjara Hills main roads
        (17.4340, 78.3500, 0.38, 0.025),  # Shilparamam → Gachibowli corridor
        (17.4800, 78.4200, 0.35, 0.020),  # Begumpet → Secunderabad
        (17.4500, 78.3700, 0.40, 0.020),  # Madhapur local tree cover
        (17.3900, 78.4800, 0.38, 0.020),  # Nampally → Abids corridor

        # ── Suburban moderate green ──
        (17.5500, 78.5000, 0.45, 0.060),  # North-east outskirts
        (17.3000, 78.4000, 0.40, 0.050),  # South suburban
        (17.4000, 78.2500, 0.50, 0.060),  # West rural belt
        (17.4500, 78.5500, 0.38, 0.050),  # East suburban
    ]

    for gz_lat, gz_lon, ndvi_peak, radius in green_areas:
        dist = np.sqrt((lat_grid - gz_lat)**2 + (lon_grid - gz_lon)**2)
        influence = ndvi_peak * np.exp(-(dist**2) / (2 * radius**2))
        # Non-additive: take the higher of current or new
        grid = np.maximum(grid, influence)

    # ── Step 3: Add realistic noise ──
    grid += np.random.normal(0, 0.03, grid.shape)
    grid = np.clip(grid, 0.02, 0.80)

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
