def calculate_risk(hazards):

    score = 0

    for hazard in hazards:

        hazard_type = hazard.get("type")
        severity = str(hazard.get("severity", "")).upper()

        # Official SACHET alerts
        if hazard.get("source") == "SACHET-NDMA":

            if severity in ["EXTREME", "RED"]:
                score = 100
                break

            elif severity in ["HIGH", "ORANGE", "ALERT"]:
                score += 30

            elif severity in ["MODERATE", "YELLOW", "WATCH"]:
                score += 20

            else:
                score += 10

        # Weather hazards
        elif hazard_type == "HIGH_WIND":
            score += 25

        elif hazard_type == "HEAVY_RAIN_RISK":
            score += 15

        elif hazard_type == "LOW_VISIBILITY":
            score += 25

        # INCOIS marine hazard
        elif hazard_type == "HIGH_WAVES":
            score += 25

    # Combined hazard bonus
    if len(hazards) >= 3 and score < 100:
        score += 10

    score = min(score, 100)

    # Risk level
    if score >= 75:
        risk_level = "EXTREME"

    elif score >= 50:
        risk_level = "HIGH"

    elif score >= 25:
        risk_level = "MODERATE"

    else:
        risk_level = "LOW"

    # Safety recommendation
    if risk_level == "EXTREME":
        recommendation = (
            "Do not venture into the sea. "
            "Follow official warnings and seek appropriate safety measures."
        )

    elif risk_level == "HIGH":
        recommendation = (
            "Sea activity is not recommended. "
            "Follow official warnings and avoid hazardous conditions."
        )

    elif risk_level == "MODERATE":
        recommendation = (
            "Exercise caution. "
            "Check official marine and weather warnings before venturing into the sea."
        )

    else:
        if hazards:
            recommendation = (
                "A minor hazard has been detected. "
                "Exercise caution and continue monitoring "
                "weather, marine conditions and official alerts."
            )
        else:
            recommendation = (
                "No major hazards detected. "
                "Continue monitoring weather, marine conditions "
                "and official alerts."
            )

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "hazard_count": len(hazards)
    }