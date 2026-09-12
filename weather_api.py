import requests


def validate_location(latitude, longitude):

    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")


def get_weather(latitude, longitude):

    validate_location(latitude, longitude)

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m,"
            "wind_direction_10m,"
            "precipitation_probability,"
            "precipitation,"
            "visibility"
        ),
        "forecast_days": 7,
        "timezone": "UTC"
    }

    try:

        headers = {
            "User-Agent": "ORCA-Weather-Safety/1.0"
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:

        return {
            "error": True,
            "source": "Open-Meteo",
            "message": str(e)
        }


def get_hourly_weather(data, target_time):

    if data is None:
        return None

    if data.get("error"):
        return None

    hourly = data.get("hourly")

    if not hourly:
        return None

    target = target_time[:16]

    for i, time in enumerate(hourly.get("time", [])):

        if time == target:

            return {
                "time": time,
                "temperature": hourly["temperature_2m"][i],
                "humidity": hourly["relative_humidity_2m"][i],
                "wind_speed": hourly["wind_speed_10m"][i],
                "wind_direction": hourly["wind_direction_10m"][i],
                "rain_probability": hourly["precipitation_probability"][i],
                "rainfall": hourly["precipitation"][i],
                "visibility": hourly["visibility"][i]
            }

    return None