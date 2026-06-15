import json
import matplotlib.pyplot as plt
from math import radians, sin, cos, sqrt, atan2


def point_in_polygon(x, y, polygon):
    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if ((yi > y) != (yj > y)):
            intersect = (
                x < (xj - xi) * (y - yi) / (yj - yi) + xi
            )

            if intersect:
                inside = not inside

        j = i

    return inside


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


# ------------------------------------
# LOAD BUILDING POLYGON
# ------------------------------------
with open("administrative block.json", "r") as f:
    data = json.load(f)

coords = data["features"][0]["geometry"]["coordinates"][0]

polygon = [(p[0], p[1]) for p in coords]

lon = [p[0] for p in coords]
lat = [p[1] for p in coords]

# ------------------------------------
# USER GPS LOCATION
# ------------------------------------
 
user_lat =   10.758775444046192
user_lon =  78.8134542670109
# ------------------------------------
# RAY CASTING CHECK
# ------------------------------------
inside = point_in_polygon(
    user_lon,
    user_lat,
    polygon
)

print("=" * 50)
print("RAY CASTING BUILDING TEST")
print("=" * 50)
print(f"User Longitude : {user_lon}")
print(f"User Latitude  : {user_lat}")

nearest_point = None
min_distance = float("inf")

if inside:
    print("\nRESULT : INSIDE BUILDING")
    point_color = "green"

else:
    print("\nRESULT : OUTSIDE BUILDING")
    point_color = "red"

    # Find nearest polygon vertex
    for lon_p, lat_p in polygon:

        dist = haversine(
            user_lat,
            user_lon,
            lat_p,
            lon_p
        )

        if dist < min_distance:
            min_distance = dist
            nearest_point = (lon_p, lat_p)

    print(f"Nearest Polygon Point : {nearest_point}")
    print(f"Distance to Building  : {min_distance:.2f} meters")

# ------------------------------------
# VISUALIZATION
# ------------------------------------
plt.figure(figsize=(10, 8))

# Building boundary
plt.plot(
    lon,
    lat,
    marker="o",
    linewidth=2,
    label="Building Boundary"
)

plt.fill(
    lon,
    lat,
    alpha=0.3
)

# User location
plt.scatter(
    user_lon,
    user_lat,
    color=point_color,
    s=200,
    marker="x",
    label="User Location"
)

# Draw nearest point and line if outside
if not inside:

    plt.scatter(
        nearest_point[0],
        nearest_point[1],
        s=120,
        marker="o",
        label="Nearest Boundary Point"
    )

    plt.plot(
        [user_lon, nearest_point[0]],
        [user_lat, nearest_point[1]],
        linestyle="--",
        linewidth=2,
        label=f"{min_distance:.1f} m"
    )

plt.title("Administrative Block Geofence Test")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.grid(True)
plt.axis("equal")

plt.show()