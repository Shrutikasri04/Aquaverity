from __future__ import annotations

import json
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path

from shapely.geometry import Point, LineString


EARTH_RADIUS_KM = 6371.0


class INCOISPFZProvider:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.pfz_file = self.project_root / "pfz_real.json"

    def _haversine(self, lat1, lon1, lat2, lon2):
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

        return 2 * EARTH_RADIUS_KM * atan2(
            sqrt(a),
            sqrt(1 - a),
        )

    def _julian_to_date(self, year, julian_day):
        return datetime.strptime(
            f"{year}-{julian_day}",
            "%Y-%j",
        ).date().isoformat()

    def get_nearest_pfz(self, lat: float, lon: float):
        if not self.pfz_file.exists():
            return {
                "status": "unavailable",
                "reason": "INCOIS PFZ data file not found",
            }

        try:
            with open(self.pfz_file, encoding="utf-8") as f:
                data = json.load(f)

            features = [
                feature
                for feature in data.get("features", [])
                if feature.get("properties", {}).get("State_Name")
                == "NORTH TAMILNADU"
            ]

            if not features:
                return {
                    "status": "unavailable",
                    "reason": "No North Tamil Nadu PFZ features found",
                }

            requested_point = Point(lon, lat)

            nearest_result = None

            for feature in features:
                props = feature.get("properties", {})
                geometry = feature.get("geometry", {})

                for line_index, coordinates in enumerate(
                    geometry.get("coordinates", [])
                ):
                    if not coordinates:
                        continue

                    line = LineString(coordinates)

                    nearest_point = line.interpolate(
                        line.project(requested_point)
                    )

                    nearest_lon = nearest_point.x
                    nearest_lat = nearest_point.y

                    distance_km = self._haversine(
                        lat,
                        lon,
                        nearest_lat,
                        nearest_lon,
                    )

                    result = {
                        "status": "available",
                        "source": "INCOIS",
                        "uid": props.get("UID"),
                        "state": props.get("State_Name"),
                        "distance_km": round(distance_km, 2),
                        "latitude": round(nearest_lat, 6),
                        "longitude": round(nearest_lon, 6),
                        "pfz_length_km": props.get("Length"),
                        "line_index": line_index,
                        "advisory_date": self._julian_to_date(
                            int(props["Year"]),
                            int(props["Julian_day"]),
                        ),
                    }

                    if (
                        nearest_result is None
                        or result["distance_km"]
                        < nearest_result["distance_km"]
                    ):
                        nearest_result = result

            return nearest_result

        except Exception as exc:
            return {
                "status": "error",
                "reason": str(exc),
            }