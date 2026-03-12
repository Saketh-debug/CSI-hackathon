"""
CoolPath Configuration
Centre: Madhapur, Hyderabad
Radius: 50 km
"""

# ── Geographic centre ───────────────────────────────────────
CENTER_LAT = 17.4474
CENTER_LON = 78.3762
RADIUS_KM = 50
RADIUS_M = RADIUS_KM * 1000

# ── Heatmap raster resolution ───────────────────────────────
HEATMAP_RESOLUTION = 80    # NxN grid for continuous heatmap image

# ── GEE ─────────────────────────────────────────────────────
GEE_PROJECT = "umbra-intelligence"
GEE_SERVICE_ACCOUNT = "pixel-pioneers@umbra-intelligence.iam.gserviceaccount.com"
GEE_CREDENTIALS_FILE = "gee-credentials.json"

# ── Temperature thresholds (°C) ─────────────────────────────
TEMP_DANGER = 40       # 🔴 DANGER
TEMP_CAUTION = 35      # 🟡 CAUTION
                       # below → 🟢 SAFE

# ── Routing ─────────────────────────────────────────────────
MAX_DEVIATION = 1.3    # cool route can be at most 1.3× fastest distance
SHADE_WEIGHT = 0.5     # how much NDVI (shade) contributes to cost
TEMP_WEIGHT = 0.3      # how much temperature contributes to cost
ROUTING_GRAPH_RADIUS = 15000   # meters — graph download radius around route

# ── Cache TTL (seconds) ─────────────────────────────────────
TEMP_CACHE_TTL = 3600       # 1 hour
NDVI_CACHE_TTL = 86400      # 24 hours

# ── Map defaults ────────────────────────────────────────────
MAP_ZOOM = 11
