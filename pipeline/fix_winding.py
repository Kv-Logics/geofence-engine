"""
Fix Polygon Winding Order in master_buildings.geojson
======================================================
GeoJSON spec requires counter-clockwise outer rings.
OSM sometimes exports clockwise rings which breaks ray-casting.

This script:
1. Loads master_buildings.geojson
2. Detects and fixes all winding-order issues
3. Validates every centroid is inside its own polygon
4. Saves the corrected file
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(BASE_DIR, "data", "master_buildings.geojson")
DEST = os.path.join(BASE_DIR, "data", "master_buildings.geojson")

# ── Helpers ────────────────────────────────────────────────────────────

def shoelace_area(ring):
    """Signed area via Shoelace. Positive = CCW, Negative = CW."""
    n = len(ring)
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += ring[i][0] * ring[j][1]
        area -= ring[j][0] * ring[i][1]
    return area / 2

def centroid(ring):
    n = len(ring)
    area = cx = cy = 0
    for i in range(n):
        j = (i + 1) % n
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        c = xi * yj - xj * yi
        area += c; cx += (xi + xj) * c; cy += (yi + yj) * c
    area /= 2
    if abs(area) < 1e-12:
        return sum(p[0] for p in ring)/n, sum(p[1] for p in ring)/n
    return cx/(6*area), cy/(6*area)

def ray_cast(lon, lat, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        j = (i - 1) % n
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if yi == yj: continue
        if ((yi > lat) != (yj > lat)) and (lon < (xj-xi)*(lat-yi)/(yj-yi)+xi):
            inside = not inside
    return inside

def ensure_ccw(ring):
    """Return ring guaranteed to be counter-clockwise."""
    area = shoelace_area(ring)
    if area < 0:          # clockwise → reverse
        return ring[::-1]
    return ring

def ensure_closed(ring):
    if ring and ring[0] != ring[-1]:
        ring = ring + [ring[0]]
    return ring

# ── Load ───────────────────────────────────────────────────────────────

print(f"Loading {SRC}...")
with open(SRC, encoding="utf-8") as f:
    gj = json.load(f)

features = gj["features"]
print(f"  {len(features)} features loaded\n")

fixed_winding  = 0
fixed_closed   = 0
still_failing  = 0

for feat in features:
    geom = feat["geometry"]
    if geom["type"] != "Polygon":
        continue

    fixed_rings = []
    for ring in geom["coordinates"]:
        # 1. Ensure ring is closed
        if ring[0] != ring[-1]:
            ring = ensure_closed(ring)
            fixed_closed += 1

        # 2. Fix winding order (outer ring must be CCW)
        area = shoelace_area(ring)
        if area < 0:
            ring = ring[::-1]
            fixed_winding += 1

        fixed_rings.append(ring)

    geom["coordinates"] = fixed_rings

    # 3. Validate centroid is now inside
    outer = geom["coordinates"][0]
    cx, cy = centroid(outer)   # lon, lat
    if not ray_cast(cx, cy, outer):
        still_failing += 1

# ── Save ───────────────────────────────────────────────────────────────

with open(DEST, "w", encoding="utf-8") as f:
    json.dump(gj, f, indent=2)

print(f"Fixed winding order : {fixed_winding} polygons")
print(f"Fixed unclosed rings: {fixed_closed} polygons")
print(f"Still failing       : {still_failing} (degenerate/self-intersecting)")
print(f"\nSaved corrected file: {DEST}")

# ── Re-validate ────────────────────────────────────────────────────────

print("\nRe-running validation...")
passed = 0
for feat in gj["features"]:
    geom = feat["geometry"]
    if geom["type"] != "Polygon": continue
    ring = geom["coordinates"][0]
    cx, cy = centroid(ring)
    if ray_cast(cx, cy, ring):
        passed += 1

total = sum(1 for f in gj["features"] if f["geometry"]["type"] == "Polygon")
print(f"Centroid-in-polygon: {passed} / {total}  ({100*passed//total}% pass rate)")
