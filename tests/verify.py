import json, os
d = json.load(open('coords_extracted/master_buildings.geojson', encoding='utf-8'))
named = sum(1 for f in d['features'] if not f['properties'].get('name','').startswith('Building '))
print(f"master_buildings.geojson: {len(d['features'])} buildings, {named} named")
for fname in ['master_buildings.geojson','attendance_zones.geojson','campus.kml','buildings.geojson']:
    p = f'coords_extracted/{fname}'
    if os.path.exists(p):
        print(f"  {fname}: {round(os.path.getsize(p)/1024)} KB")
    else:
        print(f"  {fname}: MISSING")
print("All good!")
