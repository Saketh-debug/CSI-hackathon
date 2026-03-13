"""
Weather Forecast Service — Open-Meteo API
Used ONLY for displaying hourly forecast chart, NOT for heatmap.
"""

import sys
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def fetch_hourly_forecast(lat=None, lon=None):
    """
    Fetch 24-hour hourly forecast for a single location.
    Returns dict with time/temp/apparent arrays + location name.
    """
    lat = lat or config.CENTER_LAT
    lon = lon or config.CENTER_LON

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m",
        "current": "temperature_2m,apparent_temperature,weather_code",
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        hourly = data.get("hourly", {})

        return {
            "current_temp": current.get("temperature_2m", 0),
            "current_apparent": current.get("apparent_temperature", 0),
            "weather_code": current.get("weather_code", 0),
            "times": hourly.get("time", []),
            "temps": hourly.get("temperature_2m", []),
            "apparent": hourly.get("apparent_temperature", []),
            "humidity": hourly.get("relative_humidity_2m", []),
            "wind": hourly.get("wind_speed_10m", []),
        }
    except Exception as e:
        print(f"[Forecast] API error: {e}")
        return None


def get_weather_description(code):
    """Convert WMO weather code to human-readable description."""
    codes = {
        0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅",
        3: "Overcast ☁️", 45: "Foggy 🌫️", 48: "Rime fog 🌫️",
        51: "Light drizzle 🌦️", 53: "Drizzle 🌦️", 55: "Heavy drizzle 🌧️",
        61: "Light rain 🌧️", 63: "Rain 🌧️", 65: "Heavy rain ⛈️",
        71: "Light snow ❄️", 73: "Snow ❄️", 75: "Heavy snow ❄️",
        80: "Light showers 🌦️", 81: "Showers 🌧️", 82: "Heavy showers ⛈️",
        95: "Thunderstorm ⛈️", 96: "Thunderstorm + hail 🌩️",
    }
    return codes.get(code, f"Code {code}")


if __name__ == "__main__":
    data = fetch_hourly_forecast()
    if data:
        print(f"Current: {data['current_temp']}°C (feels {data['current_apparent']}°C)")
        print(f"Weather: {get_weather_description(data['weather_code'])}")
