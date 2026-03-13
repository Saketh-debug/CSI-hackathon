# CoolPath Project Features Overview

Based on the codebase scan (specifically [app.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/app.py), [config.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/config.py), and the `services/` directory), here is a pagewise breakdown of all features present in the **CoolPath** Streamlit application.

The application dynamically updates an auto-refreshing UI with data covering a 100km radius around Madhapur, Hyderabad, and caches computations for performance.

---

## Sidebar: Global Controls
Available on all pages, the sidebar provides global functionality and routing parameters:
- **Fetch Data Now**: Clears all cached raster data and routes to immediately fetch fresh satellite imagery.
- **Auto-Refresh**: Automatically refreshes the application every 10 minutes to stay up to date.
- **Routing Weights Sliders**: Global configurations to adjust the routing algorithm:
  - **Shade Importance**: Weight of NDVI (tree canopy) in route cost.
  - **Temperature Avoidance**: Weight of LST (heat) in route cost.
  - **Max Deviation**: Allowed detour distance limit (e.g., 1.3x) compared to the absolute fastest route.

---

## Page 1: 🌡️ Temperature Map
This tab acts as the thermal insight layer of the application.
- **Continuous Surface Temperature Heatmap**: Overlays a vibrant continuous color heatmap of the Land Surface Temperature (LST) derived from Google Earth Engine's MODIS satellite measurements over the Madhapur region map.
- **Key Temperature Statistics**: Calculates and displays the minimum (Coolest Zone), average, and maximum (Hottest Zone) temperatures in the current bounds.
- **24hr Weather Forecast Chart**: Toggled via a checkbox, this fetches and displays a bar chart of the day's hourly temperatures and "feels like" temperatures, along with the current textual weather condition (e.g., "Clear", "Cloudy") leveraging the `services.weather_forecast` module.

---

## Page 2: 🌳 Tree Canopy Map
This tab visualizes shade availability using vegetation data.
- **Continuous Density Canopy Map**: Overlays a green-to-brown continuous density map based on NDVI calculations (Normalized Difference Vegetation Index) from Sentinel-2 satellite data.
- **Canopy Density Breakdown**: Calculates and displays the overall Max NDVI, and automatically categorizes the region into percentage metrics:
  - **Dense Canopy** (NDVI > 0.4)
  - **Moderate Canopy** (NDVI between 0.2 and 0.4)
  - **Exposed Area** (NDVI ≤ 0.2)

---

## Page 3: 🛵 CoolPath Router
This is the core functional feature of the application, used by riders to plan the safest and coolest routes.
- **Smart Location Setup**: 
  - Allows text-based routing for Origin and Destination addresses using `Nominatim` geocoding (restricted automatically to a valid radius).
  - Contains a built-in **📍 My Location** button to automatically pull device GPS coordinates and plot the user on the map.
- **Climate-Aware Route Comparison**: 
  - Computes the shortest distance path ("Fastest") versus the climate-optimized path ("CoolPath") using vectorized climate weighting algorithms from [services/routing.py](file:///c:/Users/aruna/OneDrive/Desktop/map%20fetcher/services/routing.py) that balance distance, heat exposure, and shade.
- **Comparison Data Table**: Renders a clear comparative matrix displaying:
  - Distance (km)
  - Shade Coverage (%)
  - Heat Exposure (%)
  - Extra Distance (%) for selecting the CoolPath.
- **Multi-Overlay Map Visualization**:
  - Plots both the fastest route (red dashed) and the CoolPath (green solid).
  - Supports blending both the temperature heatmap layer and the tree canopy overlay directly on the routing map to visually explain *why* the cool route chose that specific path.
