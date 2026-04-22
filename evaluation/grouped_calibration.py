#!/usr/bin/env python3
"""
Grouped Free-flow Calibration v2 - เร็วและตรงกับ network ปัจจุบันของคุณ
ใช้ link_ids จาก build_paths_from_network.py
"""

import xml.etree.ElementTree as ET
import pandas as pd
import argparse
import json
import gzip
from pathlib import Path
from collections import defaultdict

def get_calib_group(highway: str, area: str = "Inner") -> str:
    h = (highway or "").lower()
    if h in ["motorway", "trunk"]:
        return f"motorway_{area}"
    elif h == "primary":
        return f"primary_{area}"
    elif h == "secondary":
        return f"secondary_{area}"
    elif h == "tertiary":
        return "tertiary_Inner"
    return "other"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", required=True, type=Path, help="network XML")
    parser.add_argument("--config", required=True, type=Path, help="config_corridors_from_network.json")
    parser.add_argument("--eval", required=True, type=Path, help="evaluation_table.csv จากรอบก่อนหน้า")
    parser.add_argument("--output", required=True, type=Path, help="network ใหม่")
    parser.add_argument("--iterations", type=int, default=8)
    args = parser.parse_args()

    # 1. โหลด evaluation (เพื่อเอา google_static_duration_sec)
    eval_df = pd.read_csv(args.eval)
    google_tt_dict = eval_df.groupby('corridor_id')['google_static_duration_sec'].mean().to_dict()

    # 2. โหลด corridors + link_ids
    with open(args.config, encoding='utf-8') as f:
        config_data = json.load(f)
    corridors = {c['corridor_id']: c for c in config_data['corridors']}

    print(f"พบ {len(corridors)} corridors สำหรับ calibration")

    # 3. Grouped Calibration (ปรับ freespeed โดยตรงใน XML)
    tree = ET.parse(args.network)
    root = tree.getroot()

    for iteration in range(args.iterations):
        print(f"\n=== Iteration {iteration+1}/{args.iterations} ===")

        group_adjust = defaultdict(float)
        group_weight = defaultdict(float)

        total_mape = 0.0
        count = 0

        for corr_id, corr in corridors.items():
            link_ids = corr.get("link_ids", [])
            if not link_ids:
                continue

            # คำนวณ sim freeflow time จาก link_ids
            sim_tt = 0.0
            for link_elem in root.iter("link"):
                if link_elem.get("id") in link_ids:
                    length = float(link_elem.get("length", 0))
                    fs = float(link_elem.get("freespeed", 1))
                    sim_tt += length / fs

            google_tt = google_tt_dict.get(corr_id, None)
            if google_tt is None or google_tt <= 0:
                continue

            error = (sim_tt - google_tt) / google_tt   # + = sim เร็วเกิน
            total_mape += abs(error)
            count += 1

            # Accumulate error ต่อกลุ่ม (ใช้ highway จาก link)
            for link_elem in root.iter("link"):
                if link_elem.get("id") in link_ids:
                    hwy = link_elem.get("type") or link_elem.get("highway") or "other"
                    area = "Inner"  # เปลี่ยนเป็น logic จริงภายหลัง
                    grp = get_calib_group(hwy, area)

                    weight = float(link_elem.get("length", 1))
                    group_adjust[grp] += error * weight
                    group_weight[grp] += weight

        # ปรับ multiplier
        print(f"Mean MAPE: {total_mape/count:.4f}" if count > 0 else "No data")

        for grp in group_adjust:
            if group_weight[grp] == 0:
                continue
            avg_error = group_adjust[grp] / group_weight[grp]
            multiplier = max(0.75, min(1.30, 1.0 - 0.25 * avg_error))   # dampen

            print(f"  Group {grp:20} multiplier = {multiplier:.3f}")

            # ปรับ freespeed จริง
            for link_elem in root.iter("link"):
                if link_elem.get("calib_group") == grp or get_calib_group(
                    link_elem.get("type") or link_elem.get("highway"), "Inner") == grp:
                    fs = float(link_elem.get("freespeed"))
                    new_fs = fs * multiplier
                    new_fs = max(8.0, min(35.0, new_fs))   # clamp 28.8 – 126 km/h
                    link_elem.set("freespeed", str(round(new_fs, 4)))

    # 4. เขียน network ใหม่
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(args.output), encoding="utf-8", xml_declaration=True)
    print(f"\nเขียน network ใหม่สำเร็จ: {args.output}")

if __name__ == "__main__":
    main()