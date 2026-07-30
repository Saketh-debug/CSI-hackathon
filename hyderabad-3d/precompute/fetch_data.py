"""
hyderabad-3d | Step 1: Fetch OSM Data
======================================
Downloads building footprints + road network for a 5km demo area
centred on Madhapur / HITEC City, Hyderabad.

Outputs (written to ../data/):
  buildings.geojson  — polygon features with 'height' property
  roads.geojson      — line features with 'road_type', 'name', 'lanes'

Usage:
  python fetch_data.py

Upgrade path:
  Increase RADIUS_M to cover more of Hyderabad.
  For full city, switch to downloading the .pbf from Geofabrik and
  using pyrosm for extraction (avoids OSM API rate limits).
"""

import os
import sys
import json
from pathlib import Path

# Fix Windows CP1252 encoding for Unicode output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Config ──────────────────────────────────────────────────────────────────
CENTER_LAT  = 17.4474   # Madhapur, HITEC City
CENTER_LON  = 78.3762
RADIUS_M    = 5000      # 5 km demo area — increase later for full city

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BUILDINGS_OUT = OUT_DIR / "buildings.geojson"
ROADS_OUT     = OUT_DIR / "roads.geojson"

# Road types to include (ordered by importance for rendering)
ROAD_TYPES = [
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "residential", "living_street", "unclassified", "road",
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def resolve_height(tags: dict) -> float:
    """
    Resolve building height from OSM tags.
    Priority: height tag → building:levels × 3m → default 5m (1 floor)
    """
    raw_h = tags.get("height") or tags.get("building:height")
    if raw_h:
        try:
            # Strip units like "18 m" or "18m"
            return float(str(raw_h).replace("m", "").replace(" ", "").strip())
        except (ValueError, TypeError):
            pass

    levels = tags.get("building:levels") or tags.get("levels")
    if levels:
        try:
            return float(levels) * 3.0
        except (ValueError, TypeError):
            pass

    return 5.0  # Default: 1-storey fallback


def fetch_buildings(ox) -> dict:
    """Download building footprints and return as GeoJSON FeatureCollection."""
    print(f"[buildings] Fetching OSM buildings within {RADIUS_M}m of ({CENTER_LAT}, {CENTER_LON})...")

    tags = {"building": True}
    gdf = ox.features_from_point(
        (CENTER_LAT, CENTER_LON),
        tags=tags,
        dist=RADIUS_M,
    )

    # Keep only Polygon geometries (not Points or MultiPolygons edge cases)
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    print(f"[buildings]  -> {len(gdf)} building polygons found")

    features = []
    for idx, row in gdf.iterrows():
        tags_dict = {
            col: row[col]
            for col in gdf.columns
            if col != "geometry" and row[col] is not None and str(row[col]) != "nan"
        }
        height = resolve_height(tags_dict)
        name   = tags_dict.get("name", "")

        # Convert geometry to GeoJSON-compatible dict
        geom = row.geometry.__geo_interface__

        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "id":     str(idx),
                "height": height,
                "name":   name,
                "levels": tags_dict.get("building:levels", ""),
                "type":   tags_dict.get("building", "yes"),
            }
        })

    return {"type": "FeatureCollection", "features": features}


def fetch_roads(ox) -> dict:
    """Download road network and return as GeoJSON FeatureCollection."""
    print(f"[roads]     Fetching OSM drive network within {RADIUS_M}m...")

    G = ox.graph_from_point(
        (CENTER_LAT, CENTER_LON),
        dist=RADIUS_M,
        network_type="drive",
        simplify=True,
    )
    print(f"[roads]      -> {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Convert graph edges to GeoJSON lines
    gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

    features = []
    for idx, row in gdf_edges.iterrows():
        if row.geometry is None:
            continue

        hw = row.get("highway", "road")
        if isinstance(hw, list):
            hw = hw[0]

        geom = row.geometry.__geo_interface__

        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "road_type": str(hw),
                "name":      str(row.get("name", "") or ""),
                "oneway":    bool(row.get("oneway", False)),
                "lanes":     str(row.get("lanes", "1") or "1"),
                "length_m":  round(float(row.get("length", 0) or 0), 1),
                "maxspeed":  str(row.get("maxspeed", "") or ""),
            }
        })

    return {"type": "FeatureCollection", "features": features}


# -- Main ---------------------------------------------------------------------

def main():
    try:
        import osmnx as ox
    except ImportError:
        print("ERROR: osmnx is not installed. Run: pip install osmnx")
        sys.exit(1)

    ox.settings.log_console = False  # Suppress verbose OSMnx logs

    # -- Buildings --
    buildings_fc = fetch_buildings(ox)
    with open(BUILDINGS_OUT, "w", encoding="utf-8") as f:
        json.dump(buildings_fc, f, ensure_ascii=False)

    heights = [feat["properties"]["height"] for feat in buildings_fc["features"]]
    print(f"[buildings]  -> Saved to {BUILDINGS_OUT}")
    if heights:
        print(f"[buildings]    Height range: {min(heights):.1f}m - {max(heights):.1f}m "
              f"(avg {sum(heights)/len(heights):.1f}m)")

    # -- Roads --
    roads_fc = fetch_roads(ox)
    with open(ROADS_OUT, "w", encoding="utf-8") as f:
        json.dump(roads_fc, f, ensure_ascii=False)

    print(f"[roads]      -> Saved to {ROADS_OUT}")
    print(f"[roads]        {len(roads_fc['features'])} road segments")

    # -- Summary ----------------------------------------------------------------
    b_size = BUILDINGS_OUT.stat().st_size / 1024
    r_size = ROADS_OUT.stat().st_size / 1024
    print()
    print("=" * 50)
    print(f"  buildings.geojson  {b_size:>8.1f} KB  ({len(buildings_fc['features'])} buildings)")
    print(f"  roads.geojson      {r_size:>8.1f} KB  ({len(roads_fc['features'])} segments)")
    print("=" * 50)
    print("Done! Now run: python build_graph.py")


if __name__ == "__main__":
    main()
