"""
ML Temperature Predictor
Trains a RandomForestRegressor on historical temperature data from Open-Meteo
to predict future temperatures at any (lat, lon, datetime).
"""

import sys
import json
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "temp_model.pkl"


def fetch_historical_data(center_lat=None, center_lon=None, days_back=90):
    """
    Fetch historical hourly temperature data from Open-Meteo Archive API.
    Returns a pandas DataFrame.
    """
    center_lat = center_lat or config.CENTER_LAT
    center_lon = center_lon or config.CENTER_LON
    
    end_date = datetime.now() - timedelta(days=5)  # API has 5-day delay
    start_date = end_date - timedelta(days=days_back)
    
    # Sample a few points around the center
    offsets = [
        (0, 0), (0.1, 0), (-0.1, 0), (0, 0.1), (0, -0.1),
        (0.05, 0.05), (-0.05, 0.05), (0.05, -0.05), (-0.05, -0.05),
    ]
    
    all_records = []
    
    for dlat, dlon in offsets:
        lat = round(center_lat + dlat, 4)
        lon = round(center_lon + dlon, 4)
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "hourly": "temperature_2m,apparent_temperature",
            "timezone": "Asia/Kolkata",
        }
        
        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            apparent = hourly.get("apparent_temperature", [])
            
            for t, temp, app in zip(times, temps, apparent):
                if temp is not None:
                    dt = datetime.fromisoformat(t)
                    all_records.append({
                        "lat": lat,
                        "lon": lon,
                        "month": dt.month,
                        "day_of_week": dt.weekday(),
                        "hour": dt.hour,
                        "temperature": temp,
                        "apparent_temperature": app or temp,
                    })
        except Exception as e:
            print(f"[ML] Failed to fetch historical for ({lat}, {lon}): {e}")
    
    return pd.DataFrame(all_records)


def train_model(df=None, days_back=90):
    """
    Train a RandomForestRegressor to predict temperature.
    Features: lat, lon, month, day_of_week, hour
    Target: temperature
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import r2_score, mean_absolute_error
    import joblib
    
    if df is None or df.empty:
        print("[ML] Fetching historical training data...")
        df = fetch_historical_data(days_back=days_back)
    
    if df.empty:
        print("[ML] No training data available")
        return None
    
    print(f"[ML] Training on {len(df)} samples...")
    
    features = ["lat", "lon", "month", "day_of_week", "hour"]
    X = df[features]
    y = df["temperature"]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"[ML] R² = {r2:.4f}, MAE = {mae:.2f}°C")
    
    # Save model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"[ML] Model saved to {MODEL_PATH}")
    
    return {"r2": r2, "mae": mae, "samples": len(df)}


def predict_temperature(lat, lon, target_datetime=None):
    """
    Predict temperature at a given (lat, lon) and datetime.
    Returns predicted temperature in °C.
    """
    import joblib
    
    if not MODEL_PATH.exists():
        print("[ML] No trained model found. Training now...")
        train_model(days_back=30)
    
    if not MODEL_PATH.exists():
        return config.TEMP_CAUTION  # fallback
    
    model = joblib.load(MODEL_PATH)
    
    if target_datetime is None:
        target_datetime = datetime.now()
    
    features = np.array([[
        lat, lon,
        target_datetime.month,
        target_datetime.weekday(),
        target_datetime.hour,
    ]])
    
    prediction = model.predict(features)[0]
    return round(prediction, 1)


def predict_grid(center_lat=None, center_lon=None, target_datetime=None, n_points=25):
    """Predict temperatures for a grid of points at a future datetime."""
    from services.temperature import generate_grid
    
    center_lat = center_lat or config.CENTER_LAT
    center_lon = center_lon or config.CENTER_LON
    
    grid = generate_grid(center_lat, center_lon, config.RADIUS_KM, n_points)
    
    results = []
    for lat, lon in grid:
        temp = predict_temperature(lat, lon, target_datetime)
        
        if temp >= config.TEMP_DANGER:
            level = "DANGER"
        elif temp >= config.TEMP_CAUTION:
            level = "CAUTION"
        else:
            level = "SAFE"
        
        results.append({
            "lat": lat, "lon": lon,
            "predicted_temp": temp, "level": level,
        })
    
    return results


# ── Self-test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("Training temperature prediction model...")
    result = train_model(days_back=30)
    if result:
        print(f"\nModel trained: R²={result['r2']:.3f}, MAE={result['mae']:.1f}°C")
        
        # Test prediction
        temp = predict_temperature(config.CENTER_LAT, config.CENTER_LON)
        print(f"Predicted temperature at Madhapur now: {temp}°C")
