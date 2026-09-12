def normalize_weather_data(weather):
    if weather is None:
        return None

    return {
        "time": weather.get("time"),
        "temperature_c": weather.get("temperature"),
        "humidity_percent": weather.get("humidity"),
        "wind_speed_mps": weather.get("wind_speed"),
        "wind_direction_deg": weather.get("wind_direction"),
        "rain_probability_percent": weather.get("rain_probability"),
        "rainfall_mm": weather.get("rainfall"),
        "visibility_m": weather.get("visibility"),
        "source": "Open-Meteo"
    }
    
def normalize_ocean_data(ocean):

    if ocean is None:
        return None

    return {
        "latitude": ocean.get("latitude"),
        "longitude": ocean.get("longitude"),
        "forecast_time": ocean.get("forecast_time"),

        "waves": {
            "significant_wave_height_m":
                ocean.get("wave", {}).get(
                    "significant_wave_height_m"
                ),

            "peak_wave_period_s":
                ocean.get("wave", {}).get(
                    "peak_wave_period_s"
                ),

            "mean_wave_period_s":
                ocean.get("wave", {}).get(
                    "mean_wave_period_s"
                ),

            "mean_wave_direction_deg":
                ocean.get("wave", {}).get(
                    "mean_wave_direction_deg"
                )
        },

        "wind": {
            "u_mps":
                ocean.get("wind", {}).get("u_mps"),

            "v_mps":
                ocean.get("wind", {}).get("v_mps")
        },

        "source": "INCOIS WW3"
    }


def normalize_sachet_alerts(alerts):

    normalized_alerts = []

    for alert in alerts:

        centroid = alert.get("centroid", "")

        latitude = None
        longitude = None

        if centroid:
            try:
                longitude, latitude = map(
                    float,
                    centroid.split(",")
                )
            except (ValueError, AttributeError):
                pass

        normalized_alerts.append({
            "id": alert.get("identifier"),

            "source": "SACHET-NDMA",

            "issuer": alert.get("alert_source"),

            "hazard": alert.get("disaster_type"),

            "severity": alert.get("severity"),

            "severity_level":
                alert.get("severity_level"),

            "start_time":
                alert.get("effective_start_time"),

            "end_time":
                alert.get("effective_end_time"),

            "area":
                alert.get("area_description"),

            "latitude": latitude,

            "longitude": longitude,

            "warning_message":
                alert.get("warning_message")
        })

    return normalized_alerts