#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from heapq import heappush, heappop

from pyproj import Transformer

# WGS84 -> UTM47N for your Bangkok MATSim network
WGS84_TO_UTM47 = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True)

#python build_paths_from_network.py \
#  --network ../output/output_network.xml.gz \
#  --corridors corridors_for_network.json \
#  --outdir network_paths \
#  --weight time

@dataclass
class Node:
    node_id: str
    x: float
    y: float


@dataclass
class Link:
    link_id: str
    from_node: str
    to_node: str
    length_m: float
    freespeed_mps: float


@dataclass
class CorridorInput:
    corridor_id: str
    name: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float


def open_text_maybe_gzip(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, mode="rt", encoding="utf-8")
    return open(path, mode="rt", encoding="utf-8")


def latlng_to_utm47(lat: float, lng: float) -> Tuple[float, float]:
    x, y = WGS84_TO_UTM47.transform(lng, lat)
    return x, y


def euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def parse_network(network_path: Path) -> Tuple[Dict[str, Node], Dict[str, Link]]:
    nodes: Dict[str, Node] = {}
    links: Dict[str, Link] = {}

    with open_text_maybe_gzip(network_path) as f:
        context = ET.iterparse(f, events=("start", "end"))
        for event, elem in context:
            if event == "end" and elem.tag == "node":
                node_id = str(elem.attrib["id"])
                x = float(elem.attrib["x"])
                y = float(elem.attrib["y"])
                nodes[node_id] = Node(node_id=node_id, x=x, y=y)
                elem.clear()

            elif event == "end" and elem.tag == "link":
                link_id = str(elem.attrib["id"])
                from_node = str(elem.attrib["from"])
                to_node = str(elem.attrib["to"])
                length_m = float(elem.attrib.get("length", 0.0))
                freespeed_mps = float(elem.attrib.get("freespeed", 1.0))
                links[link_id] = Link(
                    link_id=link_id,
                    from_node=from_node,
                    to_node=to_node,
                    length_m=length_m,
                    freespeed_mps=freespeed_mps,
                )
                elem.clear()

    return nodes, links


def read_corridors_json(path: Path) -> List[CorridorInput]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    corridors: List[CorridorInput] = []

    for item in raw["corridors"]:
        corridors.append(
            CorridorInput(
                corridor_id=str(item["corridor_id"]),
                name=str(item["name"]),
                origin_lat=float(item["origin_lat"]),
                origin_lng=float(item["origin_lng"]),
                destination_lat=float(item["destination_lat"]),
                destination_lng=float(item["destination_lng"]),
            )
        )

    return corridors


def nearest_node_id(nodes: Dict[str, Node], x: float, y: float) -> str:
    best_id: Optional[str] = None
    best_dist = float("inf")

    for node_id, node in nodes.items():
        d = euclidean((x, y), (node.x, node.y))
        if d < best_dist:
            best_dist = d
            best_id = node_id

    if best_id is None:
        raise ValueError("No nearest node found.")
    return best_id


def build_adjacency(links: Dict[str, Link], weight_mode: str) -> Dict[str, List[Tuple[str, str, float]]]:
    """
    adjacency[from_node] = [(to_node, link_id, weight), ...]
    """
    adj: Dict[str, List[Tuple[str, str, float]]] = {}

    for link in links.values():
        if weight_mode == "time":
            weight = link.length_m / max(link.freespeed_mps, 1e-6)
        elif weight_mode == "length":
            weight = link.length_m
        else:
            raise ValueError(f"Unsupported weight_mode: {weight_mode}")

        adj.setdefault(link.from_node, []).append((link.to_node, link.link_id, weight))

    return adj


def shortest_path(
    start_node: str,
    end_node: str,
    adjacency: Dict[str, List[Tuple[str, str, float]]],
) -> List[str]:
    """
    Returns list of link_ids
    """
    pq: List[Tuple[float, str]] = []
    heappush(pq, (0.0, start_node))

    dist_map: Dict[str, float] = {start_node: 0.0}
    prev_node: Dict[str, str] = {}
    prev_link: Dict[str, str] = {}
    visited = set()

    while pq:
        cur_dist, cur_node = heappop(pq)

        if cur_node in visited:
            continue
        visited.add(cur_node)

        if cur_node == end_node:
            break

        for nxt_node, link_id, weight in adjacency.get(cur_node, []):
            cand = cur_dist + weight
            if nxt_node not in dist_map or cand < dist_map[nxt_node]:
                dist_map[nxt_node] = cand
                prev_node[nxt_node] = cur_node
                prev_link[nxt_node] = link_id
                heappush(pq, (cand, nxt_node))

    if end_node not in dist_map:
        return []

    path_links: List[str] = []
    cur = end_node
    while cur != start_node:
        path_links.append(prev_link[cur])
        cur = prev_node[cur]
    path_links.reverse()
    return path_links


def path_total_length(path_links: List[str], links: Dict[str, Link]) -> float:
    return sum(links[lid].length_m for lid in path_links)


def path_total_ff_time(path_links: List[str], links: Dict[str, Link]) -> float:
    return sum(links[lid].length_m / max(links[lid].freespeed_mps, 1e-6) for lid in path_links)


def export_config(
    corridors: List[CorridorInput],
    path_map: Dict[str, List[str]],
    outpath: Path,
) -> None:
    data = {"corridors": []}
    for c in corridors:
        data["corridors"].append(
            {
                "corridor_id": c.corridor_id,
                "name": c.name,
                "origin_lat": c.origin_lat,
                "origin_lng": c.origin_lng,
                "destination_lat": c.destination_lat,
                "destination_lng": c.destination_lng,
                "link_ids": path_map[c.corridor_id],
            }
        )
    outpath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MATSim corridor paths directly from network.xml.gz")
    parser.add_argument("--network", required=True, type=Path, help="Path to network.xml or network.xml.gz")
    parser.add_argument("--corridors", required=True, type=Path, help="Input corridors JSON with origin/destination lat/lng")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    parser.add_argument("--weight", choices=["time", "length"], default="time", help="Shortest path weight")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    print("Parsing network...")
    nodes, links = parse_network(args.network)
    print(f"Loaded {len(nodes)} nodes, {len(links)} links")

    corridors = read_corridors_json(args.corridors)
    adjacency = build_adjacency(links, args.weight)

    path_map: Dict[str, List[str]] = {}

    for c in corridors:
        ox, oy = latlng_to_utm47(c.origin_lat, c.origin_lng)
        dx, dy = latlng_to_utm47(c.destination_lat, c.destination_lng)

        start_node = nearest_node_id(nodes, ox, oy)
        end_node = nearest_node_id(nodes, dx, dy)

        path_links = shortest_path(start_node, end_node, adjacency)
        if not path_links:
            print(f"[{c.corridor_id}] No path found")
            path_map[c.corridor_id] = []
            continue

        total_len = path_total_length(path_links, links)
        total_ff = path_total_ff_time(path_links, links)

        print(f"[{c.corridor_id}] start_node={start_node} end_node={end_node}")
        print(f"[{c.corridor_id}] link_count={len(path_links)}")
        print(f"[{c.corridor_id}] total_length_m={total_len:.3f}")
        print(f"[{c.corridor_id}] freeflow_time_s={total_ff:.3f}")

        path_map[c.corridor_id] = path_links

        frag = {
            "corridor_id": c.corridor_id,
            "name": c.name,
            "origin_lat": c.origin_lat,
            "origin_lng": c.origin_lng,
            "destination_lat": c.destination_lat,
            "destination_lng": c.destination_lng,
            "link_ids": path_links,
        }
        (args.outdir / f"{c.corridor_id}_config_fragment.json").write_text(
            json.dumps(frag, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (args.outdir / f"{c.corridor_id}_link_ids.txt").write_text(
            "\n".join(path_links),
            encoding="utf-8",
        )

    export_config(corridors, path_map, args.outdir / "config_corridors_from_network.json")
    print(f"Saved outputs to: {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())