"""
Temperature Heatmap UI Layer
Renders a Folium heatmap of temperature data with danger zone markers.
"""

import folium
from folium.plugins import HeatMap
import branca.colormap as cm
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def create_temperature_map(temp_data, predictions=None):
    """
    Create a Folium map with temperature heatmap overlay.
    
    Args:
        temp_data: list of dicts from temperature.fetch_temperature_grid()
        predictions: optional list from ml_predictor.predict_grid()
    
    Returns:
        folium.Map object
    """
    m = folium.Map(
        location=[config.CENTER_LAT, config.CENTER_LON],
        zoom_start=config.MAP_ZOOM,
        tiles=None,
    )
    
    # Add base tile layers
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
    ).add_to(m)
    
    if temp_data:
        # ── Heatmap layer ──
        heat_data = [
            [d["lat"], d["lon"], d["current_temp"]]
            for d in temp_data
        ]
        
        HeatMap(
            heat_data,
            name="🌡️ Temperature Heatmap",
            radius=35,
            blur=25,
            max_zoom=13,
            gradient={
                0.0: '#3b82f6',   # cool blue
                0.3: '#22c55e',   # green
                0.5: '#eab308',   # yellow
                0.7: '#f97316',   # orange
                1.0: '#ef4444',   # red hot
            },
        ).add_to(m)
        
        # ── Danger zone markers ──
        danger_group = folium.FeatureGroup(name="🔴 Danger Zones (>40°C)")
        caution_group = folium.FeatureGroup(name="🟡 Caution Zones (35-40°C)")
        safe_group = folium.FeatureGroup(name="🟢 Safe Zones (<35°C)")
        
        for d in temp_data:
            icon_map = {
                "DANGER": ("red", "fire", danger_group),
                "CAUTION": ("orange", "warning-sign", caution_group),
                "SAFE": ("green", "ok-sign", safe_group),
            }
            
            color, icon, group = icon_map.get(d["level"], ("gray", "question-sign", safe_group))
            
            popup_html = f"""
            <div style="font-family: 'Segoe UI', sans-serif; min-width: 180px;">
                <h4 style="margin: 0 0 8px 0; color: {'#dc2626' if d['level']=='DANGER' else '#ea580c' if d['level']=='CAUTION' else '#16a34a'};">
                    {d['level']}
                </h4>
                <p style="margin: 4px 0;"><b>Temperature:</b> {d['current_temp']}°C</p>
                <p style="margin: 4px 0;"><b>Feels like:</b> {d['apparent_temp']}°C</p>
                <p style="margin: 4px 0;"><b>Location:</b> ({d['lat']}, {d['lon']})</p>
            </div>
            """
            
            folium.Marker(
                location=[d["lat"], d["lon"]],
                popup=folium.Popup(popup_html, max_width=250),
                icon=folium.Icon(color=color, icon=icon, prefix='glyphicon'),
            ).add_to(group)
        
        danger_group.add_to(m)
        caution_group.add_to(m)
        safe_group.add_to(m)
    
    # ── ML Predictions overlay ──
    if predictions:
        pred_group = folium.FeatureGroup(name="🔮 ML Predictions", show=False)
        
        for p in predictions:
            color_map = {"DANGER": "red", "CAUTION": "orange", "SAFE": "green"}
            
            folium.CircleMarker(
                location=[p["lat"], p["lon"]],
                radius=12,
                color=color_map.get(p["level"], "gray"),
                fill=True,
                fill_opacity=0.6,
                popup=f"Predicted: {p['predicted_temp']}°C ({p['level']})",
            ).add_to(pred_group)
        
        pred_group.add_to(m)
    
    # ── Color legend ──
    colormap = cm.LinearColormap(
        colors=['#3b82f6', '#22c55e', '#eab308', '#f97316', '#ef4444'],
        vmin=20, vmax=45,
        caption='Temperature (°C)',
    )
    colormap.add_to(m)
    
    # Layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m
