"""
CoolPath v2 — Climate-Aware Delivery Route Planner
Main Streamlit Application

🌡️ Temperature Map — GEE MODIS LST continuous heatmap + hourly forecast
🌳 Tree Canopy Map — NDVI continuous density overlay
🛵 CoolPath Router — coolest + shadiest route for delivery riders
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="CoolPath — Climate Route Planner",
    page_icon="🛵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0d9488 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    }
    .main-header h1 { color: #fff; font-size: 2.2rem; font-weight: 700; margin: 0; }
    .main-header p { color: #94a3b8; font-size: 1rem; margin: 0.5rem 0 0 0; }

    .stat-card {
        background: linear-gradient(135deg, #1e293b, #334155);
        border-radius: 12px; padding: 1.2rem 1.5rem;
        color: white; text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }
    .stat-card h3 { font-size: 2rem; margin: 0; font-weight: 700; }
    .stat-card p { font-size: 0.85rem; margin: 0.3rem 0 0 0; color: #94a3b8; }

    .stButton>button {
        background: linear-gradient(135deg, #0d9488, #0f766e);
        color: white; border: none; border-radius: 8px;
        padding: 0.5rem 1.5rem; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #14b8a6, #0d9488);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(13,148,136,0.4);
    }

    div[data-testid="stTabs"] button[role="tab"] {
        font-size: 1.05rem; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛵 CoolPath — Climate-Aware Route Planner</h1>
    <p>Madhapur, Hyderabad · 50 km Radius · Satellite surface temperature + tree canopy density</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Controls")
    if st.button("🔄 Refresh Satellite Data", use_container_width=True, type="primary"):
        for key in list(st.session_state.keys()):
            if key.startswith("lst_") or key.startswith("ndvi_") or key.startswith("route_"):
                del st.session_state[key]
        st.cache_data.clear()
        st.success("Cache cleared!")
        st.rerun()

    st.divider()
    st.markdown("### 📍 Coverage Area")
    st.caption(f"Centre: `{config.CENTER_LAT}, {config.CENTER_LON}`")
    st.caption(f"Radius: `{config.RADIUS_KM}` km")

    st.divider()
    st.markdown("### 🎚️ Routing Weights")
    config.SHADE_WEIGHT = st.slider("🌳 Shade importance", 0.0, 1.0, 0.5, 0.05)
    config.TEMP_WEIGHT = st.slider("🌡️ Temp avoidance", 0.0, 1.0, 0.3, 0.05)
    config.MAX_DEVIATION = st.slider("📐 Max deviation", 1.0, 2.0, 1.3, 0.1)

    st.divider()
    st.caption("Data: MODIS LST · Sentinel-2 NDVI · OSMnx")


# ── Helper: create base Folium map ──────────────────────────
def create_base_map(zoom=config.MAP_ZOOM):
    import folium
    m = folium.Map(
        location=[config.CENTER_LAT, config.CENTER_LON],
        zoom_start=zoom,
        tiles='OpenStreetMap',
    )
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite',
    ).add_to(m)
    return m


# ── Helper: render static map (no reload on zoom) ──────────
def render_map(m, key):
    from streamlit_folium import st_folium
    st_folium(m, width=None, height=550, key=key, returned_objects=[])


# ── Data loaders ────────────────────────────────────────────
@st.cache_data(ttl=config.TEMP_CACHE_TTL, show_spinner="🛰️ Loading surface temperature...")
def load_lst_data():
    from services.surface_temp import fetch_lst_raster
    return fetch_lst_raster()

@st.cache_data(ttl=config.NDVI_CACHE_TTL, show_spinner="🛰️ Loading tree canopy data...")
def load_ndvi_data():
    from services.ndvi import fetch_ndvi_raster
    return fetch_ndvi_raster()

@st.cache_resource(show_spinner="🗺️ Loading road network...")
def load_road_graph():
    from services.routing import get_cached_graph
    return get_cached_graph()


# ── Main tabs ───────────────────────────────────────────────
tab_temp, tab_canopy, tab_router = st.tabs([
    "🌡️ Temperature Map",
    "🌳 Tree Canopy Map",
    "🛵 CoolPath Router",
])


# ═══════════════════════════════════════════════════════════
# TAB 1: Temperature Map
# ═══════════════════════════════════════════════════════════
with tab_temp:
    st.markdown("### 🌡️ Surface Temperature Heatmap")
    st.caption("Land Surface Temperature from MODIS satellite data — continuous heatmap (🟢 cool → 🟡 warm → 🔴 hot)")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🛰️ Fetch Latest Temperature", key="lst_fetch"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        show_forecast = st.checkbox("📊 Show 24hr Forecast", value=True)

    # Load LST raster
    lst_data = load_lst_data()

    # Stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="stat-card"><h3>{lst_data["min_temp"]:.1f}°C</h3><p>🟢 Coolest Zone</p></div>', unsafe_allow_html=True)
    with c2:
        avg_t = (lst_data["min_temp"] + lst_data["max_temp"]) / 2
        st.markdown(f'<div class="stat-card"><h3>{avg_t:.1f}°C</h3><p>🟡 Average</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><h3 style="color:#ef4444">{lst_data["max_temp"]:.1f}°C</h3><p>🔴 Hottest Zone</p></div>', unsafe_allow_html=True)

    # Map with LST raster overlay
    import folium
    temp_map = create_base_map()

    lst_img = str(Path(__file__).resolve().parent / "data" / "lst_heatmap.png")
    if os.path.exists(lst_img):
        bounds = lst_data["bounds"]
        folium.raster_layers.ImageOverlay(
            image=lst_img,
            bounds=bounds,
            opacity=0.65,
            name="🌡️ Surface Temperature",
            interactive=False,
        ).add_to(temp_map)

    folium.LayerControl(collapsed=False).add_to(temp_map)

    # Color legend
    import branca.colormap as cm
    colormap = cm.LinearColormap(
        colors=['#15803d', '#22c55e', '#a3e635', '#eab308', '#f97316', '#ef4444', '#b91c1c'],
        vmin=lst_data["min_temp"], vmax=lst_data["max_temp"],
        caption='Surface Temperature (°C)',
    )
    colormap.add_to(temp_map)

    render_map(temp_map, "temp_map_v2")

    # Hourly forecast chart
    if show_forecast:
        st.markdown("#### 📊 Today's Hourly Weather Forecast")
        from services.weather_forecast import fetch_hourly_forecast, get_weather_description

        forecast = fetch_hourly_forecast()
        if forecast:
            st.caption(f"Current: **{forecast['current_temp']}°C** (feels {forecast['current_apparent']}°C) — {get_weather_description(forecast['weather_code'])}")

            chart_data = pd.DataFrame({
                "Hour": [t.split("T")[1][:5] for t in forecast["times"]],
                "Temperature (°C)": forecast["temps"],
                "Feels Like (°C)": forecast["apparent"],
            })
            st.bar_chart(chart_data.set_index("Hour"), height=250)
        else:
            st.warning("Forecast unavailable")


# ═══════════════════════════════════════════════════════════
# TAB 2: Tree Canopy Map
# ═══════════════════════════════════════════════════════════
with tab_canopy:
    st.markdown("### 🌳 Tree Canopy Density Map")
    st.caption("NDVI from Sentinel-2 satellite — continuous density (🟤 no trees → 🟡 sparse → 🟢 dense canopy / shade)")

    if st.button("🛰️ Refresh Canopy Data", key="ndvi_fetch"):
        st.cache_data.clear()
        st.rerun()

    ndvi_data = load_ndvi_data()

    # Stats
    grid = np.array(ndvi_data["grid"])
    dense_pct = np.mean(grid > 0.4) * 100
    moderate_pct = np.mean((grid > 0.2) & (grid <= 0.4)) * 100
    sparse_pct = np.mean(grid <= 0.2) * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><h3>{ndvi_data["max_ndvi"]:.2f}</h3><p>Max NDVI</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><h3 style="color:#22c55e">{dense_pct:.0f}%</h3><p>🌳 Dense Canopy</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><h3 style="color:#a3e635">{moderate_pct:.0f}%</h3><p>🌿 Moderate</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><h3 style="color:#ef4444">{sparse_pct:.0f}%</h3><p>🏜️ Exposed</p></div>', unsafe_allow_html=True)

    # Map with NDVI overlay
    canopy_map = create_base_map()

    ndvi_img = str(Path(__file__).resolve().parent / "data" / "ndvi_overlay.png")
    if os.path.exists(ndvi_img):
        folium.raster_layers.ImageOverlay(
            image=ndvi_img,
            bounds=ndvi_data["bounds"],
            opacity=0.60,
            name="🌳 Tree Canopy Density",
            interactive=False,
        ).add_to(canopy_map)

    folium.LayerControl(collapsed=False).add_to(canopy_map)

    ndvi_cmap = cm.LinearColormap(
        colors=['#92400e', '#d97706', '#eab308', '#84cc16', '#22c55e', '#15803d', '#064e3b'],
        vmin=0.0, vmax=0.7,
        caption='NDVI (Tree Density) — Higher = More Shade',
    )
    ndvi_cmap.add_to(canopy_map)

    render_map(canopy_map, "canopy_map_v2")


# ═══════════════════════════════════════════════════════════
# TAB 3: CoolPath Router
# ═══════════════════════════════════════════════════════════
with tab_router:
    st.markdown("### 🛵 CoolPath — Find the Coolest Route")
    st.caption("Compare fastest vs. coolest+shadiest route. Both temperature and tree canopy overlays shown.")

    # ── Origin input ──
    st.markdown("##### 📍 Origin")
    col_loc, col_origin = st.columns([1, 3])

    with col_loc:
        use_gps = st.button("📍 My Location", key="gps_btn", use_container_width=True)

    origin_lat, origin_lon = None, None

    if use_gps:
        try:
            from streamlit_geolocation import streamlit_geolocation
            st.caption("Click the button below to share your location:")
            location = streamlit_geolocation()
            if location and location.get('latitude'):
                origin_lat = location['latitude']
                origin_lon = location['longitude']
                st.success(f"📍 Got location: ({origin_lat:.4f}, {origin_lon:.4f})")
        except Exception as e:
            st.warning(f"Geolocation unavailable: {e}")

    with col_origin:
        origin_input = st.text_input(
            "Origin address / street name",
            value="Madhapur, Hyderabad",
            placeholder="e.g., Cyber Towers, HITEC City",
            key="origin_text",
            label_visibility="collapsed",
        )

    # ── Destination input ──
    st.markdown("##### 🏁 Destination")
    dest_input = st.text_input(
        "Destination address / street name",
        value="Banjara Hills, Hyderabad",
        placeholder="e.g., KBR Park, Jubilee Hills",
        key="dest_text",
    )

    # ── Find routes button ──
    if st.button("🧭 Find CoolPath", type="primary", use_container_width=True, key="find_routes_v2"):
        from services.routing import (
            geocode_location, is_within_region,
            find_routes as compute_routes, smart_graph_radius,
        )

        with st.spinner("🔍 Geocoding locations..."):
            # Geocode origin
            if origin_lat and origin_lon:
                origin_coords = (origin_lat, origin_lon, "GPS Location")
            else:
                origin_coords = geocode_location(origin_input)

            if not origin_coords:
                st.error(f"❌ Could not find: '{origin_input}'. Try a more specific address.")
                st.stop()

            dest_coords = geocode_location(dest_input)
            if not dest_coords:
                st.error(f"❌ Could not find: '{dest_input}'. Try a more specific address.")
                st.stop()

            # Validate region
            if not is_within_region(origin_coords[0], origin_coords[1]):
                st.error(f"❌ Origin is outside the {config.RADIUS_KM}km coverage area.")
                st.stop()
            if not is_within_region(dest_coords[0], dest_coords[1]):
                st.error(f"❌ Destination is outside the {config.RADIUS_KM}km coverage area.")
                st.stop()

        st.info(f"📍 **{origin_coords[2]}** → 🏁 **{dest_coords[2]}**")

        with st.spinner("🛰️ Loading climate data..."):
            lst_data = load_lst_data()
            ndvi_data = load_ndvi_data()

        with st.spinner("🗺️ Loading road network & computing routes..."):
            G = load_road_graph()
            result = compute_routes(
                G, origin_coords[0], origin_coords[1],
                dest_coords[0], dest_coords[1], lst_data, ndvi_data,
            )

        st.session_state["route_result"] = result
        st.session_state["route_origin_name"] = origin_coords[2]
        st.session_state["route_dest_name"] = dest_coords[2]
        st.session_state["route_lst"] = lst_data
        st.session_state["route_ndvi"] = ndvi_data

    # ── Display results ──
    if "route_result" in st.session_state:
        result = st.session_state["route_result"]

        if "error" in result:
            st.error(f"❌ {result['error']}")
        else:
            fast = result["fastest"]
            cool = result["coolest"]

            # Stats comparison table
            st.markdown("#### 📊 Route Comparison")
            stats_df = pd.DataFrame({
                "Metric": ["📏 Distance", "🌳 Shade Coverage", "🌡️ Heat Exposure", "📐 Extra Distance"],
                "🔴 Fastest": [
                    f"{fast['distance_km']} km",
                    f"{fast['stats']['shade_pct']}%",
                    f"{fast['stats']['avg_temp_score']:.0%}",
                    "—",
                ],
                "🟢 CoolPath": [
                    f"{cool['distance_km']} km",
                    f"{cool['stats']['shade_pct']}%",
                    f"{cool['stats']['avg_temp_score']:.0%}",
                    f"+{cool.get('deviation_pct', 0)}%",
                ],
            })
            st.dataframe(stats_df, use_container_width=True, hide_index=True)

            # Improvement callout
            if result.get("routes_identical"):
                st.info("ℹ️ Both routes are identical — the fastest path already has good shade coverage in this area.")
            else:
                shade_gain = cool["stats"]["shade_pct"] - fast["stats"]["shade_pct"]
                if shade_gain > 0:
                    st.success(f"🌳 CoolPath gives **{shade_gain:.0f}% more shade** with only **+{cool.get('deviation_pct', 0)}% extra distance!**")
                else:
                    st.info("ℹ️ CoolPath found a route that avoids hotter zones while staying close to the fastest path.")

            # Route map with BOTH overlays
            route_map = create_base_map(zoom=13)

            # Add temperature overlay
            lst_img = str(Path(__file__).resolve().parent / "data" / "lst_heatmap.png")
            if os.path.exists(lst_img) and "route_lst" in st.session_state:
                folium.raster_layers.ImageOverlay(
                    image=lst_img,
                    bounds=st.session_state["route_lst"]["bounds"],
                    opacity=0.35,
                    name="🌡️ Temperature",
                ).add_to(route_map)

            # Add NDVI overlay
            ndvi_img = str(Path(__file__).resolve().parent / "data" / "ndvi_overlay.png")
            if os.path.exists(ndvi_img) and "route_ndvi" in st.session_state:
                folium.raster_layers.ImageOverlay(
                    image=ndvi_img,
                    bounds=st.session_state["route_ndvi"]["bounds"],
                    opacity=0.30,
                    name="🌳 Tree Canopy",
                ).add_to(route_map)

            # Fastest route (red dashed)
            folium.PolyLine(
                fast["coords"], color='#ef4444', weight=6, opacity=0.8,
                dash_array='10 5',
                popup=f"🔴 Fastest: {fast['distance_km']} km, shade {fast['stats']['shade_pct']}%",
            ).add_to(folium.FeatureGroup(name=f"🔴 Fastest ({fast['distance_km']} km)").add_to(route_map))

            # Cool route (green solid)
            folium.PolyLine(
                cool["coords"], color='#22c55e', weight=7, opacity=0.9,
                popup=f"🟢 CoolPath: {cool['distance_km']} km, shade {cool['stats']['shade_pct']}%",
            ).add_to(folium.FeatureGroup(name=f"🟢 CoolPath ({cool['distance_km']} km)").add_to(route_map))

            # Origin + dest markers
            origin_name = st.session_state.get("route_origin_name", "A")
            dest_name = st.session_state.get("route_dest_name", "B")

            folium.Marker(
                fast["coords"][0],
                popup=f"📍 {origin_name}",
                icon=folium.Icon(color='blue', icon='home', prefix='glyphicon'),
            ).add_to(route_map)

            folium.Marker(
                fast["coords"][-1],
                popup=f"🏁 {dest_name}",
                icon=folium.Icon(color='red', icon='flag', prefix='glyphicon'),
            ).add_to(route_map)

            # Fit bounds
            all_coords = fast["coords"] + cool["coords"]
            route_map.fit_bounds(all_coords)

            folium.LayerControl(collapsed=False).add_to(route_map)
            render_map(route_map, "route_map_v2")

    else:
        st.info("👆 Enter origin & destination above, then click **Find CoolPath**.")

        default_map = create_base_map()
        folium.Marker(
            [config.CENTER_LAT, config.CENTER_LON],
            popup="Madhapur, Hyderabad", icon=folium.Icon(color='blue'),
        ).add_to(default_map)
        render_map(default_map, "default_map_v2")


# ── Footer ──────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="text-align:center; color:#64748b; font-size:0.85rem; padding:1rem 0;">
    <b>CoolPath v2</b> — Climate-Aware Delivery Route Planner<br>
    MODIS LST · Sentinel-2 NDVI · OSMnx · Open-Meteo<br>
    Last updated: {datetime.now().strftime('%d %b %Y, %H:%M IST')}
</div>
""", unsafe_allow_html=True)
