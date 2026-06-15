"""
Phase 3 - Spatial Engine v2 (Grid-Indexed Ray-Casting)
Production-grade Point-in-Polygon engine using a spatial grid index
for O(1) average-case building lookup from GPS coordinates.
"""
import json
import os
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_PATH = os.path.join(BASE_DIR, "data", "master_buildings.json")

class GeofenceEngine:
    """
    High-performance geofence engine using a spatial grid index.
    
    Architecture:
    1. On load, the campus bbox is divided into a GRID_SIZE x GRID_SIZE grid.
    2. Each building is registered into every grid cell its bbox overlaps.
    3. On lookup, we instantly find the 1-4 grid cells the point falls in.
    4. Ray-casting is only run on the small set of candidate buildings.
    
    Result: O(1) average case lookup vs O(n) linear scan.
    """

    GRID_SIZE = 20  # 20x20 grid over campus

    def __init__(self, master_json_path=MASTER_PATH):
        self.buildings = []
        self.grid = {}
        self.campus_bbox = {
            "min_lat": 10.7490, "max_lat": 10.7780,
            "min_lon": 78.8010, "max_lon": 78.8300
        }
        self._load(master_json_path)
        self._build_grid()

    def _load(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.buildings = data.get('buildings', data if isinstance(data, list) else [])
        print(f"[GeofenceEngine] Loaded {len(self.buildings)} buildings.")

    def _cell(self, lat, lon):
        """Map a lat/lon to a grid cell index (row, col)."""
        cb = self.campus_bbox
        lat_range = cb['max_lat'] - cb['min_lat']
        lon_range = cb['max_lon'] - cb['min_lon']
        row = int((lat - cb['min_lat']) / lat_range * self.GRID_SIZE)
        col = int((lon - cb['min_lon']) / lon_range * self.GRID_SIZE)
        row = max(0, min(self.GRID_SIZE - 1, row))
        col = max(0, min(self.GRID_SIZE - 1, col))
        return (row, col)

    def _cells_for_bbox(self, bbox):
        """Return all grid cells that a building's bbox overlaps."""
        r1, c1 = self._cell(bbox['min_lat'], bbox['min_lon'])
        r2, c2 = self._cell(bbox['max_lat'], bbox['max_lon'])
        cells = []
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                cells.append((r, c))
        return cells

    def _build_grid(self):
        for idx, building in enumerate(self.buildings):
            bbox = building.get('bbox')
            if not bbox:
                # Compute bbox on the fly
                polygon = building.get('polygon', [])
                if not polygon:
                    continue
                lats = [p['lat'] for p in polygon]
                lons = [p['lon'] for p in polygon]
                bbox = {
                    'min_lat': min(lats), 'max_lat': max(lats),
                    'min_lon': min(lons), 'max_lon': max(lons)
                }
                building['bbox'] = bbox

            for cell in self._cells_for_bbox(bbox):
                self.grid.setdefault(cell, []).append(idx)

        occupied = len(self.grid)
        print(f"[GeofenceEngine] Grid built: {self.GRID_SIZE}x{self.GRID_SIZE} cells, {occupied} occupied.")

    @staticmethod
    def _ray_cast(lat, lon, polygon):
        """
        Ray-casting Point-in-Polygon algorithm.
        Fires a ray from (lat, lon) eastward and counts edge crossings.
        Odd crossings = inside polygon.
        """
        inside = False
        n = len(polygon)
        for i in range(n):
            j = (i - 1) % n
            yi = polygon[i]['lat']
            yj = polygon[j]['lat']
            xi = polygon[i]['lon']
            xj = polygon[j]['lon']
            if yi == yj:
                continue
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
        return inside

    def lookup(self, lat, lon):
        """
        Returns the building dict if point (lat, lon) is inside one.
        Returns None if not inside any building.
        """
        cell = self._cell(lat, lon)
        candidates_idx = self.grid.get(cell, [])
        for idx in candidates_idx:
            b = self.buildings[idx]
            if self._ray_cast(lat, lon, b.get('polygon', [])):
                return b
        return None

    def lookup_id(self, lat, lon):
        """Convenience: returns just the building_id string or None."""
        result = self.lookup(lat, lon)
        return result['building_id'] if result else None

    def all_buildings(self):
        return self.buildings

    def stats(self):
        named = sum(1 for b in self.buildings if b.get('resolved_name') or b.get('name'))
        return {
            "total": len(self.buildings),
            "named": named,
            "unnamed": len(self.buildings) - named,
            "grid_cells_occupied": len(self.grid)
        }


# ─── Unit Test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = GeofenceEngine()
    print(f"\nStats: {engine.stats()}")

    # Test 1: Known centroid of a building should return that building
    print("\n─── Centroid Tests ───")
    hits = 0
    for b in engine.buildings[:10]:
        lat = b['centroid']['lat']
        lon = b['centroid']['lon']
        result = engine.lookup(lat, lon)
        status = "✓ HIT" if result else "✗ MISS"
        name = b.get('resolved_name') or b.get('name') or b['building_id']
        print(f"  {status} | {name[:40]:<40} | ({lat:.5f}, {lon:.5f})")
        if result:
            hits += 1

    print(f"\nCentroid accuracy: {hits}/10")

    # Test 2: Point outside campus
    result = engine.lookup(10.000, 78.000)
    print(f"\nOutside campus test: {'✓ Correctly returned None' if result is None else '✗ ERROR: should be None'}")
