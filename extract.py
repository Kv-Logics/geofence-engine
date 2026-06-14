import json
import urllib.request
import urllib.parse
import os

BBOX = "10.7517140,78.8041608,10.7751656,78.8266969"

QUERY = f"""
[out:json][timeout:300];
(
  way["amenity"="university"]({BBOX});
  relation["amenity"="university"]({BBOX});
  way["landuse"="education"]({BBOX});
  relation["landuse"="education"]({BBOX});
  way["building"]({BBOX});
  relation["building"]({BBOX});
  way["highway"]({BBOX});
  way["amenity"]({BBOX});
  relation["amenity"]({BBOX});
  node["amenity"]({BBOX});
);
out tags geom;
"""

OUT_DIR = "coords_extracted"
BUILDINGS_DIR = os.path.join(OUT_DIR, "buildings")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(BUILDINGS_DIR, exist_ok=True)

raw_osm_path = os.path.join(OUT_DIR, "raw_osm.json")

print("Downloading Overpass data...")
data = urllib.parse.urlencode({'data': QUERY}).encode('utf-8')
headers = {
    'User-Agent': 'Antigravity/1.0 (Python)',
    'Accept': '*/*'
}
req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=data, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        osm_json = json.loads(response.read().decode('utf-8'))
        with open(raw_osm_path, 'w', encoding='utf-8') as f:
            json.dump(osm_json, f, indent=2)
except Exception as e:
    print(f"Failed to download: {e}")
    # try loading if exists
    if os.path.exists(raw_osm_path):
        with open(raw_osm_path, 'r', encoding='utf-8') as f:
            osm_json = json.load(f)
    else:
        exit(1)

print("Processing data...")

def get_coords(way_geom):
    return [{"lat": pt["lat"], "lon": pt["lon"]} for pt in way_geom]

def get_geojson_coords(geom, geom_type="LineString"):
    coords = [[pt["lon"], pt["lat"]] for pt in geom]
    if geom_type == "Polygon":
        return [coords]
    return coords

campus_features = []
building_features = []
road_features = []
amenity_features = []

total_buildings = 0
named_buildings = 0
roads_count = 0
amenities_count = 0

missing_names = []

for element in osm_json.get("elements", []):
    elem_type = element["type"]
    tags = element.get("tags", {})
    osm_id = element["id"]
    
    # Process geometry
    if elem_type == "node":
        geom = [{"lat": element["lat"], "lon": element["lon"]}]
        geojson_geom = {"type": "Point", "coordinates": [element["lon"], element["lat"]]}
    elif elem_type == "way":
        if "geometry" not in element: continue
        geom = get_coords(element["geometry"])
        is_closed = len(geom) > 1 and geom[0] == geom[-1]
        
        if is_closed and ("building" in tags or "landuse" in tags or "amenity" in tags):
            geojson_geom = {"type": "Polygon", "coordinates": get_geojson_coords(element["geometry"], "Polygon")}
        else:
            geojson_geom = {"type": "LineString", "coordinates": get_geojson_coords(element["geometry"], "LineString")}
            
    elif elem_type == "relation":
        # Extract outer rings
        outer_geoms = []
        for member in element.get("members", []):
            if member["type"] == "way" and member.get("role") == "outer" and "geometry" in member:
                outer_geoms.append(get_geojson_coords(member["geometry"], "Polygon")[0])
        if not outer_geoms:
            continue
        geom = get_coords([pt for member in element.get("members", []) if member.get("role") == "outer" for pt in member.get("geometry", [])])
        geojson_geom = {"type": "Polygon", "coordinates": [outer_geoms[0]]} # Simplified multi-polygon logic

    feature = {
        "type": "Feature",
        "properties": {"osm_id": osm_id, **tags},
        "geometry": geojson_geom
    }

    # Classification
    if "amenity" in tags and tags["amenity"] == "university" or "landuse" in tags and tags["landuse"] == "education":
        campus_features.append(feature)
        
    if "building" in tags:
        total_buildings += 1
        building_features.append(feature)
        
        name = tags.get("name")
        if name:
            named_buildings += 1
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"{safe_name}.json"
        else:
            missing_names.append(osm_id)
            filename = f"building_{osm_id}.json"
            name = str(osm_id)
            
        # Calculate centroid
        if geom:
            avg_lat = sum(p["lat"] for p in geom) / len(geom)
            avg_lon = sum(p["lon"] for p in geom) / len(geom)
            centroid = {"lat": avg_lat, "lon": avg_lon}
        else:
            centroid = {"lat": 0, "lon": 0}
            
        building_data = {
            "osm_id": osm_id,
            "name": name,
            "centroid": centroid,
            "polygon": geom,
            "tags": tags
        }
        
        with open(os.path.join(BUILDINGS_DIR, filename), 'w', encoding='utf-8') as bf:
            json.dump(building_data, bf, indent=4)

    if "highway" in tags:
        roads_count += 1
        road_features.append(feature)
        
    if "amenity" in tags:
        amenities_count += 1
        amenity_features.append(feature)

def save_geojson(features, filename):
    with open(os.path.join(OUT_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

save_geojson(campus_features, "campus_boundary.geojson")
save_geojson(building_features, "buildings.geojson")
save_geojson(road_features, "roads.geojson")
save_geojson(amenity_features, "amenities.geojson")

summary = {
    "total_buildings": total_buildings,
    "named_buildings": named_buildings,
    "roads": roads_count,
    "amenities": amenities_count
}

with open(os.path.join(OUT_DIR, "summary.json"), 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=4)

print(f"Summary: {summary}")
print(f"Logged {len(missing_names)} buildings with missing names.")
