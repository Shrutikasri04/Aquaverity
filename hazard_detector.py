def detect_hazards(weather, ocean, alerts):

    hazards = []

    # -------------------------
    # WEATHER HAZARDS
    # -------------------------

    if weather:

        wind_speed = weather.get("wind_speed_mps")

        if wind_speed is not None and wind_speed >= 15:
            hazards.append({
                "type": "HIGH_WIND",
                "source": "Open-Meteo",
                "value": wind_speed,
                "unit": "m/s",
                "severity": "HIGH"
            })

        rain_probability = weather.get("rain_probability_percent")

        if (
            rain_probability is not None
            and rain_probability >= 70
        ):
            hazards.append({
                "type": "HEAVY_RAIN_RISK",
                "source": "Open-Meteo",
                "value": rain_probability,
                "unit": "%",
                "severity": "MODERATE"
            })

        visibility = weather.get("visibility_m")

        if (
            visibility is not None
            and visibility <= 2000
        ):
            hazards.append({
                "type": "LOW_VISIBILITY",
                "source": "Open-Meteo",
                "value": visibility,
                "unit": "m",
                "severity": "HIGH"
            })

    # -------------------------
    # OCEAN HAZARDS
    # -------------------------

    if ocean:

        waves = ocean.get("waves", {})

        wave_height = waves.get(
            "significant_wave_height_m"
        )

        if (
            wave_height is not None
            and wave_height >= 2.5
        ):
            hazards.append({
                "type": "HIGH_WAVES",
                "source": "INCOIS",
                "value": wave_height,
                "unit": "m",
                "severity": "HIGH"
            })

    # -------------------------
    # OFFICIAL SACHET ALERTS
    # -------------------------

    for alert in alerts or []:

        hazard = str(
            alert.get("hazard", "")
        ).lower()

        severity = str(
            alert.get("severity", "")
        ).upper()

        if "lightning" in hazard:

            hazards.append({
                "type": "LIGHTNING",
                "source": "SACHET-NDMA",
                "issuer": alert.get("issuer"),
                "severity": severity,
                "message": alert.get(
                    "warning_message"
                )
            })

        elif "thunderstorm" in hazard:

            hazards.append({
                "type": "THUNDERSTORM",
                "source": "SACHET-NDMA",
                "issuer": alert.get("issuer"),
                "severity": severity,
                "message": alert.get(
                    "warning_message"
                )
            })

        elif "cyclone" in hazard:

            hazards.append({
                "type": "CYCLONE",
                "source": "SACHET-NDMA",
                "issuer": alert.get("issuer"),
                "severity": severity,
                "message": alert.get(
                    "warning_message"
                )
            })

        elif "heavy rain" in hazard:

            hazards.append({
                "type": "HEAVY_RAIN",
                "source": "SACHET-NDMA",
                "issuer": alert.get("issuer"),
                "severity": severity,
                "message": alert.get(
                    "warning_message"
                )
            })

        elif (
            "wave" in hazard
            or "sea" in hazard
            or "marine" in hazard
        ):

            hazards.append({
                "type": "MARINE_WARNING",
                "source": "SACHET-NDMA",
                "issuer": alert.get("issuer"),
                "severity": severity,
                "message": alert.get(
                    "warning_message"
                )
            })

    return hazards