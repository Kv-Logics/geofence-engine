import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
buildings_geojson_path = os.path.join(BASE_DIR, "data", "buildings.geojson")
output_path = os.path.join(BASE_DIR, "data", "attendance_polygons.json")

print(f"Reading from {buildings_geojson_path}...")

with open(buildings_geojson_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)

attendance_data = []

for feature in geojson_data.get("features", []):
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    
    building_id = props.get("osm_id")
    coords = []
    
    if geom.get("type") == "Polygon":
        # GeoJSON Polygon coordinates are usually [[[lon, lat], [lon, lat], ...]]]
        # We need to extract the first ring (outer ring) and convert to [{'lat': lat, 'lon': lon}]
        if geom.get("coordinates") and len(geom["coordinates"]) > 0:
            ring = geom["coordinates"][0]
            coords = [{"lat": pt[1], "lon": pt[0]} for pt in ring]
    elif geom.get("type") == "LineString":
        # LineString: [[lon, lat], ...]
        ring = geom.get("coordinates", [])
        coords = [{"lat": pt[1], "lon": pt[0]} for pt in ring]
        
    if building_id and coords:
        attendance_data.append({
            "building_id": building_id,
            "polygon": coords
        })

print(f"Extracted {len(attendance_data)} polygons for attendance lookup.")

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(attendance_data, f, indent=4)

print(f"Successfully saved to {output_path}")
