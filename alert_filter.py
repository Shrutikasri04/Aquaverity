from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timezone, timedelta


IST = timezone(timedelta(hours=5, minutes=30))


def calculate_distance(lat1, lon1, lat2, lon2):

    R = 6371

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def parse_target_time(target_time):

    target = target_time.replace("Z", "+00:00")

    dt = datetime.fromisoformat(target)

    # P3 target time is treated as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def parse_sachet_time(time_string):

    if not time_string:
        return None

    # SACHET format:
    # Fri Sep 11 20:00:00 IST 2026

    try:
        return datetime.strptime(
            time_string,
            "%a %b %d %H:%M:%S IST %Y"
        ).replace(tzinfo=IST)

    except (ValueError, TypeError):
        return None


def is_alert_active(alert, target_time):

    start_time = alert.get("start_time")
    end_time = alert.get("end_time")

    if not start_time:
        return True

    target = parse_target_time(target_time)

    start = parse_sachet_time(start_time)

    if start is None:
        return True

    # Convert target to the same timezone-aware representation
    target = target.astimezone(IST)

    if target < start:
        return False

    if end_time:

        end = parse_sachet_time(end_time)

        if end is not None and target > end:
            return False

    return True


def filter_alerts_by_location(
    alerts,
    latitude,
    longitude,
    target_time,
    radius_km=150
):

    relevant_alerts = []

    for alert in alerts:

        alert_latitude = alert.get("latitude")
        alert_longitude = alert.get("longitude")

        if alert_latitude is None or alert_longitude is None:
            continue

        if not is_alert_active(alert, target_time):
            continue

        distance = calculate_distance(
            latitude,
            longitude,
            alert_latitude,
            alert_longitude
        )

        if distance <= radius_km:

            alert_copy = alert.copy()

            alert_copy["distance_km"] = round(
                distance,
                2
            )

            relevant_alerts.append(alert_copy)

    return relevant_alerts