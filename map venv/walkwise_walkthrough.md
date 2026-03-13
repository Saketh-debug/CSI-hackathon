# WalkWise — Sustainable Walkability Analyzer
## Developer Walkthrough

## Live Screenshot

![WalkWise Tab Live](C:\Users\aruna\.gemini\antigravity\brain\f741aafe-d7e3-45ac-98ff-5861e9427548\walkwise_tab_verified_1773375226663.png)

**Live stats:** Avg Score **68.6** · 🟢 84.7% Good to Walk · 🟡 15.3% Moderate Risk · 🔴 0% Avoid

---

## What Was Added

### New File: [services/walkability.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/services/walkability.py)

A brand new service that computes a **0–100 walkability score** for the Hyderabad region.

### Modified File: [app.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/app.py)

- Added [load_walkability_data()](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/app.py#160-166) cached loader
- Added 4th tab: `🚶 WalkWise`

---

## How the Score is Calculated

```
Walkability Score (0–100) =
    30% × Shade Score        (from NDVI grid — already built)
  + 30% × Heat Index Score   (from Open-Meteo feels-like temp)
  + 25% × UV Safety Score    (from Open-Meteo UV index — NEW)
  + 15% × Terrain Slope      (from OpenTopoData SRTM — NEW)
```

Each sub-score is normalised to 0–1 before weighting:

| Metric | 0 (worst) | 1 (best) | Source |
|---|---|---|---|
| Shade (NDVI) | 0 NDVI (no trees) | NDVI ≥ 0.6 (dense canopy) | Existing [ndvi.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/services/ndvi.py) |
| Heat Index | Feels-like 45°C | Feels-like 25°C | Open-Meteo `apparent_temperature` |
| UV Index | UV = 11 (extreme) | UV = 0 (none) | Open-Meteo `uv_index` |
| Slope | 15°+ (steep) | 0° (flat) | OpenTopoData SRTM 90m |

---

## New APIs Used

### 1. Open-Meteo — UV Index + Humidity + Feels-like (FREE, no key)
- **Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **New params added:** `uv_index`, `apparent_temperature`, `relative_humidity_2m`
- **How:** Sampled at 25 points (5×5 grid) across the region, interpolated to full 80×80 grid using `scipy.interpolate.griddata`
- **Rate limit:** Very generous — we sleep 50ms between calls
- **Already used in:** [weather_forecast.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/services/weather_forecast.py) for temperature; now extended for UV

### 2. OpenTopoData SRTM — Terrain Elevation (FREE, no key)
- **Endpoint:** `https://api.opentopodata.org/v1/srtm90m`
- **What it returns:** Elevation in metres for each coordinate
- **Resolution:** 90m — good enough for city-scale analysis
- **How:** 100 points queried (10×10 grid), elevation → gradient → slope in degrees
- **Rate limit:** 100 points per request, 1 request at a time
- **No sign-up needed**

---

## What the New Tab Shows (frontend guidance)

```
🚶 WalkWise Tab
│
├── [Stat Cards — 4 columns]
│     Avg Walkability Score | % Good | % Moderate | % Poor
│
├── [Best Walking Hours banner]
│     "Best walking windows today: 06:00–08:00 · 19:00–21:00"
│     (UV < 3 AND feels-like < 32°C)
│
├── [Info Panels — 2 columns]
│     UV Index: Max today + Low/Moderate/High label
│     Slope: Avg degrees + Flat/Gentle/Steep label
│
├── [Walkability Heatmap]
│     Folium map with RdYlGn (Red=bad → Green=good) image overlay
│     Legend: 0 = worst, 100 = best
│     Same map style as existing temp/NDVI tabs
│
└── [WalkWise Path Finder]
      Origin text input  |  Destination text input
      [Find WalkWise Path] button
      → Stats table: Shortest vs WalkWise (distance, score, extra %)
      → Dual-route map: red dashed = shortest, green = WalkWise
```

---

## Data Flow

```
User opens WalkWise tab
        ↓
load_walkability_data()   [cached 10min, same TTL as temp/NDVI]
        ↓
compute_walkability_grid(lst_data, ndvi_data)
  ├── shade_score   ← ndvi_data["grid"]  (already fetched)
  ├── heat_score    ← Open-Meteo 5×5 grid → interpolated
  ├── uv_score      ← Open-Meteo 5×5 grid → interpolated
  └── slope_score   ← OpenTopoData 10×10 → grad → interpolated
        ↓
walk_grid (80×80 numpy, 0-100)  ← saved to data/walkability_cache.json
        ↓
Rendered as PNG overlay on Folium map
```

For path finding:
```
[Find WalkWise Path] clicked
        ↓
geocode_location()  ← existing service, reused
        ↓
find_walk_paths()   ← new function in walkability.py
  ├── loads/caches pedestrian OSMnx graph (walk network type)
  │     saved as data/walk_graph.graphml
  ├── assigns edge weights: length × (100 - walk_score) / 25
  ├── Dijkstra: shortest path (weight=length)
  └── Dijkstra: walkwise path (weight=walk_weight)
        ↓
Returns coords, distances, scores for both routes
```

---

## Files Changed Summary

| File | Change | Why |
|---|---|---|
| [services/walkability.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/services/walkability.py) | **NEW** | Core walkability logic |
| [app.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/app.py) lines 155-167 | Added [load_walkability_data()](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/app.py#160-166) + 4th tab | Loader + tab registration |
| [app.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/app.py) lines 577-835 | Added full WalkWise tab UI | Frontend content |
| [data/walkability_cache.json](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/data/walkability_cache.json) | Auto-created on first run | Cache |
| `data/walk_graph.graphml` | Auto-created on first path-find | OSMnx pedestrian graph cache |

---

## Cache Files Created

| File | TTL | Content |
|---|---|---|
| [data/walkability_cache.json](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/data/walkability_cache.json) | 10 min | Full score grid, stats, best hours |
| `data/walk_graph.graphml` | Permanent | OSMnx pedestrian road network |

---

## Frontend Integration Notes

If building a custom frontend (non-Streamlit), these are the API responses you'd consume:

**From [compute_walkability_grid()](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/services/walkability.py#167-294):**
```json
{
  "grid": [[0-100 floats, 80x80]],
  "stats": {
    "avg_score": 52.3,
    "pct_good": 38.2,
    "pct_moderate": 45.1,
    "pct_poor": 16.7,
    "max_uv": 8.1,
    "avg_slope_deg": 1.8
  },
  "best_hours": [5, 6, 7, 18, 19, 20],
  "bounds": [[min_lat, min_lon], [max_lat, max_lon]]
}
```

**From [find_walk_paths()](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/services/walkability.py#300-421):**
```json
{
  "fastest": {"coords": [[lat, lon], ...], "distance_km": 2.3, "walk_score": 44.1},
  "walkwise": {"coords": [[lat, lon], ...], "distance_km": 2.5, "walk_score": 68.7, "extra_dist_pct": 8.7},
  "routes_identical": false
}
```

---

## No New pip Packages Required

All dependencies are already in [requirements.txt](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/requirements.txt):
- `numpy`, `scipy`, `requests` — used by walkability service
- `osmnx`, `networkx` — reused from CoolPath router
- `folium`, `matplotlib`, `pillow` — reused from existing maps
