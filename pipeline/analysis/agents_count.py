"""
count_agents.py — ตรวจสอบจำนวน agent และสถิติใน MATSim population/plan XML
Usage:
    & C:\CP49\2025_2\CAPSTONE\progess\progess\.venv\Scripts\python.exe count_agents.py <plan_file.xml>
    & C:\CP49\2025_2\CAPSTONE\progess\progess\.venv\Scripts\python.exe count_agents.py <plan_file.xml> --detail
"""

import sys
import os
import argparse
from collections import Counter
from lxml import etree


def count_agents(plan_file: str, detail: bool = False):
    print(f"\n{'='*55}")
    print(f"  MATSim Plan Inspector")
    print(f"{'='*55}")
    print(f"  File : {os.path.basename(plan_file)}")
    print(f"  Size : {os.path.getsize(plan_file) / 1_000_000:.1f} MB")
    print(f"{'='*55}\n")

    # ── parse ──────────────────────────────────────────────────────────────
    print("Parsing XML...", end=" ", flush=True)

    # รองรับทั้ง .xml และ .xml.gz
    if plan_file.endswith(".gz"):
        import gzip
        with gzip.open(plan_file, "rb") as f:
            tree = etree.parse(f)
    else:
        tree = etree.parse(plan_file)

    root = tree.getroot()
    print("done.\n")

    # ── count persons ──────────────────────────────────────────────────────
    persons = root.findall(".//person")
    n_persons = len(persons)

    # ── per-person stats ───────────────────────────────────────────────────
    plans_per_person   = []   # จำนวน plan ต่อคน
    acts_per_person    = []   # จำนวน activity ต่อคน (จาก selected plan)
    legs_per_person    = []   # จำนวน leg ต่อคน
    activity_types     = Counter()
    modes              = Counter()
    no_plan_persons    = []
    multi_plan_persons = []
    no_home_end        = []   # plan ที่ไม่จบด้วย home

    for person in persons:
        pid   = person.get("id", "?")
        plans = person.findall("plan")
        plans_per_person.append(len(plans))

        if len(plans) == 0:
            no_plan_persons.append(pid)
            continue
        if len(plans) > 1:
            multi_plan_persons.append(pid)

        # เลือก selected plan (หรืออันแรกถ้าไม่มี selected)
        selected = next(
            (p for p in plans if p.get("selected", "no") == "yes"),
            plans[0]
        )

        acts = selected.findall("activity")
        legs = selected.findall("leg")
        acts_per_person.append(len(acts))
        legs_per_person.append(len(legs))

        for act in acts:
            activity_types[act.get("type", "unknown")] += 1

        for leg in legs:
            modes[leg.get("mode", "unknown")] += 1

        # ตรวจสอบว่า plan จบด้วย home หรือไม่
        if acts:
            last_type = acts[-1].get("type", "")
            if last_type != "home":
                no_home_end.append((pid, last_type))

    # ── summary ───────────────────────────────────────────────────────────
    print(f"┌─ Agent Summary {'─'*38}┐")
    print(f"│  Total persons          : {n_persons:>10,}            │")
    print(f"│  Persons with no plan   : {len(no_plan_persons):>10,}            │")
    print(f"│  Persons with >1 plan   : {len(multi_plan_persons):>10,}            │")
    print(f"│  Plans NOT ending home  : {len(no_home_end):>10,}            │")
    print(f"└{'─'*53}┘\n")

    # plans per person
    if plans_per_person:
        avg_plans = sum(plans_per_person) / len(plans_per_person)
        max_plans = max(plans_per_person)
        print(f"Plans per person   : avg={avg_plans:.2f}  max={max_plans}")

    # activities per person
    if acts_per_person:
        avg_acts = sum(acts_per_person) / len(acts_per_person)
        min_acts = min(acts_per_person)
        max_acts = max(acts_per_person)
        print(f"Acts per person    : avg={avg_acts:.1f}  min={min_acts}  max={max_acts}")

    # legs per person
    if legs_per_person:
        avg_legs = sum(legs_per_person) / len(legs_per_person)
        print(f"Legs per person    : avg={avg_legs:.1f}")

    # activity types
    print(f"\n── Activity Types {'─'*36}")
    total_acts = sum(activity_types.values())
    for atype, count in activity_types.most_common():
        bar = "█" * int(count / total_acts * 30)
        print(f"  {atype:<16} {count:>8,}  {bar}")

    # modes
    print(f"\n── Travel Modes {'─'*38}")
    total_legs = sum(modes.values())
    for mode, count in modes.most_common():
        pct = count / total_legs * 100 if total_legs else 0
        print(f"  {mode:<16} {count:>8,}  ({pct:.1f}%)")

    # ── nighttime congestion warning ───────────────────────────────────────
    if no_home_end:
        print(f"\n⚠️  WARNING: {len(no_home_end):,} agents ไม่จบ plan ด้วย 'home'")
        print("   → อาจทำให้เกิด nighttime congestion ใน MATSim")
        if detail:
            print(f"\n   {'Person ID':<20} {'Last Activity'}")
            print(f"   {'─'*40}")
            for pid, last in no_home_end[:50]:
                print(f"   {pid:<20} {last}")
            if len(no_home_end) > 50:
                print(f"   ... และอีก {len(no_home_end)-50:,} คน")

    if no_plan_persons and detail:
        print(f"\n⚠️  Persons with no plan ({len(no_plan_persons):,}):")
        for pid in no_plan_persons[:20]:
            print(f"   {pid}")

    print(f"\n{'='*55}\n")


def main():
    parser = argparse.ArgumentParser(description="Count agents in MATSim plan XML")
    parser.add_argument("plan_file", help="Path to plan XML or XML.gz file")
    parser.add_argument("--detail", action="store_true",
                        help="Show detailed list of problematic agents")
    args = parser.parse_args()

    if not os.path.exists(args.plan_file):
        print(f"ERROR: ไม่พบไฟล์ {args.plan_file}")
        sys.exit(1)

    count_agents(args.plan_file, detail=args.detail)


if __name__ == "__main__":
    main()