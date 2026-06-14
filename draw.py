import json
import matplotlib.pyplot as plt

# Load GeoJSON
with open("administrative block.json", "r") as f:
    data = json.load(f)

# Extract polygon coordinates
coords = data["features"][0]["geometry"]["coordinates"][0]

# Separate longitude and latitude
lon = [p[0] for p in coords]
lat = [p[1] for p in coords]

# Plot
plt.figure(figsize=(10, 6))
plt.plot(lon, lat, marker='o')
plt.fill(lon, lat, alpha=0.3)

plt.title("Administrative Block Polygon")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.axis('equal')
plt.grid(True)

plt.show()