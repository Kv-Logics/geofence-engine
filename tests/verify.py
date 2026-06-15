import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
master_geojson_path = os.path.join(BASE_DIR, "data", "master_buildings.geojson")
d = json.load(open(master_geojson_path, encoding='utf-8'))
named = sum(1 for f in d['features'] if not f['properties'].get('name','').startswith('Building '))
print(f"master_buildings.geojson: {len(d['features'])} buildings, {named} named")
for fname in ['master_buildings.geojson','attendance_zones.geojson','campus.kml','buildings.geojson']:
    p = os.path.join(BASE_DIR, "data", fname)
    if os.path.exists(p):
        print(f"  {fname}: {round(os.path.getsize(p)/1024)} KB")
    else:
        print(f"  {fname}: MISSING")
print("All good!")
