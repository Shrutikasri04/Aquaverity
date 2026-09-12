from weather_api import get_weather, get_hourly_weather
from ocean_api import get_ocean_data
from sachet_api import get_alerts
from normalizer import (
    normalize_weather_data,
    normalize_ocean_data,
    normalize_sachet_alerts
)
from hazard_detector import detect_hazards
from risk_engine import calculate_risk
from alert_filter import filter_alerts_by_location

def generate_safety_recommendation(risk):
    risk_level = risk.get("risk_level", "LOW")

    if risk_level == "EXTREME":
        return {
            "level": "EXTREME",
            "action": "DO_NOT_VENTURE",
            "message": (
                "Do not venture into the sea. "
                "Follow official warnings and seek appropriate safety measures."
            )
        }

    elif risk_level == "HIGH":
        return {
            "level": "HIGH",
            "action": "AVOID_SEA_ACTIVITY",
            "message": (
                "Avoid sea activity. "
                "Follow official weather and marine warnings."
            )
        }

    elif risk_level == "MODERATE":
        return {
            "level": "MODERATE",
            "action": "EXERCISE_CAUTION",
            "message": (
                "Exercise caution. "
                "Check official marine and weather warnings before "
                "venturing into the sea."
            )
        }

    else:
        return {
            "level": "LOW",
            "action": "MONITOR",
            "message": (
                "No major hazards detected. "
                "Continue monitoring weather, marine conditions "
                "and official alerts."
            )
        }



def get_marine_conditions(latitude, longitude, target_time):

    errors = []

    # ---------------- WEATHER ----------------
    weather_raw = get_weather(latitude, longitude)

    if weather_raw and weather_raw.get("error"):
        errors.append({
            "source": "Open-Meteo",
            "message": weather_raw.get("message")
        })
        weather = None
    else:
        weather = get_hourly_weather(weather_raw, target_time)
        weather = normalize_weather_data(weather)

    # ---------------- OCEAN ----------------
    ocean_raw = get_ocean_data(latitude, longitude, target_time)

    if ocean_raw and ocean_raw.get("error"):
        errors.append({
            "source": "INCOIS WW3",
            "message": ocean_raw.get("message")
        })
        ocean = None
    else:
        ocean = normalize_ocean_data(ocean_raw)

    # ---------------- SACHET ----------------
    sachet_raw = get_alerts()

    if sachet_raw.get("error"):
        errors.append({
            "source": "SACHET-NDMA",
            "message": sachet_raw.get("message")
        })
        sachet_alerts = []
    else:
        sachet_alerts = normalize_sachet_alerts(
            sachet_raw.get("data", [])
        )

        sachet_alerts = filter_alerts_by_location(
            sachet_alerts,
            latitude,
            longitude,
            target_time,
            radius_km=150
        )

    # ---------------- HAZARDS ----------------
    hazards = detect_hazards(
        weather,
        ocean,
        sachet_alerts
    )

    # ---------------- RISK ----------------
    risk = calculate_risk(hazards)

    # ---------------- SAFETY ----------------
    safety = generate_safety_recommendation(risk)

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },

        "forecast_time": target_time,

        "weather": weather,

        "ocean": ocean,

        "alerts": sachet_alerts,

        "hazards": hazards,

        "risk": risk,

        "safety": safety,

        "errors": errors,

        "sources": [
            "Open-Meteo Weather API",
            "INCOIS WW3",
            "SACHET-NDMA"
        ]
    }