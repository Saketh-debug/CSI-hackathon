"""
CoolPath Route Comparison UI
Renders both fastest and coolest routes on a Folium map with stats.
"""

import folium
import branca.colormap as cm
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def create_route_map(route_result, origin_name="A", dest_name="B",
                     temp_data=None, ndvi_data=None):
    """
    Create a Folium map showing both fastest and coolest routes.
    
    Args:
        route_result: dict from routing.find_routes()
        origin_name: display name for origin
        dest_name: display name for destination
        temp_data: optional temperature data for heatmap bg
        ndvi_data: optional NDVI data for tree overlay
    
    Returns:
        folium.Map object
    """
    if "error" in route_result:
        m = folium.Map(
            location=[config.CENTER_LAT, config.CENTER_LON],
            zoom_start=config.MAP_ZOOM,
        )
        return m
    
    fast = route_result["fastest"]
    cool = route_result["coolest"]
    
    # Center map on midpoint of routes
    all_coords = fast["coords"] + cool["coords"]
    avg_lat = sum(c[0] for c in all_coords) / len(all_coords)
    avg_lon = sum(c[1] for c in all_coords) / len(all_coords)
    
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=13,
        tiles=None,
    )
    
    # Base tiles
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
    ).add_to(m)
    
    # ── NDVI background (subtle) ──
    if ndvi_data:
        from folium.plugins import HeatMap
        ndvi_heat = [[d["lat"], d["lon"], d["ndvi"]] for d in ndvi_data]
        HeatMap(
            ndvi_heat,
            name="🌳 Shade Coverage",
            radius=30,
            blur=20,
            max_zoom=14,
            gradient={0.0: '#fef3c7', 0.4: '#bbf7d0', 1.0: '#15803d'},
            opacity=0.4,
        ).add_to(m)
    
    # ── Fastest route (red/orange) ──
    fast_group = folium.FeatureGroup(name=f"🔴 Fastest Route ({fast['distance_km']} km)")
    
    folium.PolyLine(
        locations=fast["coords"],
        color='#ef4444',
        weight=6,
        opacity=0.8,
        dash_array='10 5',
        popup=folium.Popup(
            f"""<div style="font-family: 'Segoe UI', sans-serif;">
                <h4 style="color:#ef4444; margin:0;">🔴 Fastest Route</h4>
                <p><b>Distance:</b> {fast['distance_km']} km</p>
                <p><b>Shade coverage:</b> {fast['stats']['shade_pct']}%</p>
                <p><b>Avg heat exposure:</b> {fast['stats']['avg_temp_score']:.0%}</p>
            </div>""",
            max_width=250,
        ),
    ).add_to(fast_group)
    fast_group.add_to(m)
    
    # ── Coolest route (green/blue) ──
    cool_group = folium.FeatureGroup(name=f"🟢 CoolPath ({cool['distance_km']} km, +{cool.get('deviation_pct', 0)}%)")
    
    folium.PolyLine(
        locations=cool["coords"],
        color='#22c55e',
        weight=7,
        opacity=0.9,
        popup=folium.Popup(
            f"""<div style="font-family: 'Segoe UI', sans-serif;">
                <h4 style="color:#22c55e; margin:0;">🟢 CoolPath Route</h4>
                <p><b>Distance:</b> {cool['distance_km']} km (+{cool.get('deviation_pct', 0)}%)</p>
                <p><b>Shade coverage:</b> {cool['stats']['shade_pct']}%</p>
                <p><b>Avg heat exposure:</b> {cool['stats']['avg_temp_score']:.0%}</p>
                <p><b>Avg shade index:</b> {cool['stats']['avg_shade']:.2f}</p>
            </div>""",
            max_width=250,
        ),
    ).add_to(cool_group)
    cool_group.add_to(m)
    
    # ── Origin & destination markers ──
    origin_coord = fast["coords"][0]
    dest_coord = fast["coords"][-1]
    
    folium.Marker(
        location=origin_coord,
        popup=f"<b>📍 {origin_name}</b> (Start)",
        icon=folium.Icon(color='blue', icon='home', prefix='glyphicon'),
    ).add_to(m)
    
    folium.Marker(
        location=dest_coord,
        popup=f"<b>🏁 {dest_name}</b> (Destination)",
        icon=folium.Icon(color='red', icon='flag', prefix='glyphicon'),
    ).add_to(m)
    
    # ── Legend ──
    legend_html = f"""
    <div style="
        position: fixed; bottom: 50px; left: 50px; z-index: 1000;
        background: rgba(255,255,255,0.95); padding: 15px 20px;
        border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        font-family: 'Segoe UI', sans-serif; font-size: 13px;
        backdrop-filter: blur(10px);
    ">
        <h4 style="margin:0 0 10px 0; font-size:15px;">🛵 Route Comparison</h4>
        <div style="margin: 5px 0;">
            <span style="color:#ef4444; font-weight:bold;">━ ━ ━</span> Fastest ({fast['distance_km']} km)
        </div>
        <div style="margin: 5px 0;">
            <span style="color:#22c55e; font-weight:bold;">━━━━</span> CoolPath ({cool['distance_km']} km)
        </div>
        <hr style="margin: 8px 0; border-color: #e5e7eb;">
        <div style="font-size:11px; color:#6b7280;">
            Shade: {fast['stats']['shade_pct']}% → {cool['stats']['shade_pct']}%<br>
            Extra distance: +{cool.get('deviation_pct', 0)}%
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m


def get_route_stats_df(route_result):
    """Return route comparison as a dict suitable for Streamlit display."""
    if "error" in route_result:
        return None
    
    fast = route_result["fastest"]
    cool = route_result["coolest"]
    
    return {
        "Metric": [
            "📏 Distance",
            "🌳 Shade Coverage",
            "🌡️ Heat Exposure",
            "📐 Extra Distance",
            "🌿 Avg Shade Index",
        ],
        "🔴 Fastest Route": [
            f"{fast['distance_km']} km",
            f"{fast['stats']['shade_pct']}%",
            f"{fast['stats']['avg_temp_score']:.0%}",
            "—",
            f"{fast['stats']['avg_shade']:.3f}",
        ],
        "🟢 CoolPath": [
            f"{cool['distance_km']} km",
            f"{cool['stats']['shade_pct']}%",
            f"{cool['stats']['avg_temp_score']:.0%}",
            f"+{cool.get('deviation_pct', 0)}%",
            f"{cool['stats']['avg_shade']:.3f}",
        ],
    }
