"""
Export campus map data into industry-standard GIS formats:
  - master_buildings.geojson  (Leaflet, QGIS, ArcGIS, Mapbox)
  - campus.kml                (Google Earth, Google Maps import)
  - campus_roads.kml
  - attendance_zones.geojson  (Minimal polygon-only file for spatial engine)

Run: python export_formats.py
"""

import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

COORDS_DIR = "coords_extracted"
RAW_OSM = os.path.join(COORDS_DIR, "raw_osm_v2.json")
if not os.path.exists(RAW_OSM):
    RAW_OSM = os.path.join(COORDS_DIR, "raw_osm.json")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def shoelace_centroid(polygon):
    n = len(polygon)
    if n == 0:
        return 0, 0
    area = cx = cy = 0
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
        return sum(p['lat'] for p in polygon)/n, sum(p['lon'] for p in polygon)/n
    return cy / (6*area), cx / (6*area)

def parse_osm_buildings(raw):
    buildings = []
    for el in raw.get('elements', []):
        tags = el.get('tags', {})
        if 'building' not in tags:
            continue
        polygon = []
        if el['type'] == 'way':
            polygon = [{'lat': p['lat'], 'lon': p['lon']} for p in el.get('geometry', [])]
        elif el['type'] == 'relation':
            for m in el.get('members', []):
                if m.get('role') == 'outer' and m.get('type') == 'way':
                    polygon = [{'lat': p['lat'], 'lon': p['lon']} for p in m.get('geometry', [])]
                    break
        if len(polygon) < 3:
            continue
        lat, lon = shoelace_centroid(polygon)
        buildings.append({
            'id': el['id'],
            'name': tags.get('name') or tags.get('ref') or tags.get('operator'),
            'tags': tags,
            'polygon': polygon,
            'centroid': {'lat': lat, 'lon': lon}
        })
    return buildings

def parse_osm_roads(raw):
    roads = []
    for el in raw.get('elements', []):
        tags = el.get('tags', {})
        if 'highway' not in tags or el['type'] != 'way':
            continue
        coords = [{'lat': p['lat'], 'lon': p['lon']} for p in el.get('geometry', [])]
        if len(coords) < 2:
            continue
        roads.append({'id': el['id'], 'name': tags.get('name'), 'highway': tags.get('highway'), 'coords': coords})
    return roads

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Load raw OSM
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"Loading {RAW_OSM}...")
with open(RAW_OSM, encoding='utf-8') as f:
    raw = json.load(f)

buildings = parse_osm_buildings(raw)
roads     = parse_osm_roads(raw)
print(f"  Buildings: {len(buildings)},  Roads: {len(roads)}")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. master_buildings.geojson  (GeoJSON spec-compliant)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
features = []
for idx, b in enumerate(buildings):
    coords = [[p['lon'], p['lat']] for p in b['polygon']]
    if coords[0] != coords[-1]:
        coords.append(coords[0])   # close ring
    features.append({
        "type": "Feature",
        "id": b['id'],
        "properties": {
            "building_idx": idx + 1,
            "name": b['name'] or f"Building {idx+1}",
            "osm_id": b['id'],
            "source": "osm",
            **{k: v for k, v in b['tags'].items() if k not in ('name',)}
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords]
        }
    })

geojson_path = os.path.join(COORDS_DIR, "master_buildings.geojson")
with open(geojson_path, 'w', encoding='utf-8') as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)
print(f"âœ“ Saved: {geojson_path}")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. attendance_zones.geojson  (slim polygon-only for engine)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
zones = []
for idx, b in enumerate(buildings):
    coords = [[p['lon'], p['lat']] for p in b['polygon']]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    bbox_lats = [p['lat'] for p in b['polygon']]
    bbox_lons = [p['lon'] for p in b['polygon']]
    zones.append({
        "type": "Feature",
        "properties": {
            "building_id": f"osm_{b['id']}",
            "building_idx": idx + 1,
            "name": b['name'] or f"Building {idx+1}"
        },
        "geometry": {"type": "Polygon", "coordinates": [coords]}
    })

zones_path = os.path.join(COORDS_DIR, "attendance_zones.geojson")
with open(zones_path, 'w', encoding='utf-8') as f:
    json.dump({"type": "FeatureCollection", "features": zones}, f, indent=2)
print(f"âœ“ Saved: {zones_path}")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 3. campus.kml  (Google Earth, Google Maps import)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_kml(buildings, roads):
    kml = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, 'Document')
    ET.SubElement(doc, 'name').text = 'NITT Campus Map'
    ET.SubElement(doc, 'description').text = 'NIT Trichy complete campus geofence data'

    # Style: buildings
    style_b = ET.SubElement(doc, 'Style', id='building')
    poly_style = ET.SubElement(style_b, 'PolyStyle')
    ET.SubElement(poly_style, 'color').text = '4d0066ff'  # ABGR
    ET.SubElement(poly_style, 'outline').text = '1'
    line_style = ET.SubElement(style_b, 'LineStyle')
    ET.SubElement(line_style, 'color').text = 'ff0066ff'
    ET.SubElement(line_style, 'width').text = '2'

    # Style: roads
    style_r = ET.SubElement(doc, 'Style', id='road')
    line_style2 = ET.SubElement(style_r, 'LineStyle')
    ET.SubElement(line_style2, 'color').text = 'ff888888'
    ET.SubElement(line_style2, 'width').text = '2'

    # Buildings folder
    folder_b = ET.SubElement(doc, 'Folder')
    ET.SubElement(folder_b, 'name').text = f'Buildings ({len(buildings)})'

    for idx, b in enumerate(buildings):
        pm = ET.SubElement(folder_b, 'Placemark')
        ET.SubElement(pm, 'name').text = b['name'] or f"Building {idx+1}"
        ET.SubElement(pm, 'description').text = '\n'.join(f"{k}: {v}" for k, v in b['tags'].items())
        ET.SubElement(pm, 'styleUrl').text = '#building'
        poly = ET.SubElement(pm, 'Polygon')
        ET.SubElement(poly, 'altitudeMode').text = 'clampToGround'
        outer = ET.SubElement(poly, 'outerBoundaryIs')
        ring = ET.SubElement(outer, 'LinearRing')
        coords_list = b['polygon'] + [b['polygon'][0]]
        coord_str = ' '.join(f"{p['lon']},{p['lat']},0" for p in coords_list)
        ET.SubElement(ring, 'coordinates').text = coord_str

    # Roads folder
    folder_r = ET.SubElement(doc, 'Folder')
    ET.SubElement(folder_r, 'name').text = f'Roads ({len(roads)})'

    for r in roads:
        pm = ET.SubElement(folder_r, 'Placemark')
        ET.SubElement(pm, 'name').text = r['name'] or r['highway']
        ET.SubElement(pm, 'styleUrl').text = '#road'
        ls = ET.SubElement(pm, 'LineString')
        coord_str = ' '.join(f"{p['lon']},{p['lat']},0" for p in r['coords'])
        ET.SubElement(ls, 'coordinates').text = coord_str

    return kml

kml_tree = build_kml(buildings, roads)
kml_str = minidom.parseString(ET.tostring(kml_tree, encoding='unicode')).toprettyxml(indent='  ')
kml_path = os.path.join(COORDS_DIR, "campus.kml")
with open(kml_path, 'w', encoding='utf-8') as f:
    f.write(kml_str)
print(f"âœ“ Saved: {kml_path}")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 4. Summary
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
named = sum(1 for b in buildings if b['name'])
print(f"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘         Export Complete                      â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘  Total Buildings : {len(buildings):<26}â•‘
â•‘  Named Buildings : {named:<26}â•‘
â•‘  Roads           : {len(roads):<26}â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘  master_buildings.geojson  â†’ QGIS / ArcGIS  â•‘
â•‘  attendance_zones.geojson  â†’ Spatial Engine  â•‘
â•‘  campus.kml                â†’ Google Earth    â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
""")

