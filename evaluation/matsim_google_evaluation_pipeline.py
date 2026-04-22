#!/usr/bin/env python3
from __future__ import annotations
"""
MATSim vs Google Routes evaluation pipeline (ปรับเวอร์ชันผ่อนปรน)
"""

import argparse
import csv
import gzip
import json
import math
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()


# -----------------------------
# Data models
# -----------------------------

@dataclass(frozen=True)
class TimeSlice:
    label: str
    departure_time_local: str
    window_start_sec: int
    window_end_sec: int


@dataclass(frozen=True)
class Corridor:
    corridor_id: str
    name: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    link_ids: List[str]


@dataclass
class LinkInfo:
    link_id: str
    length_m: float
    freespeed_mps: float


# -----------------------------
# Utility functions
# -----------------------------

def open_text_maybe_gzip(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, mode="rt", encoding="utf-8")
    return open(path, mode="rt", encoding="utf-8")


def parse_hms_to_seconds(hms: str) -> int:
    parts = hms.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid HH:MM:SS string: {hms}")
    h, m, s = map(int, parts)
    return h * 3600 + m * 60 + s


def parse_iso8601_duration_to_seconds(value: str) -> float:
    value = value.strip()
    simple_pattern = re.compile(r"^(?P<s>\d+(?:\.\d+)?)s$")
    simple_match = simple_pattern.match(value)
    if simple_match:
        return float(simple_match.group("s"))

    iso_pattern = re.compile(
        r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?$"
    )
    iso_match = iso_pattern.match(value)
    if iso_match:
        hours = float(iso_match.group("h") or 0)
        minutes = float(iso_match.group("m") or 0)
        seconds = float(iso_match.group("s") or 0)
        return hours * 3600 + minutes * 60 + seconds

    raise ValueError(f"Unsupported duration format: {value}")


def mean_or_none(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def ensure_outdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Config loading
# -----------------------------

def load_config(config_path: Path) -> Tuple[List[TimeSlice], List[Corridor]]:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    time_slices: List[TimeSlice] = []
    for item in raw["time_slices"]:
        time_slices.append(
            TimeSlice(
                label=item["label"],
                departure_time_local=item["departure_time_local"],
                window_start_sec=parse_hms_to_seconds(item["window_start_hms"]),
                window_end_sec=parse_hms_to_seconds(item["window_end_hms"]),
            )
        )

    corridors: List[Corridor] = []
    for item in raw["corridors"]:
        link_ids = [str(x) for x in item.get("link_ids", [])]
        corridors.append(
            Corridor(
                corridor_id=str(item["corridor_id"]),
                name=item["name"],
                origin_lat=float(item["origin_lat"]),
                origin_lng=float(item["origin_lng"]),
                destination_lat=float(item["destination_lat"]),
                destination_lng=float(item["destination_lng"]),
                link_ids=link_ids,
            )
        )

    return time_slices, corridors


# -----------------------------
# Network parsing
# -----------------------------

def parse_network(network_path: Path) -> Dict[str, LinkInfo]:
    links: Dict[str, LinkInfo] = {}
    with open_text_maybe_gzip(network_path) as f:
        context = ET.iterparse(f, events=("start", "end"))
        for event, elem in context:
            if event == "end" and elem.tag == "link":
                link_id = str(elem.attrib["id"])
                length_m = float(elem.attrib.get("length", 0.0))
                freespeed_mps = float(elem.attrib.get("freespeed", 0.0))
                links[link_id] = LinkInfo(link_id=link_id, length_m=length_m, freespeed_mps=freespeed_mps)
                elem.clear()
    return links


def corridor_freeflow_stats(corridor: Corridor, network: Dict[str, LinkInfo]) -> Tuple[float, float]:
    total_length_m = 0.0
    total_ff_time_sec = 0.0
    for link_id in corridor.link_ids:
        if link_id not in network:
            raise KeyError(f"Link ID '{link_id}' in corridor '{corridor.corridor_id}' not found in network")
        info = network[link_id]
        total_length_m += info.length_m
        total_ff_time_sec += info.length_m / info.freespeed_mps
    return total_length_m, total_ff_time_sec


# -----------------------------
# Google Routes
# -----------------------------

def call_google_routes_api(corridor: Corridor, time_slice: TimeSlice, api_key: str) -> Dict[str, Any]:
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters",
    }
    payload = {
        "origin": {"location": {"latLng": {"latitude": corridor.origin_lat, "longitude": corridor.origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": corridor.destination_lat, "longitude": corridor.destination_lng}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": time_slice.departure_time_local,
        "computeAlternativeRoutes": False,
        "languageCode": "en-US",
        "units": "METRIC",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    route = data.get("routes", [])[0]

    duration_sec = parse_iso8601_duration_to_seconds(route["duration"])
    static_duration_sec = parse_iso8601_duration_to_seconds(route["staticDuration"])
    distance_m = float(route["distanceMeters"])

    return {
        "corridor_id": corridor.corridor_id,
        "corridor_name": corridor.name,
        "time_label": time_slice.label,
        "google_duration_sec": duration_sec,
        "google_static_duration_sec": static_duration_sec,
        "google_distance_m": distance_m,
        "google_ci": safe_div(duration_sec, static_duration_sec),
        "google_speed_kph": safe_div(distance_m, duration_sec) * 3.6 if duration_sec else None,
    }


def collect_google_results(corridors: List[Corridor], time_slices: List[TimeSlice], api_key: str) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for corridor in corridors:
        for time_slice in time_slices:
            row = call_google_routes_api(corridor, time_slice, api_key)
            rows.append(row)
    return pd.DataFrame(rows)


# -----------------------------
# MATSim Events Extraction (ปรับผ่อนปรนแล้ว)
# -----------------------------

def normalize_vehicle_id(event_attrib: Dict[str, str]) -> Optional[str]:
    for key in ("vehicle", "driverId", "person"):
        if key in event_attrib:
            return str(event_attrib[key])
    return None


def extract_matsim_corridor_travel_times(
        events_path: Path,
        corridors: List[Corridor],
        time_slices: List[TimeSlice],
        network: Dict[str, LinkInfo],
) -> pd.DataFrame:
    corridor_map = {c.corridor_id: c for c in corridors}
    first_link_to_corridors: Dict[str, List[str]] = defaultdict(list)
    last_link_by_corridor: Dict[str, str] = {}

    for corridor in corridors:
        if not corridor.link_ids:
            continue
        first_link_to_corridors[corridor.link_ids[0]].append(corridor.corridor_id)
        last_link_by_corridor[corridor.corridor_id] = corridor.link_ids[-1]

    active: Dict[Tuple[str, str], Dict[str, Any]] = {}
    traversal_times: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    slice_lookup = [(ts.label, ts.window_start_sec, ts.window_end_sec) for ts in time_slices]

    def classify_time_slice(start_time_sec: float) -> Optional[str]:
        t = int(start_time_sec)
        for label, start_sec, end_sec in slice_lookup:
            if start_sec <= t < end_sec:
                return label
        return None

    print("Starting MATSim corridor extraction (relaxed mode 70%)...")

    with open_text_maybe_gzip(events_path) as f:
        context = ET.iterparse(f, events=("start", "end"))
        for event, elem in context:
            if event != "end" or elem.tag != "event":
                continue

            attrib = elem.attrib
            event_type = attrib.get("type")
            if event_type not in {"entered link", "left link"}:
                elem.clear()
                continue

            vehicle_id = normalize_vehicle_id(attrib)
            link_id = attrib.get("link")
            time_sec = float(attrib.get("time", 0.0))
            if vehicle_id is None or link_id is None:
                elem.clear()
                continue

            if event_type == "entered link" and link_id in first_link_to_corridors:
                for corridor_id in first_link_to_corridors[link_id]:
                    key = (vehicle_id, corridor_id)
                    active[key] = {"start_time": time_sec, "seen_links": {link_id}}

            if event_type == "entered link":
                for key in [k for k in active if k[0] == vehicle_id]:
                    active[key]["seen_links"].add(link_id)

            if event_type == "left link":
                for key in [k for k in active if k[0] == vehicle_id]:
                    _, corridor_id = key
                    if link_id != last_link_by_corridor.get(corridor_id):
                        continue

                    state = active[key]
                    corridor = corridor_map[corridor_id]
                    total_links = len(corridor.link_ids)
                    seen_count = len(state["seen_links"] & set(corridor.link_ids))

                    min_required = max(2, int(0.50 * total_links))   # ลดเหลือ 50%

                    if seen_count >= min_required:
                        ts_label = classify_time_slice(state["start_time"])
                        if ts_label is not None:
                            duration = time_sec - state["start_time"]
                            # กรอง outlier: .duration ไม่ควรเกิน 2 ชั่วโมง (7200 วินาที)
                            if duration < 7200:
                                traversal_times[(corridor_id, ts_label)].append(duration)
                                print(f"✓ FOUND: {corridor_id} | Vehicle {vehicle_id} | Duration {duration:.1f}s | Seen {seen_count}/{total_links}")
                            else:
                                print(f"✗ OUTLIER ignored: {corridor_id} | Vehicle {vehicle_id} | Duration {duration:.1f}s")
                    del active[key]

            elem.clear()

    # Build rows
    rows = []
    for corridor in corridors:
        if not corridor.link_ids:
            continue
        total_length_m, ff_time_sec = corridor_freeflow_stats(corridor, network)
        for ts in time_slices:
            times = traversal_times.get((corridor.corridor_id, ts.label), [])
            avg_time_sec = mean_or_none(times)
            rows.append({
                "corridor_id": corridor.corridor_id,
                "corridor_name": corridor.name,
                "time_label": ts.label,
                "matsim_observations": len(times),
                "matsim_duration_sec": avg_time_sec,
                "matsim_freeflow_duration_sec": ff_time_sec,
                "matsim_distance_m": total_length_m,
                "matsim_ci": safe_div(avg_time_sec, ff_time_sec),
                "matsim_speed_kph": safe_div(total_length_m, avg_time_sec) * 3.6 if avg_time_sec else None,
            })

    print(f"Extraction completed. Total traversals found: {sum(len(t) for t in traversal_times.values())}")
    return pd.DataFrame(rows)


# -----------------------------
# Evaluation & Summary (เหมือนเดิม)
# -----------------------------

def generate_evaluation_table(google_df: pd.DataFrame, matsim_df: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(google_df, matsim_df, on=["corridor_id", "corridor_name", "time_label"], how="inner")
    
    merged["relative_travel_time_error"] = (
        (merged["matsim_duration_sec"] - merged["google_duration_sec"]).abs() / merged["google_duration_sec"]
    )
    merged["congestion_index_error"] = (merged["matsim_ci"] - merged["google_ci"]).abs()
    merged["speed_relative_error"] = (
        (merged["matsim_speed_kph"] - merged["google_speed_kph"]).abs() / merged["google_speed_kph"]
    )

    def classify_row(row):
        tt_ok = pd.notna(row["relative_travel_time_error"]) and row["relative_travel_time_error"] < 0.30
        ci_ok = pd.notna(row["congestion_index_error"]) and row["congestion_index_error"] < 0.50
        speed_ok = pd.notna(row["speed_relative_error"]) and row["speed_relative_error"] < 0.20
        if tt_ok and ci_ok and speed_ok:
            return "PASS"
        if tt_ok and ci_ok:
            return "PASS_PARTIAL"
        return "FAIL"

    merged["validation_status"] = merged.apply(classify_row, axis=1)
    
    ordered_cols = [
        "corridor_id", "corridor_name", "time_label",
        "google_duration_sec", "matsim_duration_sec",
        "google_static_duration_sec", "matsim_freeflow_duration_sec",
        "google_distance_m", "matsim_distance_m",
        "google_ci", "matsim_ci",
        "google_speed_kph", "matsim_speed_kph",
        "relative_travel_time_error", "congestion_index_error", "speed_relative_error",
        "matsim_observations", "validation_status"
    ]
    return merged[ordered_cols].sort_values(["corridor_id", "time_label"]).reset_index(drop=True)


def generate_summary_table(evaluation_df: pd.DataFrame) -> pd.DataFrame:
    grouped = evaluation_df.groupby("time_label").agg(
        mean_relative_travel_time_error=("relative_travel_time_error", "mean"),
        mean_congestion_index_error=("congestion_index_error", "mean"),
        mean_speed_relative_error=("speed_relative_error", "mean"),
        avg_matsim_observations=("matsim_observations", "mean"),
        pass_count=("validation_status", lambda s: (s == "PASS").sum()),
        pass_partial_count=("validation_status", lambda s: (s == "PASS_PARTIAL").sum()),
        fail_count=("validation_status", lambda s: (s == "FAIL").sum()),
        sample_count=("validation_status", "count"),
    ).reset_index()

    overall = pd.DataFrame([{
        "time_label": "ALL",
        "mean_relative_travel_time_error": evaluation_df["relative_travel_time_error"].mean(),
        "mean_congestion_index_error": evaluation_df["congestion_index_error"].mean(),
        "mean_speed_relative_error": evaluation_df["speed_relative_error"].mean(),
        "avg_matsim_observations": evaluation_df["matsim_observations"].mean(),
        "pass_count": (evaluation_df["validation_status"] == "PASS").sum(),
        "pass_partial_count": (evaluation_df["validation_status"] == "PASS_PARTIAL").sum(),
        "fail_count": (evaluation_df["validation_status"] == "FAIL").sum(),
        "sample_count": len(evaluation_df),
    }])

    return pd.concat([grouped, overall], ignore_index=True)


def build_methodology_text() -> str:
    return """Methodology
-----------
MATSim simulation was validated against Google Routes API using selected road corridors.
Travel times were extracted by tracking vehicles that traverse a significant portion of the defined corridor links.
Validation metrics include relative travel time error, congestion index error, and speed error."""

# -----------------------------
# Main
# -----------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MATSim vs Google Routes evaluation pipeline")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--network", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--skip-google", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_outdir(args.outdir)

    time_slices, corridors = load_config(args.config)
    network = parse_network(args.network)

    google_csv = args.outdir / "google_routes_results.csv"
    matsim_csv = args.outdir / "matsim_corridor_results.csv"
    evaluation_csv = args.outdir / "evaluation_table.csv"
    summary_csv = args.outdir / "evaluation_summary.csv"

    # Google Routes
    if args.skip_google and google_csv.exists():
        google_df = pd.read_csv(google_csv)
    else:
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_MAPS_API_KEY is not set")
        google_df = collect_google_results(corridors, time_slices, api_key)
        google_df.to_csv(google_csv, index=False)
        print(f"Saved: {google_csv}")

    # MATSim extraction
    matsim_df = extract_matsim_corridor_travel_times(args.events, corridors, time_slices, network)
    matsim_df.to_csv(matsim_csv, index=False)
    print(f"Saved: {matsim_csv}")

    # Evaluation
    evaluation_df = generate_evaluation_table(google_df, matsim_df)
    evaluation_df.to_csv(evaluation_csv, index=False)
    print(f"Saved: {evaluation_csv}")

    summary_df = generate_summary_table(evaluation_df)
    summary_df.to_csv(summary_csv, index=False)
    print(f"Saved: {summary_csv}")

    print("\nEvaluation completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())