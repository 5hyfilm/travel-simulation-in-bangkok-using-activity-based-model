#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

#python export_corridor_geojson.py \
#  --links ../output/output_links.csv.gz \
#  --config-fragment network_paths/PHAYATHAI_SB_config_fragment.json \
#  --out geojson/PHAYATHAI_SB.geojson


#python export_corridor_geojson.py \
#  --links ../output/output_links.csv.gz \
#  --config-fragment network_paths/RAMA1_WB_config_fragment.json \
#  --out geojson/RAMA1_WB.geojson


def open_text_maybe_gzip(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, mode="rt", encoding="utf-8")
    return open(path, mode="rt", encoding="utf-8")


def detect_column(name_candidates: Sequence[str], fieldnames: Sequence[str]) -> Optional[str]:
    lowered = {f.lower(): f for f in fieldnames}
    for candidate in name_candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def parse_wkt_linestring(wkt: str) -> List[List[float]]:
    wkt = wkt.strip()
    coords: List[List[float]] = []

    if wkt.startswith("LINESTRING"):
        inner = wkt[wkt.find("(") + 1 : wkt.rfind(")")]
        chunks = [c.strip() for c in inner.split(",") if c.strip()]
        for c in chunks:
            x_s, y_s = c.split()[:2]
            coords.append([float(x_s), float(y_s)])
        return coords

    if wkt.startswith("MULTILINESTRING"):
        inner = wkt[wkt.find("((") + 2 : wkt.rfind("))")]
        segments = inner.split("),(")
        for seg in segments:
            chunks = [c.strip() for c in seg.split(",") if c.strip()]
            for c in chunks:
                x_s, y_s = c.split()[:2]
                coords.append([float(x_s), float(y_s)])
        return coords

    raise ValueError(f"Unsupported geometry WKT: {wkt[:80]}")


def read_links_geometries(path: Path) -> Dict[str, Dict]:
    with open_text_maybe_gzip(path) as f:
        reader = csv.DictReader(f, delimiter=";")
        if reader.fieldnames is None:
            raise ValueError("Could not read header from output_links.csv.gz")

        link_col = detect_column(["link", "link_id", "id"], reader.fieldnames)
        from_col = detect_column(["from_node", "from"], reader.fieldnames)
        to_col = detect_column(["to_node", "to"], reader.fieldnames)
        origid_col = detect_column(["origid", "orig_id", "origId"], reader.fieldnames)
        geom_col = detect_column(["geometry", "geom", "wkt"], reader.fieldnames)

        if None in (link_col, geom_col):
            raise ValueError(f"Missing required columns in links file. Found: {reader.fieldnames}")

        result: Dict[str, Dict] = {}
        for row in reader:
            link_id = str(row[link_col])
            geom_raw = (row.get(geom_col) or "").strip()
            if not geom_raw:
                continue
            try:
                coords = parse_wkt_linestring(geom_raw)
            except Exception:
                continue

            result[link_id] = {
                "from_node": str(row.get(from_col, "")) if from_col else "",
                "to_node": str(row.get(to_col, "")) if to_col else "",
                "origid": str(row.get(origid_col, "")) if origid_col else "",
                "coordinates": coords,
            }

    return result


def read_link_ids_txt(path: Path) -> List[str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [x for x in lines if x]


def read_config_fragment_json(path: Path) -> Tuple[str, str, List[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    corridor_id = str(raw["corridor_id"])
    corridor_name = str(raw["name"])
    link_ids = [str(x) for x in raw["link_ids"]]
    return corridor_id, corridor_name, link_ids


def build_geojson_features(
    corridor_id: str,
    corridor_name: str,
    link_ids: List[str],
    links_geom: Dict[str, Dict],
) -> Dict:
    features = []

    for idx, link_id in enumerate(link_ids):
        if link_id not in links_geom:
            continue

        g = links_geom[link_id]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "corridor_id": corridor_id,
                    "corridor_name": corridor_name,
                    "sequence": idx,
                    "link_id": link_id,
                    "from_node": g["from_node"],
                    "to_node": g["to_node"],
                    "origid": g["origid"],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": g["coordinates"],
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "name": corridor_id,
        "crs": {
            "type": "name",
            "properties": {
                "name": "EPSG:32647"
            }
        },
        "features": features,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export MATSim corridor link_ids to GeoJSON")
    parser.add_argument("--links", required=True, type=Path, help="Path to output_links.csv.gz")
    parser.add_argument("--link-ids", type=Path, help="Path to *_connected_link_ids.txt")
    parser.add_argument("--config-fragment", type=Path, help="Path to *_config_fragment.json")
    parser.add_argument("--corridor-id", type=str, default="CORRIDOR", help="Used with --link-ids")
    parser.add_argument("--corridor-name", type=str, default="Corridor", help="Used with --link-ids")
    parser.add_argument("--out", required=True, type=Path, help="Output GeoJSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if bool(args.link_ids) == bool(args.config_fragment):
        raise ValueError("Use exactly one of --link-ids or --config-fragment")

    links_geom = read_links_geometries(args.links)

    if args.config_fragment:
        corridor_id, corridor_name, link_ids = read_config_fragment_json(args.config_fragment)
    else:
        corridor_id = args.corridor_id
        corridor_name = args.corridor_name
        link_ids = read_link_ids_txt(args.link_ids)

    geojson = build_geojson_features(corridor_id, corridor_name, link_ids, links_geom)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(geojson, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved GeoJSON: {args.out}")
    print(f"Feature count: {len(geojson['features'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
