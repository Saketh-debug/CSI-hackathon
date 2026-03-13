"""
Tree Canopy (NDVI) Map UI Layer
Renders a Folium map with NDVI-based tree canopy coverage overlay.
"""

import folium
from folium.plugins import HeatMap
import branca.colormap as cm
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def create_canopy_map(ndvi_data):
    """
    Create a Folium map with NDVI tree canopy overlay.
    
    Args:
        ndvi_data: list of dicts from ndvi.compute_ndvi_grid()
    
    Returns:
        folium.Map object
    """
    m = folium.Map(
        location=[config.CENTER_LAT, config.CENTER_LON],
        zoom_start=config.MAP_ZOOM,
        tiles=None,
    )
    
    # Base tiles
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
    ).add_to(m)
    
    if ndvi_data:
        # ── NDVI Heatmap (green = trees) ──
        heat_data = [
            [d["lat"], d["lon"], d["ndvi"]]
            for d in ndvi_data
        ]
        
        HeatMap(
            heat_data,
            name="🌳 Tree Canopy Heatmap",
            radius=35,
            blur=25,
            max_zoom=13,
            gradient={
                0.0: '#dc2626',   # red (no trees, exposed)
                0.2: '#f97316',   # orange
                0.4: '#eab308',   # yellow
                0.6: '#22c55e',   # green (some trees)
                1.0: '#15803d',   # dark green (dense canopy)
            },
        ).add_to(m)
        
        # ── Canopy circle markers ──
        dense_group = folium.FeatureGroup(name="🌳 Dense Canopy (NDVI > 0.4)")
        moderate_group = folium.FeatureGroup(name="🌿 Moderate (0.2-0.4)")
        sparse_group = folium.FeatureGroup(name="🏜️ Sparse/No Trees (< 0.2)")
        
        for d in ndvi_data:
            level = d.get("canopy_level", "SPARSE")
            
            if level == "DENSE":
                color = '#15803d'
                fill_color = '#22c55e'
                group = dense_group
                shade_text = "Excellent shade ☀️→🌳"
            elif level == "MODERATE":
                color = '#65a30d'
                fill_color = '#a3e635'
                group = moderate_group
                shade_text = "Partial shade 🌤️"
            else:
                color = '#dc2626'
                fill_color = '#fca5a5'
                group = sparse_group
                shade_text = "No shade ☀️🔥"
            
            popup_html = f"""
            <div style="font-family: 'Segoe UI', sans-serif; min-width: 180px;">
                <h4 style="margin: 0 0 8px 0; color: {color};">
                    {level} CANOPY
                </h4>
                <p style="margin: 4px 0;"><b>NDVI:</b> {d['ndvi']:.3f}</p>
                <p style="margin: 4px 0;"><b>Shade:</b> {shade_text}</p>
                <p style="margin: 4px 0;"><b>Location:</b> ({d['lat']}, {d['lon']})</p>
            </div>
            """
            
            folium.CircleMarker(
                location=[d["lat"], d["lon"]],
                radius=10,
                color=color,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(group)
        
        dense_group.add_to(m)
        moderate_group.add_to(m)
        sparse_group.add_to(m)
    
    # ── NDVI legend ──
    colormap = cm.LinearColormap(
        colors=['#dc2626', '#f97316', '#eab308', '#22c55e', '#15803d'],
        vmin=0.0, vmax=0.8,
        caption='NDVI (Tree Canopy Density) — Higher = More Shade',
    )
    colormap.add_to(m)
    
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m
