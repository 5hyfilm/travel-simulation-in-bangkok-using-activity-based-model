"""
export_signal_locations.py
--------------------------
Reads signalSystems.xml and network.cleaned.xml.gz to extract
the coordinates of every junction that has a traffic signal.

Outputs:
  output/signal_locations.csv     — node_id, x_utm, y_utm, lat, lon, num_signals
  output/signal_locations.geojson — GeoJSON PointFeatureCollection
"""

import gzip
import json
import csv
import xml.etree.ElementTree as ET
from pyproj import Transformer

# --- Paths (run from preprocess/ folder) ---
SIGNAL_SYSTEMS_FILE = "../data/processed/signalSystems.xml"
NETWORK_FILE        = "../data/processed/network.cleaned.xml.gz"
OUT_CSV             = "output/signal_locations.csv"
OUT_GEOJSON         = "output/signal_locations.geojson"

# EPSG:32647 (UTM Zone 47N, Bangkok) → WGS84
transformer = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)


def load_signal_node_ids(path):
    """Return dict: node_id (str) → number of signals at that junction."""
    print(f"Reading signal systems from: {path}")
    tree = ET.parse(path)
    root = tree.getroot()

    # Handle optional XML namespace
    ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

    node_signal_count = {}
    for system in root.findall(f"{ns}signalSystem"):
        node_id = system.get("id")
        signals = system.findall(f"{ns}signals/{ns}signal")
        node_signal_count[node_id] = len(signals)

    print(f"  Found {len(node_signal_count)} signal systems (junctions with signals)")
    return node_signal_count


def load_node_coords(path, node_ids):
    """Return dict: node_id (str) → (x, y) in UTM from the network file."""
    print(f"Reading network from: {path}")
    coords = {}
    target_ids = set(node_ids)

    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as f:
        for event, elem in ET.iterparse(f, events=("start",)):
            if elem.tag == "node" or elem.tag.endswith("}node"):
                nid = elem.get("id")
                if nid in target_ids:
                    coords[nid] = (float(elem.get("x")), float(elem.get("y")))
                elem.clear()
            if len(coords) == len(target_ids):
                break  # stop early once all found

    print(f"  Matched coordinates for {len(coords)} / {len(target_ids)} nodes")
    return coords


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["node_id", "x_utm", "y_utm", "lon", "lat", "num_signals"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV saved: {path}  ({len(rows)} rows)")


def write_geojson(rows, path):
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["lon"], row["lat"]]
            },
            "properties": {
                "node_id":    row["node_id"],
                "x_utm":      row["x_utm"],
                "y_utm":      row["y_utm"],
                "num_signals": row["num_signals"]
            }
        })
    geojson = {"type": "FeatureCollection", "features": features}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"GeoJSON saved: {path}  ({len(features)} features)")


def main():
    print("=== Exporting signal junction locations ===\n")

    # 1. Get node IDs that have signals
    node_signal_count = load_signal_node_ids(SIGNAL_SYSTEMS_FILE)

    # 2. Get UTM coordinates from network
    coords = load_node_coords(NETWORK_FILE, node_signal_count.keys())

    # 3. Build rows, convert UTM → WGS84
    rows = []
    missing = 0
    for node_id, num_signals in node_signal_count.items():
        if node_id not in coords:
            missing += 1
            continue
        x, y = coords[node_id]
        lon, lat = transformer.transform(x, y)
        rows.append({
            "node_id":    node_id,
            "x_utm":      round(x, 3),
            "y_utm":      round(y, 3),
            "lon":        round(lon, 7),
            "lat":        round(lat, 7),
            "num_signals": num_signals
        })

    if missing:
        print(f"  Warning: {missing} nodes not found in network (may have been cleaned out)")

    # 4. Write outputs
    print()
    write_csv(rows, OUT_CSV)
    write_geojson(rows, OUT_GEOJSON)

    print(f"\n=== Done! {len(rows)} signal junctions exported ===")
    print(f"  → {OUT_CSV}")
    print(f"  → {OUT_GEOJSON}")


if __name__ == "__main__":
    main()
