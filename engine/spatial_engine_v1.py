import json
import os
import math

class GeofenceEngine:
    def __init__(self, polygons_file):
        """
        Initializes the geofence engine by loading the building polygons.
        :param polygons_file: Path to attendance_polygons.json
        """
        self.buildings = []
        self._load_polygons(polygons_file)

    def _load_polygons(self, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Polygon file not found: {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for b in data:
            building_id = b.get("building_id")
            polygon = b.get("polygon", [])
            if building_id and polygon:
                # Precompute bounding box for fast filtering
                lats = [pt["lat"] for pt in polygon]
                lons = [pt["lon"] for pt in polygon]
                bbox = {
                    "min_lat": min(lats),
                    "max_lat": max(lats),
                    "min_lon": min(lons),
                    "max_lon": max(lons)
                }
                
                self.buildings.append({
                    "id": building_id,
                    "polygon": polygon,
                    "bbox": bbox
                })

    def _is_in_bbox(self, lat, lon, bbox):
        return (bbox["min_lat"] <= lat <= bbox["max_lat"] and 
                bbox["min_lon"] <= lon <= bbox["max_lon"])

    def _ray_cast(self, x, y, polygon):
        """
        Ray-casting algorithm for Point-in-Polygon validation.
        x = longitude, y = latitude
        """
        inside = False
        n = len(polygon)
        for i in range(n):
            j = (i - 1) % n
            xi, yi = polygon[i]['lon'], polygon[i]['lat']
            xj, yj = polygon[j]['lon'], polygon[j]['lat']
            
            # Avoid division by zero
            if yi == yj:
                continue
                
            intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
            if intersect:
                inside = not inside
        return inside

    def lookup_building(self, lat, lon):
        """
        Takes a latitude and longitude and returns the building_id if it falls inside one.
        Returns None if not inside any building.
        """
        for building in self.buildings:
            # 1. Fast bounding box check
            if not self._is_in_bbox(lat, lon, building["bbox"]):
                continue
                
            # 2. Precise ray-casting check
            if self._ray_cast(lon, lat, building["polygon"]):
                return building["id"]
                
        return None

if __name__ == "__main__":
    # Simple test using the extracted polygons
    engine = GeofenceEngine(os.path.join("coords_extracted", "attendance_polygons.json"))
    print(f"Loaded {len(engine.buildings)} buildings into the spatial engine.")
    
    # Just an arbitrary point within NITT bounding box (might not hit a building)
    test_lat, test_lon = 10.760, 78.813
    print(f"Testing lookup for {test_lat}, {test_lon}...")
    result = engine.lookup_building(test_lat, test_lon)
    if result:
        print(f"Match found! Point is inside Building ID: {result}")
    else:
        print("Point is not inside any registered building footprint.")
