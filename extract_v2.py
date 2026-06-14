"""
Phase 1 - Expanded OSM Extraction v2
Uses a larger bounding box and better query to capture all buildings
including relations (multi-polygon buildings like large department blocks).
"""
import json
import urllib.request
import urllib.parse
import os

# Slightly expanded bbox to catch all campus edge buildings
BBOX = "10.7490,78.8010,10.7780,78.8300"

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
  way["leisure"]({BBOX});
  way["sport"]({BBOX});
);
out body geom qt;
"""

OUT_DIR = "coords_extracted"
os.makedirs(OUT_DIR, exist_ok=True)
raw_path = os.path.join(OUT_DIR, "raw_osm_v2.json")

print("Downloading expanded OSM data...")
data = urllib.parse.urlencode({'data': QUERY}).encode('utf-8')
headers = {'User-Agent': 'NITT-GeofenceEngine/2.0', 'Accept': '*/*'}
req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=data, headers=headers)

with urllib.request.urlopen(req, timeout=310) as resp:
    osm = json.loads(resp.read().decode('utf-8'))
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(osm, f, indent=2)

total = len([e for e in osm.get('elements', []) if e.get('tags', {}).get('building')])
print(f"OSM v2 done. Raw building elements found: {total}")
print(f"Saved to: {raw_path}")
