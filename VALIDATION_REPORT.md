# Ray-Casting Geofencing — Validation Report

**Project:** NITT Campus Geofence Engine  
**Date:** 2026-06-14  
**Dataset:** NIT Tiruchirappalli — OpenStreetMap Overpass API  
**Algorithm:** Ray-Casting Point-in-Polygon (PiP)

---

## 1. Dataset Summary

| Metric | Value |
|---|---|
| Total Building Polygons | **306** |
| Named Buildings | **58** |
| Data Sources | OSM Overpass API (expanded bbox) |
| Campus Bounding Box | `10.7490–10.7780°N, 78.8010–78.8300°E` |
| Extraction Method | Overpass `way[building]` + `relation[building]` |
| Formats Produced | `.geojson`, `.kml`, `.json` |

---

## 2. Algorithm — Ray-Casting PiP

The engine fires a horizontal ray from the query point `(lat, lon)` eastward across the polygon boundary. Edge crossings are counted — **odd = inside, even = outside**.

```
GPS point (lat, lon)
        │
        ▼
  Bounding Box Pre-filter ──── No overlap → SKIP (O(1))
        │
        ▼
  Ray-Casting PiP ────────────── Edge crossing count
        │
        ▼
  Odd crossings → INSIDE    Even crossings → OUTSIDE
```

### Edge Case Handling

| Case | Handling |
|---|---|
| Horizontal edges (`yi == yj`) | Skipped to avoid division by zero |
| Clockwise winding order | Auto-corrected by `fix_winding.py` |
| Unclosed rings | Auto-closed (append first point to end) |
| Concave (L-shaped) polygons | Handled correctly — scanline interior point used for validation |
| Point exactly on edge | Consistent result due to strict `>` comparisons |

---

## 3. Validation Results

### Test 1 — Interior Point Self-Containment (Scanline Method)

Every building polygon was tested by computing a guaranteed-interior point using a horizontal scanline, then checking it against the ray-casting algorithm.

| Metric | Result |
|---|---|
| **Buildings tested** | 306 |
| **PASSED** | **306** ✅ |
| **FAILED** | **0** |
| **Pass rate** | **100%** |
| **Total time** | 2.29 ms |
| **Per building** | 0.0075 ms |

> **Note on concave polygons:** The Shoelace centroid of an L-shaped polygon can legitimately fall outside the polygon boundary. This is not a bug — the scanline interior-point test correctly validates all such cases.

---

### Test 2 — Outside-Campus Rejection

Points clearly outside the NIT Trichy campus must never match any building.

| Test Point | Coordinate | Result |
|---|---|---|
| Chennai City Centre | `(10.0000, 78.0000)` | ✅ PASS — Not inside any building |
| New Delhi | `(28.6139, 77.2090)` | ✅ PASS — Not inside any building |
| SW Bbox Corner | `(10.7490, 78.8010)` | ✅ PASS — Not inside any building |
| NE Bbox Corner | `(10.7780, 78.8300)` | ✅ PASS — Not inside any building |
| Null Island | `(0.0000, 0.0000)` | ✅ PASS — Not inside any building |

---

### Test 3 — Named Building Lookup (Attendance Simulation)

Centroid of each named building was looked up across the full 306-building dataset.

| Building | Lookup Result | Time |
|---|---|---|
| Administrative Block | ✅ HIT — `Administrative block` | 12.0 µs |
| TREC STEP | ✅ HIT — `TREC STEP` | 14.7 µs |
| Training & Placement | ✅ HIT — `Training & Placement new building` | 9.9 µs |
| A Mess | ✅ HIT — `'A' Mess` | 17.2 µs |

---

## 4. Performance Benchmark

**10,000 random GPS points** were tested against all 306 building polygons with bounding-box pre-filtering enabled.

| Metric | Result |
|---|---|
| **Total lookups** | 10,000 |
| **Total time** | 3,668.7 ms |
| **Per lookup** | **0.367 ms (367 µs)** |
| **Throughput** | **2,725 lookups / second** |
| **Campus hit rate** | 198 / 10,000 (~2% — matches expected building coverage) |

### With Grid-Index Engine (`spatial_engine_v2.py`)

The `GeofenceEngine` class adds a **20×20 spatial grid index** over the campus, reducing candidates per lookup from O(n=306) to O(~8).

| Metric | O(n) scan | Grid-indexed |
|---|---|---|
| Candidates per lookup | 306 | ~8 |
| Improvement | 1× | **~38×** |
| Estimated throughput | 2,725/sec | ~100,000/sec |

---

## 5. Data Quality Notes

| Issue | Count | Resolution |
|---|---|---|
| Clockwise winding order | 303 polygons | Auto-fixed by `fix_winding.py` |
| Unclosed rings | 0 | N/A |
| Self-intersecting polygons | 0 | N/A |
| Buildings with no OSM name | 248 | Assigned `Building N` identifier |
| Buildings with OSM name | 58 | Preserved from tags |

---

## 6. Files in this Repository

| File | Purpose |
|---|---|
| `extract_v2.py` | Download raw OSM data via Overpass API |
| `merge_pipeline.py` | Merge sources, reverse-geocode, deduplicate |
| `fix_winding.py` | Normalize all polygon winding orders |
| `export_formats.py` | Export `.geojson`, `.kml`, `attendance_zones.geojson` |
| `spatial_engine_v2.py` | Production geofence engine (grid-indexed PiP) |
| `validate_raycasting.py` | Interior-point + speed validation |
| `test_raycasting.py` | Unit tests for algorithm correctness |
| `map.html` | Interactive map — satellite, draw, rename, test PiP |
| `usage.py` | Integration examples for attendance system |
| `coords_extracted/master_buildings.geojson` | Final 306-building dataset |
| `coords_extracted/attendance_zones.geojson` | Slim polygon-only file for engine |
| `coords_extracted/campus.kml` | Google Earth import |

---

## 7. Conclusion

The ray-casting Point-in-Polygon algorithm is **production-ready** for the NITT faculty attendance geofencing system. All 306 building polygons are geometrically valid, the engine correctly rejects all out-of-campus coordinates, and achieves sub-millisecond lookup latency suitable for real-time GPS tracking.
