"""
CoolPath FastAPI Backend
Thin REST wrapper around the existing streamlit-demo/services/ modules.
Placed inside streamlit-demo/ so all relative sys.path resolution in
services/*.py continues to work without modification.
"""

import sys
import threading
import numpy as np
from pathlib import Path
from contextlib import asynccontextmanager

# ── Ensure project root (streamlit-demo/) is on path ───────
ROOT = Path(__file__).resolve().parent.parent   # = streamlit-demo/
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os

# ── Static file paths ───────────────────────────────────────
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Cache warm-up lock (prevents concurrent first-run races) ─
_warmup_lock = threading.Lock()


# ── Startup: eagerly generate PNG tiles ────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm caches at startup so PNGs exist before first request."""
    from services.surface_temp import fetch_lst_raster
    from services.ndvi import fetch_ndvi_raster

    print("[Backend] Warming up LST cache...")
    try:
        fetch_lst_raster()
        print("[Backend] ✅ LST cache ready")
    except Exception as e:
        print(f"[Backend] ⚠️ LST warm-up failed: {e}")

    print("[Backend] Warming up NDVI cache...")
    try:
        fetch_ndvi_raster()
        print("[Backend] ✅ NDVI cache ready")
    except Exception as e:
        print(f"[Backend] ⚠️ NDVI warm-up failed: {e}")

    yield  # server runs here


# ── App ─────────────────────────────────────────────────────
app = FastAPI(
    title="CoolPath API",
    description="Climate-aware routing backend for Hyderabad",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins so LAN devices (other phones/laptops) can connect
# When accessed via a LAN IP the browser Origin header will be http://<ip>:5173,
# which wouldn't match a localhost whitelist, so we open it up for dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated PNG overlays
app.mount("/static", StaticFiles(directory=str(DATA_DIR)), name="static")


# ═══════════════════════════════════════════════════════════
# Pydantic models
# ═══════════════════════════════════════════════════════════
class RouteRequest(BaseModel):
    origin: str
    destination: str
    shade_weight: float = 0.5
    temp_weight: float = 0.3
    max_deviation: float = 1.3


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]
    language: Optional[str] = "English"

class SingleMessageRequest(BaseModel):
    phone: str
    message: str

class BulkMessageRequest(BaseModel):
    phones: List[str]
    message: str


# ═══════════════════════════════════════════════════════════
# ENDPOINT: GET /api/temperature
# ═══════════════════════════════════════════════════════════
@app.get("/api/temperature")
def get_temperature():
    """
    Returns surface temperature stats + URL to heatmap PNG overlay.
    Computes avg_temp from the grid (not available in raw service output).
    """
    from services.surface_temp import fetch_lst_raster
    import time

    try:
        data = fetch_lst_raster()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Temperature service error: {e}")

    grid = np.array(data["grid"])
    avg_temp = float(np.nanmean(grid))

    # Cache-bust URL so browsers always fetch the freshest tile
    ts = int(data.get("timestamp", time.time()))

    return {
        "min_temp": round(data["min_temp"], 1),
        "max_temp": round(data["max_temp"], 1),
        "avg_temp": round(avg_temp, 1),
        "bounds": data["bounds"],
        "timestamp": ts,
        "image_url": f"/static/lst_heatmap.png?ts={ts}",
    }


# ═══════════════════════════════════════════════════════════
# ENDPOINT: GET /api/canopy
# ═══════════════════════════════════════════════════════════
@app.get("/api/canopy")
def get_canopy():
    """
    Returns NDVI tree canopy stats + URL to NDVI overlay PNG.
    Normalises dense + moderate + sparse to sum exactly to 100%.
    """
    from services.ndvi import fetch_ndvi_raster
    import time

    try:
        data = fetch_ndvi_raster()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Canopy service error: {e}")

    grid = np.array(data["grid"])

    raw_dense    = float(np.mean(grid > 0.4) * 100)
    raw_moderate = float(np.mean((grid > 0.2) & (grid <= 0.4)) * 100)
    raw_sparse   = float(np.mean(grid <= 0.2) * 100)

    # Normalise to exactly 100 (floating-point safety)
    total = raw_dense + raw_moderate + raw_sparse or 100.0
    dense_pct    = round(raw_dense    / total * 100, 1)
    moderate_pct = round(raw_moderate / total * 100, 1)
    sparse_pct   = round(100 - dense_pct - moderate_pct, 1)   # remainder avoids rounding drift

    ts = int(data.get("timestamp", time.time()))

    return {
        "max_ndvi":     round(float(data["max_ndvi"]), 3),
        "min_ndvi":     round(float(data["min_ndvi"]), 3),
        "dense_pct":    dense_pct,
        "moderate_pct": moderate_pct,
        "sparse_pct":   sparse_pct,
        "bounds":       data["bounds"],
        "timestamp":    ts,
        "image_url":    f"/static/ndvi_overlay.png?ts={ts}",
    }


# ═══════════════════════════════════════════════════════════
# ENDPOINT: GET /api/forecast
# ═══════════════════════════════════════════════════════════
@app.get("/api/forecast")
def get_forecast(lat: Optional[float] = None, lon: Optional[float] = None):
    """
    Returns 24-hour hourly forecast from Open-Meteo.
    Returns 503 with fallback empty arrays if external API fails.
    """
    from services.weather_forecast import fetch_hourly_forecast, get_weather_description

    data = fetch_hourly_forecast(lat=lat, lon=lon)

    if data is None:
        # Graceful degradation — don't crash, return empty payload with flag
        return {
            "available": False,
            "current_temp": None,
            "current_apparent": None,
            "weather_code": None,
            "weather_description": None,
            "times": [],
            "temps": [],
            "apparent": [],
            "humidity": [],
            "wind": [],
        }

    return {
        "available": True,
        "current_temp":     data["current_temp"],
        "current_apparent": data["current_apparent"],
        "weather_code":     data["weather_code"],
        "weather_description": get_weather_description(data["weather_code"]),
        "times":    data["times"],
        "temps":    data["temps"],
        "apparent": data["apparent"],
        "humidity": data["humidity"],
        "wind":     data["wind"],
    }


# ═══════════════════════════════════════════════════════════
# ENDPOINT: GET /api/summary  (Dashboard stats)
# ═══════════════════════════════════════════════════════════
@app.get("/api/summary")
def get_summary():
    """
    Aggregated stats for the Dashboard page.
    Returns all values in °C (not °F — frontend converts if needed).
    """
    from services.surface_temp import fetch_lst_raster
    from services.ndvi import fetch_ndvi_raster
    import time

    try:
        lst  = fetch_lst_raster()
        ndvi = fetch_ndvi_raster()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Summary service error: {e}")

    temp_grid = np.array(lst["grid"])
    ndvi_grid = np.array(ndvi["grid"])

    avg_temp = round(float(np.nanmean(temp_grid)), 1)

    raw_dense    = float(np.mean(ndvi_grid > 0.4) * 100)
    raw_moderate = float(np.mean((ndvi_grid > 0.2) & (ndvi_grid <= 0.4)) * 100)
    raw_sparse   = float(np.mean(ndvi_grid <= 0.2) * 100)
    total = raw_dense + raw_moderate + raw_sparse or 100.0
    dense_pct    = round(raw_dense    / total * 100, 1)
    moderate_pct = round(raw_moderate / total * 100, 1)
    sparse_pct   = round(100 - dense_pct - moderate_pct, 1)

    # shade_pct = pixels with NDVI > 0.25 (same threshold as routing)
    shade_pct = round(float(np.mean(ndvi_grid > 0.25) * 100), 1)

    ts = int(time.time())

    return {
        # Temperatures in °C
        "avg_temp_c":  avg_temp,
        "min_temp_c":  round(lst["min_temp"], 1),
        "max_temp_c":  round(lst["max_temp"], 1),
        # Convenience °F conversions for Dashboard (currently shows °F)
        "avg_temp_f":  round(avg_temp * 9/5 + 32, 1),
        "min_temp_f":  round(lst["min_temp"] * 9/5 + 32, 1),
        "max_temp_f":  round(lst["max_temp"] * 9/5 + 32, 1),
        # Canopy
        "canopy_pct":    dense_pct,
        "moderate_pct":  moderate_pct,
        "exposed_pct":   sparse_pct,
        "shade_pct":     shade_pct,
        "max_ndvi":      round(float(ndvi["max_ndvi"]), 3),
        # Image URLs with cache-busting
        "lst_image_url":  f"/static/lst_heatmap.png?ts={ts}",
        "ndvi_image_url": f"/static/ndvi_overlay.png?ts={ts}",
        "lst_bounds":  lst["bounds"],
        "ndvi_bounds": ndvi["bounds"],
        "timestamp":   ts,
    }


# ═══════════════════════════════════════════════════════════
# ENDPOINT: POST /api/route
# ═══════════════════════════════════════════════════════════
@app.post("/api/route")
def compute_route(req: RouteRequest):
    """
    Geocode origin + destination, run climate-aware routing.
    Returns fastest + coolest route coords + stats.
    All error states from routing.py are mapped to HTTP errors.
    """
    import copy
    import config as cfg

    from services.routing import (
        geocode_location, is_within_region,
        get_cached_graph, find_routes,
    )
    from services.surface_temp import fetch_lst_raster
    from services.ndvi import fetch_ndvi_raster

    # Apply routing weights from request
    cfg.SHADE_WEIGHT  = req.shade_weight
    cfg.TEMP_WEIGHT   = req.temp_weight
    cfg.MAX_DEVIATION = req.max_deviation

    # ── Geocode ────────────────────────────────────────────
    origin_coords = geocode_location(req.origin)
    if not origin_coords:
        raise HTTPException(status_code=400, detail=f"Could not geocode origin: '{req.origin}'. Try a more specific Hyderabad address.")

    dest_coords = geocode_location(req.destination)
    if not dest_coords:
        raise HTTPException(status_code=400, detail=f"Could not geocode destination: '{req.destination}'. Try a more specific Hyderabad address.")

    # ── Boundary check ─────────────────────────────────────
    if not is_within_region(origin_coords[0], origin_coords[1]):
        raise HTTPException(status_code=400, detail=f"Origin '{origin_coords[2]}' is outside the {cfg.RADIUS_KM}km coverage area around Madhpur.")

    if not is_within_region(dest_coords[0], dest_coords[1]):
        raise HTTPException(status_code=400, detail=f"Destination '{dest_coords[2]}' is outside the {cfg.RADIUS_KM}km coverage area.")

    # ── Load data + graph ──────────────────────────────────
    try:
        lst_data  = fetch_lst_raster()
        ndvi_data = fetch_ndvi_raster()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not load climate data: {e}")

    try:
        G_original = get_cached_graph()
        G = copy.deepcopy(G_original)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Road graph unavailable: {e}")

    # ── Compute routes ─────────────────────────────────────
    result = find_routes(
        G,
        origin_coords[0], origin_coords[1],
        dest_coords[0],   dest_coords[1],
        lst_data, ndvi_data,
    )

    if "error" in result:
        err = result["error"]
        if "too close" in err.lower():
            raise HTTPException(status_code=400, detail=err)
        raise HTTPException(status_code=404, detail=err)

    fast = result["fastest"]
    cool = result["coolest"]

    return {
        "origin": {
            "address": origin_coords[2],
            "lat": origin_coords[0],
            "lon": origin_coords[1],
        },
        "destination": {
            "address": dest_coords[2],
            "lat": dest_coords[0],
            "lon": dest_coords[1],
        },
        "fastest": {
            "coords":      fast["coords"],         # [[lat,lon], ...]
            "distance_km": fast["distance_km"],
            "duration_min": fast.get("duration_min", 0),
            "stats": {
                "shade_pct":      fast["stats"]["shade_pct"],
                "avg_temp_score": round(fast["stats"]["avg_temp_score"], 3),
                "avg_shade":      round(fast["stats"]["avg_shade"], 3),
            },
        },
        "coolest": {
            "coords":        cool["coords"],
            "distance_km":   cool["distance_km"],
            "duration_min":  cool.get("duration_min", 0),
            "deviation_pct": cool.get("deviation_pct", 0),
            "stats": {
                "shade_pct":      cool["stats"]["shade_pct"],
                "avg_temp_score": round(cool["stats"]["avg_temp_score"], 3),
                "avg_shade":      round(cool["stats"]["avg_shade"], 3),
            },
        },
        "routes_identical": result.get("routes_identical", False),
    }


# ═══════════════════════════════════════════════════════════
# ENDPOINT: POST /api/chat  (EcoAssist AI Bot)
# ═══════════════════════════════════════════════════════════
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    EcoAssist AI chatbot powered by local Llama 3 via Ollama.
    Detects intent from the user message, fetches live platform data
    (weather / canopy / temperature) only when relevant, then calls
    Ollama at localhost:11434 with the assembled context.
    """
    import json
    import requests as _requests

    from backend.website_knowledge import WEBSITE_KNOWLEDGE

    # ── 1. System prompt ───────────────────────────────────
    SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "rag_system_prompt.txt"
    try:
        system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    except Exception:
        system_prompt = "You are EcoAssist, an AI assistant for the CoolPath environmental platform."

    # ── 2. Intent detection ────────────────────────────────
    msg_lower = req.message.lower()

    WEATHER_KEYWORDS = ["weather", "temperature", "rain", "forecast", "hot", "humid",
                        "wind", "cold", "degrees", "°", "mausam", "baarish", "garmi",
                        "velayati", "vaayu"]
    CANOPY_KEYWORDS  = ["tree", "canopy", "ndvi", "green", "forest", "plants", "shade",
                        "vegetation", "plantation", "pedalu", "chetlu"]
    TEMP_KEYWORDS    = ["surface temp", "heatmap", "lst", "heat", "thermal"]

    want_weather = any(w in msg_lower for w in WEATHER_KEYWORDS)
    want_canopy  = any(w in msg_lower for w in CANOPY_KEYWORDS)
    want_temp    = any(w in msg_lower for w in TEMP_KEYWORDS)

    # ── 3. Fetch live data for detected intents ────────────
    live_data_parts = []

    if want_weather:
        try:
            from services.weather_forecast import fetch_hourly_forecast, get_weather_description
            wdata = fetch_hourly_forecast()
            if wdata:
                live_data_parts.append(
                    f"[LIVE WEATHER DATA]\n"
                    f"Current temperature: {wdata['current_temp']}°C\n"
                    f"Feels like: {wdata['current_apparent']}°C\n"
                    f"Condition: {get_weather_description(wdata['weather_code'])}\n"
                    f"Next 6h temperatures (°C): {wdata['temps'][:6]}\n"
                    f"Next 6h humidity (%): {wdata['humidity'][:6]}\n"
                    f"Next 6h wind (km/h): {wdata['wind'][:6]}"
                )
        except Exception as e:
            live_data_parts.append(f"[WEATHER DATA] Unavailable: {e}")

    if want_canopy or want_temp:
        try:
            from services.ndvi import fetch_ndvi_raster
            ndvi = fetch_ndvi_raster()
            ndvi_grid = np.array(ndvi["grid"])
            dense    = round(float(np.mean(ndvi_grid > 0.4) * 100), 1)
            moderate = round(float(np.mean((ndvi_grid > 0.2) & (ndvi_grid <= 0.4)) * 100), 1)
            sparse   = round(100 - dense - moderate, 1)
            live_data_parts.append(
                f"[LIVE CANOPY DATA]\n"
                f"Dense canopy (NDVI>0.4): {dense}%\n"
                f"Moderate canopy (0.2–0.4): {moderate}%\n"
                f"Sparse/exposed (< 0.2): {sparse}%\n"
                f"Max NDVI: {round(float(ndvi['max_ndvi']), 3)}"
            )
        except Exception as e:
            live_data_parts.append(f"[CANOPY DATA] Unavailable: {e}")

    if want_temp:
        try:
            from services.surface_temp import fetch_lst_raster
            lst = fetch_lst_raster()
            lst_grid = np.array(lst["grid"])
            avg_t = round(float(np.nanmean(lst_grid)), 1)
            live_data_parts.append(
                f"[LIVE SURFACE TEMPERATURE]\n"
                f"Average: {avg_t}°C\n"
                f"Min: {round(lst['min_temp'], 1)}°C\n"
                f"Max: {round(lst['max_temp'], 1)}°C"
            )
        except Exception as e:
            live_data_parts.append(f"[SURFACE TEMP] Unavailable: {e}")

    live_data_section = (
        "\n\n---\n" + "\n\n".join(live_data_parts)
        if live_data_parts else ""
    )

    # ── 4. Build full system message ───────────────────────
    lang_directive = ""
    headings = ""
    if req.language is not None and req.language.lower() != "english":
        lang_lower = req.language.lower()
        if lang_lower == "telugu":
            headings = "\nUse these exact headings literally: 'సమాధానం' instead of 'Answer', 'వివరాలు' instead of 'Details', 'సూచనలు' instead of 'Suggestions'."
        elif lang_lower == "hindi":
            headings = "\nUse these exact headings literally: 'उत्तर' instead of 'Answer', 'विवरण' instead of 'Details', 'सुझाव' instead of 'Suggestions'."

        lang_directive = f"""

=========================================
CRITICAL OVERRIDE - LANGUAGE INSTRUCTION:
No matter what language the user writes in, and no matter what previous instructions say, you MUST output your ENTIRE response exclusively in the {req.language} language using its native script.
Do NOT reply in English. Do NOT provide English translations alongside the {req.language} text. {headings}
=========================================
"""

    full_system = (
        system_prompt
        + "\n\n---\n"
        + "## Platform Knowledge\n"
        + WEBSITE_KNOWLEDGE
        + live_data_section
        + lang_directive
    )

    # ── 5. Build Ollama messages list ──────────────────────
    messages = [{"role": "system", "content": full_system}]

    # Append history (last 8 turns to keep context window sane)
    for turn in req.history[-8:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": req.message})

    # ── 6. Call Ollama ─────────────────────────────────────
    OLLAMA_URL = "http://localhost:11434/api/chat"

    try:
        ollama_resp = _requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3",
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                    "num_predict": 512,
                },
            },
            timeout=120,
        )
        ollama_resp.raise_for_status()
        result = ollama_resp.json()
        reply = result["message"]["content"].strip()
    except _requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Please start it with: ollama serve",
        )
    except _requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Llama 3 took too long to respond.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    return {"reply": reply}


# ═══════════════════════════════════════════════════════════
# ENDPOINTS: POST /api/messaging (WhatsApp via Twilio)
# ═══════════════════════════════════════════════════════════
from services.whatsapp import send_whatsapp_message

@app.post("/api/messaging/single")
def send_single_message(req: SingleMessageRequest):
    """Sends a single WhatsApp message and returns the tracking SID."""
    sid = send_whatsapp_message(req.phone, req.message)
    if not sid:
        raise HTTPException(
            status_code=500,
            detail="Failed to send WhatsApp message. Check Twilio configuration or phone number format."
        )
    return {"status": "success", "sid": sid, "phone": req.phone}

@app.post("/api/messaging/bulk")
def send_bulk_messages(req: BulkMessageRequest):
    """Sends identical WhatsApp messages to multiple recipients."""
    results = []
    success_count: int = 0
    for phone in req.phones:
        sid = send_whatsapp_message(phone, req.message)
        if sid:
            success_count += 1
            results.append({"phone": phone, "status": "success", "sid": sid})
        else:
            results.append({"phone": phone, "status": "failed"})
            
    return {
        "status": "completed",
        "total": len(req.phones),
        "successful": success_count,
        "results": results
    }

# ═══════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "CoolPath API v2"}

