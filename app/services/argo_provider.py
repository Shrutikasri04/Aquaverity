from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import requests


class ArgovisProvider:
    """
    Read-only ARGO lookup using the public Argovis REST API.

    The provider searches a geographic box around the requested
    latitude/longitude and selects the nearest available profile.

    Note:
    ARGO observations are discrete measurements and may not be
    available exactly at the requested location or date.
    """

    def __init__(
        self,
        enabled: bool = True,
        base_url: str = "https://argovis-api.colorado.edu",
        search_days: int = 365,
        radius_km: float = 150.0,
    ):
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")
        self.search_days = search_days
        self.radius_km = radius_km

    def nearest_profile(self, lat: float, lon: float) -> dict:

        if not self.enabled:
            return {
                "status": "disabled",
                "nearest_profile_distance_km": None,
                "profile_count": 0,
                "latest_profile_time": None,
                "profile_id": None,
                "profile_lat": None,
                "profile_lon": None,
                "notes": "ARGO lookup disabled by configuration.",
            }

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.search_days)

        # Approximate geographic box around requested location.
        # 1 degree latitude ≈ 111 km.
        lat_delta = self.radius_km / 111.0

        # Avoid division problems close to the poles.
        import math

        lon_scale = max(math.cos(math.radians(lat)), 0.1)
        lon_delta = self.radius_km / (111.0 * lon_scale)

        polygon = (
            f"[[{lon - lon_delta},{lat - lat_delta}],"
            f"[{lon + lon_delta},{lat - lat_delta}],"
            f"[{lon + lon_delta},{lat + lat_delta}],"
            f"[{lon - lon_delta},{lat + lat_delta}],"
            f"[{lon - lon_delta},{lat - lat_delta}]]"
        )

        params = {
    "polygon": polygon,
    "startDate": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "endDate": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
}

        try:
            response = requests.get(
                f"{self.base_url}/argo",
                params=params,
                timeout=20,
            )

            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, list) or not payload:
                return {
                    "status": "no_data",
                    "nearest_profile_distance_km": None,
                    "profile_count": 0,
                    "latest_profile_time": None,
                    "profile_id": None,
                    "profile_lat": None,
                    "profile_lon": None,
                    "notes": "No ARGO profiles found in the requested region/time window.",
                }

            nearest = None
            nearest_distance = None
            latest = None

            for profile in payload:

                geo = profile.get("geolocation")

                # Argovis normally returns:
                # {"type": "Point", "coordinates": [lon, lat]}
                if isinstance(geo, dict):
                    coordinates = geo.get("coordinates")
                elif isinstance(geo, list):
                    coordinates = geo
                else:
                    coordinates = None

                if isinstance(coordinates, list) and len(coordinates) >= 2:

                    try:
                        p_lon = float(coordinates[0])
                        p_lat = float(coordinates[1])

                        distance = _haversine_km(
                            lat,
                            lon,
                            p_lat,
                            p_lon,
                        )

                        if (
                            nearest_distance is None
                            or distance < nearest_distance
                        ):
                            nearest_distance = distance
                            nearest = profile

                    except (TypeError, ValueError):
                        continue

                timestamp = profile.get("timestamp")

                if timestamp:
                    if latest is None or str(timestamp) > str(latest):
                        latest = timestamp

            if nearest is None:
                return {
                    "status": "no_location",
                    "nearest_profile_distance_km": None,
                    "profile_count": len(payload),
                    "latest_profile_time": latest,
                    "profile_id": None,
                    "profile_lat": None,
                    "profile_lon": None,
                    "notes": "ARGO profiles were returned, but valid coordinates were unavailable.",
                }

            nearest_geo = nearest.get("geolocation", {})
            nearest_coordinates = (
                nearest_geo.get("coordinates", [])
                if isinstance(nearest_geo, dict)
                else nearest_geo
            )

            profile_lon = None
            profile_lat = None

            if isinstance(nearest_coordinates, list) and len(nearest_coordinates) >= 2:
                profile_lon = float(nearest_coordinates[0])
                profile_lat = float(nearest_coordinates[1])

            return {
                "status": "available",
                "nearest_profile_distance_km": (
                    round(nearest_distance, 2)
                    if nearest_distance is not None
                    else None
                ),
                "profile_count": len(payload),
                "latest_profile_time": latest,
                "profile_id": nearest.get("_id"),
                "profile_lat": profile_lat,
                "profile_lon": profile_lon,
                "notes": "ARGO metadata retrieved from Argovis.",
            }

        except requests.RequestException as exc:
            return {
                "status": "unavailable",
                "nearest_profile_distance_km": None,
                "profile_count": 0,
                "latest_profile_time": None,
                "profile_id": None,
                "profile_lat": None,
                "profile_lon": None,
                "notes": f"ARGO network request failed: {type(exc).__name__}",
            }

        except ValueError as exc:
            return {
                "status": "unavailable",
                "nearest_profile_distance_km": None,
                "profile_count": 0,
                "latest_profile_time": None,
                "profile_id": None,
                "profile_lat": None,
                "profile_lon": None,
                "notes": f"ARGO response could not be parsed: {type(exc).__name__}",
            }

        except Exception as exc:
            return {
                "status": "unavailable",
                "nearest_profile_distance_km": None,
                "profile_count": 0,
                "latest_profile_time": None,
                "profile_id": None,
                "profile_lat": None,
                "profile_lon": None,
                "notes": f"ARGO lookup failed gracefully: {type(exc).__name__}",
            }


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    from math import asin, cos, radians, sin, sqrt

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    return 6371.0088 * 2 * asin(sqrt(a))