"""
NITT Geofence Engine — Actual Usage Examples
=============================================
This script demonstrates how to use the spatial engine
in a real attendance / faculty location system.

Usage:
    python usage.py

Integrate into your backend:
    from spatial_engine_v2 import GeofenceEngine
"""

import json
import os
import time

# Resolve paths dynamically relative to the script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(BASE_DIR, "data", "master_buildings.json")
GEOJSON = os.path.join(BASE_DIR, "data", "master_buildings.geojson")

# If master_buildings.json doesn't exist yet, build it from GeoJSON
if not os.path.exists(MASTER) and os.path.exists(GEOJSON):
    print("Building master_buildings.json from GeoJSON...")
    with open(GEOJSON, encoding='utf-8') as f:
        gj = json.load(f)
    buildings = []
    for feat in gj['features']:
        props = feat['properties']
        ring = feat['geometry']['coordinates'][0]
        polygon = [{'lat': c[1], 'lon': c[0]} for c in ring]
        lats = [p['lat'] for p in polygon]
        lons = [p['lon'] for p in polygon]
        buildings.append({
            "building_id": str(props.get('osm_id', props.get('building_id', ''))),
            "building_idx": props.get('building_idx', 0),
            "name": props.get('name'),
            "resolved_name": props.get('name'),
            "source": props.get('source', 'osm'),
            "centroid": {"lat": sum(lats)/len(lats), "lon": sum(lons)/len(lons)},
            "polygon": polygon,
            "bbox": {"min_lat": min(lats), "max_lat": max(lats), "min_lon": min(lons), "max_lon": max(lons)},
            "tags": {k: v for k, v in props.items() if k not in ('building_id','building_idx','name','source')}
        })
    with open(MASTER, 'w', encoding='utf-8') as f:
        json.dump({"buildings": buildings}, f, indent=2)
    print(f"  Created {MASTER} with {len(buildings)} buildings.\n")

# ── Import Engine ─────────────────────────────────────────────────────────
# Add parent directory of tests/ (repository root) to system path to import engine.spatial_engine
import sys
sys.path.append(BASE_DIR)
from engine.spatial_engine import GeofenceEngine

print("=" * 60)
print("  NITT Geofence Engine — Usage Demo")
print("=" * 60)

engine = GeofenceEngine(MASTER)
stats = engine.stats()
print(f"\nEngine ready. Stats: {stats}\n")

# ─────────────────────────────────────────────────────────────────────────
# USE CASE 1: Single GPS lookup (what your attendance system calls)
# ─────────────────────────────────────────────────────────────────────────
print("-" * 60)
print("USE CASE 1: Faculty GPS Ping -> Which building?")
print("-" * 60)

# Simulate a faculty member's GPS coordinate
sample_points = [
    (10.7621, 78.8137, "Faculty A"),
    (10.7638, 78.8152, "Faculty B"),
    (10.7605, 78.8120, "Faculty C"),
    (10.0000, 78.0000, "Outside campus"),
]

for lat, lon, label in sample_points:
    t0 = time.perf_counter()
    result = engine.lookup(lat, lon)
    elapsed_us = (time.perf_counter() - t0) * 1_000_000

    if result:
        name = result.get('resolved_name') or result.get('name') or result['building_id']
        print(f"  {label:<18} -> [{name}]  ({elapsed_us:.1f} us)")
    else:
        print(f"  {label:<18} -> [Not inside any building]  ({elapsed_us:.1f} us)")

# ─────────────────────────────────────────────────────────────────────────
# USE CASE 2: Batch attendance verification
# ─────────────────────────────────────────────────────────────────────────
print(f"\n{'-'*60}")
print("USE CASE 2: Batch Attendance — Check all faculty")
print("-" * 60)

# Simulate faculty records with GPS pings
faculty_gps = [
    {"id": "FAC001", "name": "Dr. Kumar",   "lat": 10.7621, "lon": 78.8137},
    {"id": "FAC002", "name": "Dr. Priya",   "lat": 10.7638, "lon": 78.8152},
    {"id": "FAC003", "name": "Dr. Rajan",   "lat": 10.7605, "lon": 78.8120},
    {"id": "FAC004", "name": "Dr. Meena",   "lat": 10.0000, "lon": 78.0000},  # off campus
]

attendance = []
for faculty in faculty_gps:
    building = engine.lookup(faculty['lat'], faculty['lon'])
    record = {
        "faculty_id": faculty['id'],
        "faculty_name": faculty['name'],
        "status": "PRESENT" if building else "ABSENT",
        "location": (building.get('resolved_name') or building.get('name') or building['building_id']) if building else None,
        "building_id": building['building_id'] if building else None,
    }
    attendance.append(record)
    status_icon = "+" if building else "-"
    loc = record['location'] or "off campus"
    print(f"  [{status_icon}] {faculty['name']:<20} {record['status']:<8} @ {loc}")

print(f"\n  Present: {sum(1 for r in attendance if r['status']=='PRESENT')}/{len(attendance)}")

# ─────────────────────────────────────────────────────────────────────────
# USE CASE 3: Building directory lookup
# ─────────────────────────────────────────────────────────────────────────
print(f"\n{'-'*60}")
print("USE CASE 3: Building Directory (first 15 named)")
print("-" * 60)

named = [b for b in engine.all_buildings() if b.get('resolved_name') or b.get('name')][:15]
for b in named:
    name = b.get('resolved_name') or b.get('name')
    idx  = b.get('building_idx', '?')
    c    = b['centroid']
    print(f"  #{idx:<4} {name:<40}  centroid: ({c['lat']:.5f}, {c['lon']:.5f})")

# ─────────────────────────────────────────────────────────────────────────
# USE CASE 4: Export attendance_zones.geojson for mobile/Unity
# ─────────────────────────────────────────────────────────────────────────
print(f"\n{'-'*60}")
print("USE CASE 4: Generate attendance_zones.geojson")
print("-" * 60)

zones_features = []
for b in engine.all_buildings():
    coords = [[p['lon'], p['lat']] for p in b['polygon']]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    zones_features.append({
        "type": "Feature",
        "properties": {
            "building_id": b['building_id'],
            "building_idx": b.get('building_idx'),
            "name": b.get('resolved_name') or b.get('name') or f"Building {b.get('building_idx')}"
        },
        "geometry": {"type": "Polygon", "coordinates": [coords]}
    })

out_path = os.path.join(BASE_DIR, "data", "attendance_zones.geojson")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({"type": "FeatureCollection", "features": zones_features}, f, indent=2)
print(f"  [SUCCESS] Written {len(zones_features)} zones to {out_path}")
print(f"  Open in: QGIS | ArcGIS | Google Earth Pro | Mapbox Studio")
print()
print("=" * 60)
print("  All use cases complete.")
print("=" * 60)
