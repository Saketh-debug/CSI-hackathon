"""
Static knowledge base describing the CoolPath platform pages and features.
injected into every /api/chat prompt so EcoAssist can answer "how does X work" questions.
"""

WEBSITE_KNOWLEDGE = """
## CoolPath Platform — Page & Feature Reference

### Home Page (/)
Landing page for the CoolPath environmental monitoring platform focused on Hyderabad.
Highlights: real-time temperature, air quality snapshot, quick links to all features.

### Dashboard (/dashboard)
Overview of current environmental stats for the Hyderabad region:
- Average surface temperature (°C)
- Min/Max surface temperature
- Tree canopy coverage % (dense, moderate, exposed)
- Shade coverage %
- Live LST heatmap image and NDVI canopy overlay image
Data is fetched from Google Earth Engine (Sentinel-2 satellite) and cached for 10 minutes.

### Heatmap (/heatmap)
Interactive Leaflet map showing:
- Surface temperature overlay (LST) — red = hot, green = cooler
- NDVI tree canopy overlay toggle — green = dense canopy, yellow = moderate, red = sparse/bare
- 24-hour forecast bar chart showing hourly temperature and "feels like" temperature
- Weather code / condition icon for each hour
Toggles: show/hide heatmap layer, canopy layer, forecast card.

### Tree Canopy (/canopy)
Dedicated view of the NDVI (Normalized Difference Vegetation Index) tree density map.
Color legend: dark green = high NDVI (>0.4, dense), yellow-green = moderate (0.2–0.4), red/brown = sparse (<0.2).
Statistics shown: max NDVI, dense %, moderate %, sparse % coverage.
Used to identify areas needing plantation or green infrastructure.

### Cool Path Router (/router) — also Mobile version at /mobile-router
Enter an origin and destination address in Hyderabad.
The system returns two routes:
  1. Fastest Route: shortest/quickest path (like standard navigation)
  2. Coolest Route: optimized path avoiding hot zones, favouring shaded roads and green corridors
Both routes show: distance (km), shade coverage %, average temperature score.
Parameters: shade weight, temperature weight, max deviation multiplier.
The routing uses OpenStreetMap road graph + LST/NDVI satellite data.

### Messaging / Thermal Alerts (/messaging)
Send SMS heat/weather alerts to personnel. Three modes:
  1. Single Alert — send to one phone number
  2. Bulk Dispatch — manually add multiple phone numbers + one message
  3. CSV Broadcast — upload a CSV (columns: Phone, Name, Dept) + template with {{name}} personalisation
Use cases: plantation drives, heat emergency notifications, community alerts.

### APIs (for developers)
- GET /api/temperature — current LST stats + heatmap image URL
- GET /api/canopy — NDVI stats + overlay image URL
- GET /api/forecast?lat=&lon= — 24h hourly weather from Open-Meteo
- GET /api/summary — all dashboard stats in one call
- POST /api/route — compute fastest + coolest route

### Coverage Area
The platform covers a 100 km radius centred on Madhapur, Hyderabad (17.4474°N, 78.3762°E).
All routing must start and end within this area.
"""
