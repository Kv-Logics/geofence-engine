"""
Ray-Casting Point-in-Polygon Test
===================================
Tests the core algorithm against all 306 NITT buildings.
Strategy: A building's OWN centroid must always be inside itself.
This validates 100% of polygons at once.
"""
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON = os.path.join(BASE_DIR, "data", "master_buildings.geojson")
if not os.path.exists(GEOJSON):
    GEOJSON = os.path.join(BASE_DIR, "data", "buildings.geojson")

# ── Ray-Casting Algorithm ───────────────────────────────────────────────
def ray_cast(lat, lon, ring):
    """
    Fires a horizontal ray from (lat,lon) eastward.
    Counts how many polygon edges it crosses.
    Odd = inside, Even = outside.

    ring: list of [lon, lat] pairs (GeoJSON format)
    """
    inside = False
    n = len(ring)
    for i in range(n):
        j = (i - 1) % n
        xi, yi = ring[i][0], ring[i][1]   # lon, lat
        xj, yj = ring[j][0], ring[j][1]

        # Skip horizontal edges (degenerate case)
        if yi == yj:
            continue

        # Check if ray crosses this edge
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside

    return inside

def centroid_of_ring(ring):
    """Shoelace formula for accurate centroid."""
    n = len(ring)
    area = cx = cy = 0
    for i in range(n):
        j = (i + 1) % n
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        cross = xi * yj - xj * yi
        area += cross
        cx   += (xi + xj) * cross
        cy   += (yi + yj) * cross
    area /= 2
    if abs(area) < 1e-12:
        lats = [p[1] for p in ring]
        lons = [p[0] for p in ring]
        return sum(lats)/n, sum(lons)/n
    return cy / (6 * area), cx / (6 * area)  # lat, lon

# ── Load GeoJSON ─────────────────────────────────────────────────────────
print(f"Loading {GEOJSON}...")
with open(GEOJSON, encoding="utf-8") as f:
    gj = json.load(f)

features = gj["features"]
print(f"Loaded {len(features)} building polygons\n")

# ── Test 1: Centroid Self-Containment ────────────────────────────────────
print("=" * 62)
print("TEST 1: Every building centroid must be inside its own polygon")
print("=" * 62)

hits = 0
misses = []
t_start = time.perf_counter()

for feat in features:
    props = feat["properties"]
    geom  = feat["geometry"]
    if geom["type"] != "Polygon":
        continue

    ring = geom["coordinates"][0]  # outer ring
    lat, lon = centroid_of_ring(ring)

    inside = ray_cast(lat, lon, ring)

    if inside:
        hits += 1
    else:
        name = props.get("name") or props.get("building_id") or "?"
        misses.append(name)

elapsed = (time.perf_counter() - t_start) * 1000
print(f"  Passed : {hits} / {len(features)}")
print(f"  Failed : {len(misses)}")
print(f"  Time   : {elapsed:.2f} ms total  ({elapsed/len(features):.3f} ms/building)")

if misses:
    print(f"\n  Failed polygons (winding issue or degenerate):")
    for m in misses[:10]:
        print(f"    - {m}")

# ── Test 2: Known Outside Points ─────────────────────────────────────────
print(f"\n{'='*62}")
print("TEST 2: Points clearly outside campus must return False")
print("=" * 62)

outside_points = [
    (10.0000, 78.0000, "Chennai centre"),
    (28.6139, 77.2090, "New Delhi"),
    (10.7490, 78.8010, "SW corner of bbox"),
    (10.7780, 78.8300, "NE corner of bbox"),
    (0.0000,  0.0000,  "Null island"),
]

all_ring = [feat["geometry"]["coordinates"][0] for feat in features if feat["geometry"]["type"] == "Polygon"]

for lat, lon, label in outside_points:
    inside_any = any(ray_cast(lat, lon, ring) for ring in all_ring)
    status = "FAIL - inside a building (should be outside)!" if inside_any else "PASS"
    print(f"  {status:<6}  {label} ({lat}, {lon})")

# ── Test 3: Single point lookup (what the attendance system calls) ────────
print(f"\n{'='*62}")
print("TEST 3: Single GPS lookup — attendance system simulation")
print("=" * 62)

# Pick centroids of first 5 named buildings and look them up
named = [f for f in features if not f["properties"].get("name","").startswith("Building ")][:5]

for feat in named:
    props = feat["properties"]
    ring  = feat["geometry"]["coordinates"][0]
    lat, lon = centroid_of_ring(ring)
    name = props.get("name", "?")

    t0 = time.perf_counter()
    # Full scan against all buildings (O(n) with bounding box opt)
    result = None
    for f2 in features:
        if f2["geometry"]["type"] != "Polygon":
            continue
        r2 = f2["geometry"]["coordinates"][0]
        # Bounding box pre-filter
        lats = [p[1] for p in r2]; lons = [p[0] for p in r2]
        if not (min(lats) <= lat <= max(lats) and min(lons) <= lon <= max(lons)):
            continue
        if ray_cast(lat, lon, r2):
            result = f2["properties"].get("name") or f2["properties"].get("building_id")
            break
    elapsed_us = (time.perf_counter() - t0) * 1_000_000
    match = "HIT" if result else "MISS"
    correct = result == name or result == props.get("building_id")
    print(f"  [{match}] {name[:35]:<35} -> '{result}'  ({elapsed_us:.1f} us)")

print(f"\n{'='*62}")
print("Ray-casting validation complete.")
print("=" * 62)
