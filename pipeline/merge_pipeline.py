"""
Phase 2 - Merge & Validation Pipeline
Merges OSM + Microsoft + Manual drawings into one authoritative master_buildings.json
Handles:
  - Deduplication via Intersection over Union (IoU)
  - Polygon winding order normalization
  - Accurate centroid via Shoelace formula
  - Stable building IDs
  - Name resolution (OSM tags first, then reverse geocode placeholder)
"""
import json
import os
import math
import urllib.request
import time

# ─── Config ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COORDS_DIR = os.path.join(BASE_DIR, "data")
OSM_RAW_V2  = os.path.join(COORDS_DIR, "raw_osm_v2.json")
OSM_RAW_V1  = os.path.join(COORDS_DIR, "raw_osm.json")   # fallback
MSFT_PATH   = os.path.join(COORDS_DIR, "microsoft_footprints.json")
MANUAL_PATH = os.path.join(COORDS_DIR, "manual.json")
MASTER_PATH = os.path.join(COORDS_DIR, "master_buildings.json")

BBOX = {"min_lat": 10.7490, "max_lat": 10.7780, "min_lon": 78.8010, "max_lon": 78.8300}
IOU_OVERLAP_THRESHOLD = 0.3   # polygons overlapping >30% are considered duplicates
GEOCODE_DELAY = 1.1           # seconds between Nominatim calls (rate limit)

# ─── Geometry Helpers ──────────────────────────────────────────────────────

def shoelace_centroid(polygon):
    """Accurate centroid via Shoelace formula."""
    n = len(polygon)
    if n == 0:
        return None, None
    area = 0
    cx = cy = 0
    for i in range(n):
        j = (i + 1) % n
        xi, yi = polygon[i]['lon'], polygon[i]['lat']
        xj, yj = polygon[j]['lon'], polygon[j]['lat']
        cross = xi * yj - xj * yi
        area += cross
        cx += (xi + xj) * cross
        cy += (yi + yj) * cross
    area /= 2
    if abs(area) < 1e-12:
        # Fallback to simple mean
        return (sum(p['lat'] for p in polygon) / n,
                sum(p['lon'] for p in polygon) / n)
    cx /= (6 * area)
    cy /= (6 * area)
    return cy, cx  # lat, lon

def compute_bbox(polygon):
    lats = [p['lat'] for p in polygon]
    lons = [p['lon'] for p in polygon]
    return {
        "min_lat": min(lats), "max_lat": max(lats),
        "min_lon": min(lons), "max_lon": max(lons)
    }

def bbox_intersection_area(b1, b2):
    inter_min_lat = max(b1['min_lat'], b2['min_lat'])
    inter_max_lat = min(b1['max_lat'], b2['max_lat'])
    inter_min_lon = max(b1['min_lon'], b2['min_lon'])
    inter_max_lon = min(b1['max_lon'], b2['max_lon'])
    if inter_max_lat < inter_min_lat or inter_max_lon < inter_min_lon:
        return 0.0
    return (inter_max_lat - inter_min_lat) * (inter_max_lon - inter_min_lon)

def bbox_area(b):
    return (b['max_lat'] - b['min_lat']) * (b['max_lon'] - b['min_lon'])

def bbox_iou(b1, b2):
    inter = bbox_intersection_area(b1, b2)
    if inter == 0:
        return 0.0
    union = bbox_area(b1) + bbox_area(b2) - inter
    return inter / union if union > 0 else 0.0

def normalize_winding(polygon):
    """Ensure counter-clockwise winding (GeoJSON spec)."""
    if len(polygon) < 3:
        return polygon
    area = sum(
        (polygon[i]['lon'] * polygon[(i+1) % len(polygon)]['lat'] -
         polygon[(i+1) % len(polygon)]['lon'] * polygon[i]['lat'])
        for i in range(len(polygon))
    )
    if area < 0:  # clockwise → reverse
        return polygon[::-1]
    return polygon

def ensure_closed(polygon):
    if polygon and polygon[0] != polygon[-1]:
        polygon = polygon + [polygon[0]]
    return polygon

# ─── OSM Parsing ───────────────────────────────────────────────────────────

def parse_osm(osm_json):
    buildings = []
    elements = osm_json.get('elements', [])

    for el in elements:
        tags = el.get('tags', {})
        if 'building' not in tags:
            continue

        osm_id = el['id']
        el_type = el['type']
        polygon = []

        if el_type == 'way':
            geom = el.get('geometry', [])
            polygon = [{'lat': p['lat'], 'lon': p['lon']} for p in geom]

        elif el_type == 'relation':
            for member in el.get('members', []):
                if member.get('role') == 'outer' and member.get('type') == 'way':
                    geom = member.get('geometry', [])
                    polygon = [{'lat': p['lat'], 'lon': p['lon']} for p in geom]
                    break

        if len(polygon) < 3:
            continue

        polygon = normalize_winding(ensure_closed(polygon))
        bbox = compute_bbox(polygon)
        centroid_lat, centroid_lon = shoelace_centroid(polygon)

        # Build resolved name from all available tags
        name = (tags.get('name') or tags.get('ref') or
                tags.get('operator') or tags.get('department') or
                tags.get('faculty') or None)

        buildings.append({
            "building_id": f"osm_{osm_id}",
            "name": name,
            "resolved_name": name,
            "source": "osm",
            "centroid": {"lat": centroid_lat, "lon": centroid_lon},
            "polygon": polygon,
            "bbox": bbox,
            "tags": tags
        })

    return buildings

def parse_microsoft(msft_json):
    buildings = []
    for i, feature in enumerate(msft_json.get('features', [])):
        geom = feature.get('geometry', {})
        if geom.get('type') != 'Polygon':
            continue
        coords = geom.get('coordinates', [[]])[0]
        polygon = [{'lat': c[1], 'lon': c[0]} for c in coords]
        if len(polygon) < 3:
            continue
        polygon = normalize_winding(ensure_closed(polygon))
        bbox = compute_bbox(polygon)
        centroid_lat, centroid_lon = shoelace_centroid(polygon)
        props = feature.get('properties', {})
        buildings.append({
            "building_id": f"msft_{i}",
            "name": None,
            "resolved_name": None,
            "source": "microsoft_ml",
            "centroid": {"lat": centroid_lat, "lon": centroid_lon},
            "polygon": polygon,
            "bbox": bbox,
            "tags": {"building": "yes", "confidence": props.get("confidence", "")}
        })
    return buildings

def parse_manual(manual_json):
    buildings = []
    for i, b in enumerate(manual_json.get('buildings', [])):
        polygon = b.get('polygon', [])
        if len(polygon) < 3:
            continue
        polygon = normalize_winding(ensure_closed(polygon))
        bbox = compute_bbox(polygon)
        centroid_lat, centroid_lon = shoelace_centroid(polygon)
        buildings.append({
            "building_id": f"manual_{i}",
            "name": b.get('name'),
            "resolved_name": b.get('name'),
            "source": "manual",
            "centroid": {"lat": centroid_lat, "lon": centroid_lon},
            "polygon": polygon,
            "bbox": bbox,
            "tags": b.get('tags', {"building": "yes"})
        })
    return buildings

# ─── Deduplication ─────────────────────────────────────────────────────────

def deduplicate(buildings):
    """Remove buildings with >30% bbox overlap (keep OSM > MSFT > manual by priority)."""
    priority = {"osm": 0, "microsoft_ml": 1, "manual": 2}
    buildings.sort(key=lambda b: priority.get(b['source'], 99))

    kept = []
    for candidate in buildings:
        cb = candidate['bbox']
        is_dup = False
        for existing in kept:
            if bbox_iou(cb, existing['bbox']) > IOU_OVERLAP_THRESHOLD:
                # Merge name if existing has none
                if existing['name'] is None and candidate['name']:
                    existing['name'] = candidate['name']
                    existing['resolved_name'] = candidate['name']
                is_dup = True
                break
        if not is_dup:
            kept.append(candidate)

    return kept

# ─── Reverse Geocoding ─────────────────────────────────────────────────────

def reverse_geocode(lat, lon):
    try:
        url = (f"https://nominatim.openstreetmap.org/reverse"
               f"?lat={lat:.6f}&lon={lon:.6f}&format=json&zoom=18&addressdetails=0")
        req = urllib.request.Request(url, headers={'User-Agent': 'NITT-GeofenceEngine/2.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get('display_name', '').split(',')[0].strip()
    except Exception:
        return None

# ─── Main Pipeline ─────────────────────────────────────────────────────────

def main():
    all_buildings = []

    # Load OSM
    osm_path = OSM_RAW_V2 if os.path.exists(OSM_RAW_V2) else OSM_RAW_V1
    print(f"Loading OSM from {osm_path}...")
    with open(osm_path, 'r', encoding='utf-8') as f:
        osm_json = json.load(f)
    osm_buildings = parse_osm(osm_json)
    print(f"  Parsed {len(osm_buildings)} OSM buildings")
    all_buildings.extend(osm_buildings)

    # Load Microsoft
    if os.path.exists(MSFT_PATH):
        print(f"Loading Microsoft footprints from {MSFT_PATH}...")
        with open(MSFT_PATH, 'r', encoding='utf-8') as f:
            msft_json = json.load(f)
        msft_buildings = parse_microsoft(msft_json)
        print(f"  Parsed {len(msft_buildings)} Microsoft buildings")
        all_buildings.extend(msft_buildings)
    else:
        print("No Microsoft footprints file found, skipping.")

    # Load Manual
    if os.path.exists(MANUAL_PATH):
        print(f"Loading manual buildings from {MANUAL_PATH}...")
        with open(MANUAL_PATH, 'r', encoding='utf-8') as f:
            manual_json = json.load(f)
        manual_buildings = parse_manual(manual_json)
        print(f"  Parsed {len(manual_buildings)} manual buildings")
        all_buildings.extend(manual_buildings)
    else:
        print("No manual.json found, skipping.")

    print(f"\nTotal before deduplication: {len(all_buildings)}")
    merged = deduplicate(all_buildings)
    print(f"Total after deduplication:  {len(merged)}")

    # Assign stable sequential IDs
    for i, b in enumerate(merged):
        b['building_idx'] = i + 1

    # Batch reverse geocode unnamed buildings
    unnamed = [b for b in merged if not b.get('resolved_name')]
    print(f"\nReverse geocoding {len(unnamed)} unnamed buildings (rate-limited)...")
    resolved_count = 0
    for b in unnamed:
        lat = b['centroid']['lat']
        lon = b['centroid']['lon']
        name = reverse_geocode(lat, lon)
        if name and 'National Institute of Technology' in name or (name and len(name) > 3):
            b['resolved_name'] = name
            resolved_count += 1
        time.sleep(GEOCODE_DELAY)

    print(f"Resolved {resolved_count} additional names via geocoding.")

    # Save master
    named = sum(1 for b in merged if b.get('resolved_name'))
    output = {
        "meta": {
            "total_buildings": len(merged),
            "named_buildings": named,
            "unnamed_buildings": len(merged) - named,
            "sources": {
                "osm": sum(1 for b in merged if b['source'] == 'osm'),
                "microsoft_ml": sum(1 for b in merged if b['source'] == 'microsoft_ml'),
                "manual": sum(1 for b in merged if b['source'] == 'manual')
            }
        },
        "buildings": merged
    }

    with open(MASTER_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    # Also write a GeoJSON for the map
    geojson_path = os.path.join(COORDS_DIR, "master_buildings.geojson")
    features = []
    for b in merged:
        coords = [[p['lon'], p['lat']] for p in b['polygon']]
        features.append({
            "type": "Feature",
            "properties": {
                "building_id": b['building_id'],
                "building_idx": b['building_idx'],
                "name": b.get('resolved_name') or b.get('name') or f"Building {b['building_idx']}",
                "source": b['source'],
                **b.get('tags', {})
            },
            "geometry": {"type": "Polygon", "coordinates": [coords]}
        })
    with open(geojson_path, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

    print(f"\n[OK] master_buildings.json saved: {len(merged)} buildings")
    print(f"[OK] master_buildings.geojson saved")
    print(f"  Named: {named} / {len(merged)}")
    print(f"  Sources: {output['meta']['sources']}")

if __name__ == "__main__":
    main()
