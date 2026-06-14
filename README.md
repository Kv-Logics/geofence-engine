# Geofence Engine

> **Production-grade geospatial mapping and location intelligence system for NIT Tiruchirappalli campus.**  
> Standalone map extraction, polygon geofencing, spatial indexing, and coordinate-to-building resolution.

[![Dataset](https://img.shields.io/badge/Buildings-306%20Polygons-blue)](#)
[![Algorithm](https://img.shields.io/badge/Algorithm-Ray--Casting%20PiP-orange)](#)
[![Pass Rate](https://img.shields.io/badge/Validation-100%25%20Pass-brightgreen)](#)
[![Throughput](https://img.shields.io/badge/Throughput-2%2C725%20lookups%2Fsec-green)](#)

---

## Overview

This repository extracts the complete NIT Trichy campus from OpenStreetMap, validates every building polygon using a ray-casting Point-in-Polygon algorithm, and provides a production spatial engine for faculty attendance geofencing.

```
GPS Ping (lat, lon)
       │
       ▼
 Bounding Box Pre-filter ── No → SKIP
       │ Yes
       ▼
 Ray-Casting PiP
       │
       ▼
 { building_id, name, polygon }
```

---

## Repository Structure

```
geofence-engine/
├── extract_v2.py              ← OSM Overpass extraction (expanded bbox)
├── merge_pipeline.py          ← Merge, deduplicate, reverse-geocode
├── fix_winding.py             ← Auto-fix polygon winding order
├── export_formats.py          ← Export .geojson / .kml / attendance zones
├── spatial_engine_v2.py       ← Grid-indexed PiP engine (production)
├── spatial_engine.py          ← Linear scan PiP engine (reference)
├── validate_raycasting.py     ← Interior-point + speed benchmark
├── test_raycasting.py         ← Unit tests
├── usage.py                   ← Attendance system integration examples
├── map.html                   ← Interactive map (satellite, edit, test)
├── run_map.bat                ← One-click local server launcher
├── VALIDATION_REPORT.md       ← Full algorithm validation report
└── coords_extracted/
    ├── master_buildings.geojson     ← 306 buildings (primary dataset)
    ├── attendance_zones.geojson     ← Slim polygons for engine
    ├── campus_boundary.geojson      ← Campus perimeter
    ├── buildings.geojson            ← Raw OSM buildings
    ├── roads.geojson                ← Campus road network
    ├── campus.kml                   ← Google Earth format
    ├── raw_osm.json                 ← Raw Overpass response
    └── raw_osm_v2.json              ← Expanded Overpass response
```

---

## Dataset

| Metric | Value |
|---|---|
| Total Building Polygons | **306** |
| Named Buildings | **58** |
| Campus Bounding Box | `10.7490–10.7780°N, 78.8010–78.8300°E` |
| Data Source | OpenStreetMap Overpass API |
| Formats | GeoJSON · KML · JSON |

---

## Quick Start

### 1. View the Interactive Map

```bash
# Double-click run_map.bat  OR manually:
cd "geofence-engine"
python -m http.server 8000
# Open: http://localhost:8000/map.html
```

The map loads on **real Esri satellite imagery** with:
- 🔢 Numbered markers (`1 → Library`, `2 → Admin Block` ...)
- 📋 Left sidebar with searchable `number → name` list
- ✏️ Draw new building polygons
- 🔧 Edit existing polygon vertices
- ✍️ Rename any building inline
- ⚡ Live geofence test panel (click map → check which building)

### 2. Geofence Lookup (Python)

```python
from spatial_engine_v2 import GeofenceEngine

engine = GeofenceEngine("coords_extracted/master_buildings.json")

# Single GPS lookup
result = engine.lookup(lat=10.7621, lon=78.8137)

if result:
    print(f"Inside: {result['name']}  (ID: {result['building_id']})")
else:
    print("Not inside any registered building")
```

### 3. Re-Extract Campus Data

```bash
python extract_v2.py          # Download latest OSM data
python fix_winding.py         # Fix polygon winding order
python export_formats.py      # Generate all output formats
```

### 4. Run Validation

```bash
python validate_raycasting.py
```

---

## Algorithm

### Ray-Casting Point-in-Polygon

```python
def ray_cast(lon, lat, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        j = (i - 1) % n
        xi, yi = ring[i][0], ring[i][1]   # lon, lat
        xj, yj = ring[j][0], ring[j][1]
        if yi == yj: continue              # skip horizontal edges
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
    return inside
```

### Grid-Indexed Spatial Engine

The `GeofenceEngine` in `spatial_engine_v2.py` divides the campus into a **20×20 grid**. Each lookup queries only the ~8 buildings in the relevant cell instead of all 306 — a **~38× speedup**.

```
Campus bbox → 20×20 grid cells
Each building → registered in overlapping cells
GPS query → cell lookup → ~8 candidates → ray-cast
```

---

## Validation Results

> Full details in [VALIDATION_REPORT.md](./VALIDATION_REPORT.md)

### Algorithm Correctness

| Test | Result |
|---|---|
| Interior-point self-containment (306 polygons) | ✅ **306/306 — 100% PASS** |
| Outside-campus rejection (5 points) | ✅ **5/5 — 100% PASS** |
| Named building lookup (attendance simulation) | ✅ **4/4 HIT** |
| Degenerate / self-intersecting polygons | ✅ **0 found** |

### Performance Benchmark (10,000 lookups)

| Metric | Value |
|---|---|
| Per lookup | **0.367 ms (367 µs)** |
| Throughput | **2,725 lookups / second** |
| With grid index (estimated) | **~100,000 lookups / second** |

---

## Integration Example — Attendance System

```python
from spatial_engine_v2 import GeofenceEngine

engine = GeofenceEngine("coords_extracted/master_buildings.json")

# Batch attendance check
faculty_pings = [
    {"id": "FAC001", "name": "Dr. Kumar", "lat": 10.7621, "lon": 78.8137},
    {"id": "FAC002", "name": "Dr. Priya", "lat": 10.7638, "lon": 78.8152},
]

for faculty in faculty_pings:
    building = engine.lookup(faculty["lat"], faculty["lon"])
    status   = "PRESENT" if building else "ABSENT"
    location = building["name"] if building else "Off Campus"
    print(f"{faculty['name']} → {status} @ {location}")
```

---

## Data Formats

### `master_buildings.geojson`
Standard GeoJSON FeatureCollection. Opens directly in **QGIS**, **ArcGIS**, **Mapbox Studio**, **Google Earth Pro**.

### `attendance_zones.geojson`
Minimal polygon-only file optimised for spatial engine loading:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": { "building_id": "osm_123456", "name": "Library" },
    "geometry": { "type": "Polygon", "coordinates": [[...]] }
  }]
}
```

### `campus.kml`
Import into **Google Earth** or **Google Maps** (My Maps → Import).

---

## License

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) — [ODbL](https://opendatacommons.org/licenses/odbl/).  
Code — MIT License.
