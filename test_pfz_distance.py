import json
from math import radians, sin, cos, sqrt, atan2

from shapely.geometry import Point, LineString


CHENNAI_LAT = 13.0827
CHENNAI_LON = 80.2707

EARTH_RADIUS_KM = 6371.0


def haversine(lat1, lon1, lat2, lon2):
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))


with open("pfz_real.json", encoding="utf-8") as f:
    data = json.load(f)


features = [
    f
    for f in data["features"]
    if f.get("properties", {}).get("State_Name") == "NORTH TAMILNADU"
]


results = []

for feature in features:
    props = feature["properties"]
    geometry = feature["geometry"]

    # MultiLineString
    for line_index, line_coords in enumerate(geometry["coordinates"]):

        line = LineString(line_coords)

        # Find nearest point in coordinate space
        chennai_point = Point(CHENNAI_LON, CHENNAI_LAT)
        nearest = line.interpolate(line.project(chennai_point))

        nearest_lon, nearest_lat = nearest.x, nearest.y

        distance_km = haversine(
            CHENNAI_LAT,
            CHENNAI_LON,
            nearest_lat,
            nearest_lon,
        )

        results.append({
            "uid": props["UID"],
            "sno": props["Sno"],
            "length_km": props["Length"],
            "line_index": line_index,
            "distance_km": distance_km,
            "nearest_lat": nearest_lat,
            "nearest_lon": nearest_lon,
        })


results.sort(key=lambda x: x["distance_km"])


print()
print("========================================")
print("   REAL INCOIS PFZ - CHENNAI SEARCH")
print("========================================")
print()

for r in results[:10]:
    print(
        f"UID={r['uid']} | "
        f"Distance={r['distance_km']:.2f} km | "
        f"PFZ={r['nearest_lat']:.4f}, {r['nearest_lon']:.4f} | "
        f"Length={r['length_km']:.2f} km"
    )

print()
print("========================================")
print("NEAREST PFZ")
print("========================================")

if results:
    r = results[0]

    print(f"UID          : {r['uid']}")
    print(f"Distance     : {r['distance_km']:.2f} km")
    print(f"Latitude     : {r['nearest_lat']:.6f}")
    print(f"Longitude    : {r['nearest_lon']:.6f}")
    print(f"PFZ Length   : {r['length_km']:.2f} km")
else:
    print("No PFZ found.")