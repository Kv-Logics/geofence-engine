"""
Phase 1 - Microsoft Global ML Building Footprints
Downloads and filters the open-source satellite-derived building footprints
from Microsoft's dataset for the NITT campus area.
Dataset: https://github.com/microsoft/GlobalMLBuildingFootprints
"""
import json
import urllib.request
import gzip
import os

OUT_DIR = "coords_extracted"
os.makedirs(OUT_DIR, exist_ok=True)

# NITT campus bounding box
MIN_LAT, MAX_LAT = 10.7490, 10.7780
MIN_LON, MAX_LON = 78.8010, 78.8300

# Microsoft dataset - India quadkey tile containing NITT
# Source: https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv
# NITT is approximately at quadkey level 9: 120221303
# We use the country-level filtered approach
INDIA_URL = "https://minedbuildings.blob.core.windows.net/global-buildings/2023-04-25/India.geojsonl.gz"

out_path = os.path.join(OUT_DIR, "microsoft_footprints.json")

def in_bbox(feature):
    coords = feature.get("geometry", {}).get("coordinates", [[]])[0]
    if not coords:
        return False
    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    if not lats or not lons:
        return False
    return (
        max(lats) >= MIN_LAT and min(lats) <= MAX_LAT and
        max(lons) >= MIN_LON and min(lons) <= MAX_LON
    )

print("Downloading Microsoft Global Building Footprints (India)...")
print("This is a large file - streaming and filtering on the fly...")

filtered = []
bytes_read = 0

try:
    req = urllib.request.Request(INDIA_URL, headers={'User-Agent': 'NITT-GeofenceEngine/2.0'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        with gzip.open(resp, 'rt', encoding='utf-8') as gz:
            for line in gz:
                bytes_read += len(line)
                if bytes_read % (10 * 1024 * 1024) < len(line):
                    print(f"  Read {bytes_read // (1024*1024)} MB, found {len(filtered)} buildings so far...")
                try:
                    feature = json.loads(line.strip())
                    if in_bbox(feature):
                        filtered.append(feature)
                except json.JSONDecodeError:
                    continue

    print(f"Done. Found {len(filtered)} Microsoft buildings in NITT area.")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": filtered, "source": "microsoft_ml"}, f, indent=2)
    print(f"Saved to: {out_path}")

except Exception as e:
    print(f"Download failed: {e}")
    print("Creating empty Microsoft footprints file to continue pipeline...")
    with open(out_path, 'w') as f:
        json.dump({"type": "FeatureCollection", "features": [], "source": "microsoft_ml"}, f)
