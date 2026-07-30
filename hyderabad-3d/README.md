# 🏙️ Hyderabad 3D City Map

A 3D interactive city map of Hyderabad built with **MapLibre GL**, **FastAPI**, and **OSM data**.
Part of the Verdex CoolPath project — standalone experiment module.

## Features
- ✅ 3D extruded buildings with height-based colour gradient
- ✅ Road network with road-type-based styling
- ✅ Point-to-point routing via NetworkX (precomputed graph)
- ✅ Address geocoding via Nominatim
- ✅ Layer toggles (buildings, roads, 3D pitch)
- ✅ GPS location support
- ✅ Demo area: 5km around Madhapur/HITEC City

---

## Quick Start

### Step 1 — Precompute data (run once, ~5-10 min)

```bash
cd precompute

# Use your existing project venv (osmnx already installed)
# OR: pip install -r requirements.txt

python fetch_data.py    # Downloads buildings + roads → ../data/
python build_graph.py   # Builds routing graph → ../data/routing_graph.pkl
```

You should see:
```
buildings.geojson   ~15,000 KB  (X buildings)
roads.geojson       ~3,000 KB   (Y segments)
routing_graph.pkl   ~XX MB
```

### Step 2 — Start the backend

```bash
cd backend
pip install -r requirements.txt   # fastapi, uvicorn (others already in venv)

uvicorn main:app --reload --port 8000
```

Test it:
- http://localhost:8000/ → status check
- http://localhost:8000/buildings → GeoJSON
- http://localhost:8000/geocode?q=Gachibowli → lat/lon

### Step 3 — Start the frontend

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** — you should see the 3D city.

---

## Project Structure

```
hyderabad-3d/
├── precompute/
│   ├── fetch_data.py       # OSM → buildings.geojson + roads.geojson
│   ├── build_graph.py      # NetworkX graph → routing_graph.pkl
│   └── requirements.txt
│
├── data/                   # Generated files (gitignored)
│   ├── buildings.geojson
│   ├── roads.geojson
│   └── routing_graph.pkl
│
├── backend/
│   ├── main.py             # FastAPI: /buildings /roads /route /geocode
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── main.js          # Entry point
        ├── config.js        # BACKEND_URL, map defaults
        ├── style.css        # Dark theme
        ├── map/
        │   └── map3d.js     # MapLibre map + layers
        └── ui/
            ├── shell.js     # App HTML template
            └── searchPanel.js  # Route search UI
```

---

## Upgrade Path

| Current | Future |
|---|---|
| GeoJSON files | PMTiles vector tiles |
| 5km demo area | Full Hyderabad |
| NetworkX Dijkstra (~1-2s) | OSRM Contraction Hierarchies (<50ms) |
| No analysis | Shadow calculator (sun angle + height raycast) |
| No PostGIS | PostGIS for spatial queries |

---

## Tech Stack

| Layer | Tech |
|---|---|
| 3D Rendering | MapLibre GL JS |
| Frontend | Vanilla JS + Vite |
| Backend | FastAPI + Uvicorn |
| Routing | NetworkX (Dijkstra) |
| Road Data | OpenStreetMap via osmnx |
| Geocoding | Nominatim |
