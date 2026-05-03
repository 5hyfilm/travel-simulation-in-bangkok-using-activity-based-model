"""
analysis_full.py — Full MATSim Bangkok output analysis for validation improvement.
Run from project root:
  python evaluation/analysis_full.py
"""

import gzip
import math
import os
import sys
import xml.etree.ElementTree as ET

import pandas as pd
import numpy as np

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPS_FILE   = os.path.join(BASE, "output", "output_trips.csv.gz")
CONFIG_FILE  = os.path.join(BASE, "data", "config.xml")
NETWORK_FILE = os.path.join(BASE, "data", "processed", "network.xml.gz")

SEP = "=" * 72

def hms_to_sec(t):
    try:
        h, m, s = str(t).split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 0. Load trips
# ══════════════════════════════════════════════════════════════════════════════
print(SEP)
print("  Loading output_trips.csv.gz …")
print(SEP)
trips_raw = pd.read_csv(TRIPS_FILE, sep=";", low_memory=False)
print(f"  Total rows loaded : {len(trips_raw):,}")
print(f"  Columns           : {list(trips_raw.columns)}")

trips_raw["trav_sec"] = trips_raw["trav_time"].apply(hms_to_sec)
trips_raw["dep_sec"]  = trips_raw["dep_time"].apply(hms_to_sec)
trips_raw["trav_min"] = trips_raw["trav_sec"] / 60
trips_raw["dep_hour"] = trips_raw["dep_sec"] / 3600
trips_raw["dist_km"]  = trips_raw["traveled_distance"] / 1000

# Valid trips (positive time and distance)
trips = trips_raw[
    (trips_raw["trav_sec"] > 0) &
    (trips_raw["dist_km"]  > 0) &
    trips_raw["dep_hour"].between(0, 30, inclusive="both")
].copy()
print(f"  Valid trips       : {len(trips):,}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. Travel time distribution — histogram stats, suspiciously fast/slow trips
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 1 — Travel Time Distribution & Speed Sanity")
print(SEP)

trips["speed_kph"] = trips["dist_km"] / (trips["trav_sec"] / 3600)

total = len(trips)
fast  = (trips["speed_kph"] > 80).sum()
slow  = (trips["speed_kph"] < 5).sum()

print(f"\n  trav_time stats (minutes):")
desc = trips["trav_min"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
for k, v in desc.items():
    print(f"    {k:8s}: {v:8.2f}")

print(f"\n  Implied speed stats (km/h):")
desc2 = trips["speed_kph"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
for k, v in desc2.items():
    print(f"    {k:8s}: {v:8.2f}")

print(f"\n  Suspiciously FAST  (speed > 80 km/h) : {fast:,} trips  ({100*fast/total:.2f}%)")
print(f"  Suspiciously SLOW  (speed <  5 km/h) : {slow:,} trips  ({100*slow/total:.2f}%)")

# Buckets
print(f"\n  Speed distribution buckets:")
for lo, hi in [(0,5),(5,20),(20,50),(50,80),(80,150),(150,999)]:
    n = ((trips["speed_kph"] >= lo) & (trips["speed_kph"] < hi)).sum()
    print(f"    [{lo:3d}-{hi:3d}) km/h : {n:7,}  ({100*n/total:.2f}%)")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Cascade-stuck agents — trav_time > 60 min for trips < 10 km
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 2 — Cascade-Stuck Agents")
print(SEP)

stuck = trips[(trips["trav_min"] > 60) & (trips["dist_km"] < 10)]
print(f"\n  Agents with trav_time > 60 min AND dist < 10 km: {len(stuck):,}")
print(f"  As % of all valid trips                         : {100*len(stuck)/total:.2f}%")

stuck2 = trips[trips["trav_min"] > 90]
print(f"\n  Agents with trav_time > 90 min (any dist)       : {len(stuck2):,}  ({100*len(stuck2)/total:.2f}%)")

very_slow = trips[(trips["trav_min"] > 60) & (trips["speed_kph"] < 5)]
print(f"  Agents with trav_time>60 min AND speed<5 km/h   : {len(very_slow):,}  ({100*len(very_slow)/total:.2f}%)")

print(f"\n  Travel time percentiles for stuck (>60 min, <10 km) group:")
if len(stuck) > 0:
    for p in [50, 75, 90, 95, 99]:
        print(f"    P{p:2d}: {np.percentile(stuck['trav_min'], p):.1f} min")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Mode breakdown
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 3 — Mode Breakdown")
print(SEP)

mode_col = None
for candidate in ["main_mode", "longest_distance_mode", "modes"]:
    if candidate in trips.columns:
        mode_col = candidate
        break

if mode_col:
    mode_counts = trips[mode_col].value_counts()
    print(f"\n  Mode column used: '{mode_col}'")
    print(f"  {'Mode':<30} {'Trips':>10} {'%':>8}  {'Median dist km':>15}  {'Median time min':>16}")
    print(f"  {'-'*30} {'-'*10} {'-'*8}  {'-'*15}  {'-'*16}")
    for mode, cnt in mode_counts.items():
        sub = trips[trips[mode_col] == mode]
        md  = sub["dist_km"].median()
        mt  = sub["trav_min"].median()
        print(f"  {str(mode):<30} {cnt:>10,} {100*cnt/total:>7.1f}%  {md:>15.2f}  {mt:>16.2f}")
else:
    print("  No mode column found. Columns:", list(trips.columns))


# ══════════════════════════════════════════════════════════════════════════════
# 4. Distance vs travel time — implied speeds by distance bucket
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 4 — Distance vs Travel Time: Implied Speeds by Bucket")
print(SEP)

buckets = [(0,5,"0-5 km"),(5,15,"5-15 km"),(15,30,"15-30 km"),(30,200,"30+ km")]
print(f"\n  {'Bucket':<12} {'N':>8}  {'Median spd':>12}  {'Mean spd':>10}  {'P5 spd':>8}  {'P95 spd':>8}  {'Median min':>11}")
print(f"  {'-'*12} {'-'*8}  {'-'*12}  {'-'*10}  {'-'*8}  {'-'*8}  {'-'*11}")
for lo, hi, label in buckets:
    sub = trips[(trips["dist_km"] >= lo) & (trips["dist_km"] < hi)]
    if len(sub) == 0:
        continue
    spds = sub["speed_kph"]
    print(f"  {label:<12} {len(sub):>8,}  {spds.median():>12.1f}  {spds.mean():>10.1f}"
          f"  {np.percentile(spds,5):>8.1f}  {np.percentile(spds,95):>8.1f}  {sub['trav_min'].median():>11.1f}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. Time-of-day pattern — average travel time by departure hour
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 5 — Time-of-Day Pattern")
print(SEP)

trips["dep_hour_int"] = trips["dep_hour"].astype(int)
hourly = trips.groupby("dep_hour_int").agg(
    n=("trav_min", "count"),
    median_min=("trav_min", "median"),
    mean_min=("trav_min", "mean"),
    median_spd=("speed_kph", "median"),
).reset_index()

print(f"\n  {'Hour':>6} {'N trips':>9} {'Median min':>11} {'Mean min':>10} {'Median spd km/h':>16}")
print(f"  {'-'*6} {'-'*9} {'-'*11} {'-'*10} {'-'*16}")
for _, row in hourly[hourly["dep_hour_int"].between(5, 23)].iterrows():
    marker = " ← AM peak" if row["dep_hour_int"] in [7,8] else (
             " ← PM peak" if row["dep_hour_int"] in [17,18] else "")
    print(f"  {row['dep_hour_int']:>6}h {row['n']:>9,} {row['median_min']:>11.1f} "
          f"{row['mean_min']:>10.1f} {row['median_spd']:>16.1f}{marker}")

# Check AM peak vs midday
am = hourly[hourly["dep_hour_int"].isin([7,8])]["median_min"].mean()
md_val = hourly[hourly["dep_hour_int"].isin([11,12])]["median_min"].mean()
pm = hourly[hourly["dep_hour_int"].isin([17,18])]["median_min"].mean()
print(f"\n  AM peak (7-8h) median travel time   : {am:.1f} min")
print(f"  Midday (11-12h) median travel time  : {md_val:.1f} min")
print(f"  PM peak (17-18h) median travel time : {pm:.1f} min")
if am > md_val * 1.05:
    print("  ✅ AM peak IS longer than midday → congestion is captured")
else:
    print("  ❌ AM peak is NOT longer than midday → congestion not captured")
if pm > md_val * 1.05:
    print("  ✅ PM peak IS longer than midday → congestion is captured")
else:
    print("  ❌ PM peak is NOT longer than midday → congestion not captured")


# ══════════════════════════════════════════════════════════════════════════════
# 6. Score breakdown by distance band (proxy without Google Maps)
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 6 — Simulation Travel Time vs Bangkok Reference Benchmarks")
print(SEP)
print("  (Using TomTom/ADB reference speeds since no live API call is made here)")

# Bangkok reference: free-flow ~35-45 km/h inner, ~55-65 km/h outer
# With congestion factor 1.36 (TomTom 2024), peak speeds drop ~26%
# We compare sim speed to expected congested speed
ref_speeds = {
    "0-5 km"   : {"ff": 28.0, "congested": 18.0},  # inner city, heavy signals
    "5-15 km"  : {"ff": 40.0, "congested": 28.0},  # mixed
    "15-30 km" : {"ff": 55.0, "congested": 38.0},  # arterials / expressways
    "30+ km"   : {"ff": 70.0, "congested": 50.0},  # expressway dominant
}

print(f"\n  {'Band':<12} {'N':>8} {'Sim med spd':>12} {'Ref congested':>14} {'Ratio sim/ref':>14} {'Assessment'}")
print(f"  {'-'*12} {'-'*8} {'-'*12} {'-'*14} {'-'*14} {'-'*20}")
for lo, hi, label in buckets:
    sub = trips[(trips["dist_km"] >= lo) & (trips["dist_km"] < hi)]
    if len(sub) == 0:
        continue
    sim_spd = sub["speed_kph"].median()
    ref     = ref_speeds[label]
    ratio   = sim_spd / ref["congested"]
    flag    = "✅ OK" if 0.65 <= ratio <= 1.35 else ("⚠️  too fast" if ratio > 1.35 else "❌ too slow")
    print(f"  {label:<12} {len(sub):>8,} {sim_spd:>12.1f} {ref['congested']:>14.1f} {ratio:>14.2f}x  {flag}")

print()
print("  Reference: TomTom Traffic Index 2024 — Bangkok average congestion +36% vs free-flow")
print("  Reference: ADB Urban Transport Outlook SEA 2023")


# ══════════════════════════════════════════════════════════════════════════════
# 7. flowCapacityFactor sensitivity — effective demand/capacity ratio
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 7 — flowCapacityFactor Sensitivity Analysis")
print(SEP)

try:
    tree = ET.parse(CONFIG_FILE)
    root = tree.getroot()
    params = {}
    for module in root.iter("module"):
        mname = module.get("name", "")
        for param in module.iter("param"):
            key = f"{mname}.{param.get('name','')}"
            params[key] = param.get("value","")

    # Relevant parameters
    flow_factor   = float(params.get("qsim.flowCapacityFactor",
                          params.get("hermes.flowCapacityFactor", "0.10")))
    storage_factor= float(params.get("qsim.storageCapacityFactor",
                          params.get("hermes.storageCapacityFactor", "0.10")))
    sample_size   = float(params.get("qsim.endTime",  # fallback
                          params.get("global.coordinateSystem", "0")))
    last_iter     = params.get("controler.lastIteration", "50")
    stuck_time    = params.get("qsim.stuckTime", params.get("hermes.stuckTime", "600"))

    print(f"\n  Config parameters found:")
    relevant_keys = [k for k in params if any(x in k for x in
                     ["flowCap","storageCap","stuckTime","lastIteration","sampleSize","coordinateSystem","endTime"])]
    for k in sorted(relevant_keys):
        print(f"    {k} = {params[k]}")

    print(f"\n  flowCapacityFactor   : {flow_factor}")
    print(f"  storageCapacityFactor: {storage_factor}")
    print(f"  stuckTime            : {stuck_time} s")
    print(f"  lastIteration        : {last_iter}")

    # Demand/capacity analysis
    # Bangkok population ~10.5M; 300k agents = ~2.86% not 7%
    # but user says 300k @ 7% sample
    pop_sample = 300_000  # agents
    bkk_pop    = 10_500_000
    sample_pct = pop_sample / bkk_pop * 100

    print(f"\n  Agent population analysis:")
    print(f"    Agents in sim       : {pop_sample:,}")
    print(f"    Bangkok metro pop   : {bkk_pop:,}")
    print(f"    Implied sample %    : {sample_pct:.1f}%")

    # Effective demand vs capacity
    # flowCapacityFactor scales road capacity; demand enters at 100% of sample
    # Effective demand/capacity ratio = (sample_pct/100) / flowCapacityFactor
    effective_ratio = (sample_pct / 100) / flow_factor
    print(f"\n  Demand/capacity analysis:")
    print(f"    Effective flow D/C  : {sample_pct/100:.3f} / {flow_factor:.3f} = {effective_ratio:.2f}x")
    if effective_ratio < 0.8:
        rec_ff = sample_pct / 100 / 0.9
        print(f"    → Network is UNDER-loaded (D/C {effective_ratio:.2f} < 0.80)")
        print(f"    → Congestion cannot form → sim speeds too high")
        print(f"    → Recommendation: lower flowCapacityFactor to {rec_ff:.3f} OR")
        print(f"       use a sample-size correction: set flowCapacityFactor = sampleSize")
        print(f"       i.e. if sampleSize=0.07, flowCapacityFactor=0.07 gives D/C=1.0")
    elif effective_ratio > 1.2:
        rec_ff = sample_pct / 100 / 0.9
        print(f"    → Network is OVER-loaded (D/C {effective_ratio:.2f} > 1.20)")
        print(f"    → Too much congestion → sim speeds too low")
        print(f"    → Recommendation: raise flowCapacityFactor to {rec_ff:.3f}")
    else:
        print(f"    → D/C ratio {effective_ratio:.2f} is in a reasonable range (0.80–1.20)")

except Exception as e:
    print(f"  ERROR reading config: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 8. Network freespeed check — sample 200 links
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SECTION 8 — Network Freespeed Distribution (sample of 200 links)")
print(SEP)

try:
    link_speeds = []
    link_capacities = []
    link_lanes = []
    count = 0
    SAMPLE = 200

    # Try output network first (post-simulation), fallback to processed
    net_candidates = [
        os.path.join(BASE, "output", "output_network.xml.gz"),
        NETWORK_FILE,
        os.path.join(BASE, "data", "processed", "network.xml.gz"),
    ]
    net_file = None
    for c in net_candidates:
        if os.path.exists(c):
            net_file = c
            break

    print(f"\n  Using network file: {net_file}")

    if net_file and net_file.endswith(".gz"):
        import gzip as gz
        ctx = gz.open(net_file, "rt", encoding="utf-8")
    elif net_file:
        ctx = open(net_file, "rt", encoding="utf-8")
    else:
        ctx = None

    if ctx is not None:
        # Streaming parse to avoid loading full file into RAM
        for event, elem in ET.iterparse(ctx if not net_file.endswith(".gz") else gz.open(net_file, "rt"), events=["start"]):
            if elem.tag == "link":
                try:
                    fs  = float(elem.get("freespeed", 0))
                    cap = float(elem.get("capacity", 0))
                    lanes = float(elem.get("permlanes", elem.get("numLanes", 1)))
                    if fs > 0:
                        link_speeds.append(fs * 3.6)  # m/s → km/h
                        link_capacities.append(cap)
                        link_lanes.append(lanes)
                        count += 1
                except Exception:
                    pass
                elem.clear()
                if count >= SAMPLE:
                    break

        print(f"\n  Links sampled: {count}")
        if link_speeds:
            speeds = np.array(link_speeds)
            caps   = np.array(link_capacities)
            lanes_arr = np.array(link_lanes)
            print(f"\n  Freespeed distribution (km/h):")
            for p in [5, 25, 50, 75, 90, 95, 99]:
                print(f"    P{p:2d}: {np.percentile(speeds, p):.1f} km/h")
            print(f"    Mean: {speeds.mean():.1f} km/h")
            print(f"    Max : {speeds.max():.1f} km/h")

            # Categorise
            print(f"\n  Speed category distribution:")
            cats = [(0,30,"<30 (urban slow)"),(30,50,"30-50 (urban)"),(50,80,"50-80 (arterial)"),
                    (80,120,"80-120 (expressway)"),(120,999,">120 (UNREALISTIC)")]
            for lo, hi, lbl in cats:
                n = ((speeds >= lo) & (speeds < hi)).sum()
                flag = " ⚠️  CHECK" if lo >= 120 else ""
                print(f"    {lbl:<25}: {n:>4} links  ({100*n/count:.1f}%){flag}")

            print(f"\n  Capacity distribution (veh/h/lane):")
            cap_per_lane = caps / np.maximum(lanes_arr, 1)
            for p in [5, 25, 50, 75, 95]:
                print(f"    P{p:2d}: {np.percentile(cap_per_lane, p):.0f} veh/h/lane")
            if np.percentile(cap_per_lane, 50) > 2200:
                print("  ⚠️  Median capacity > 2200 veh/h/lane — may be too high for Bangkok")
            elif np.percentile(cap_per_lane, 50) < 600:
                print("  ⚠️  Median capacity < 600 veh/h/lane — may be too low")
            else:
                print(f"  ✅ Median capacity {np.percentile(cap_per_lane, 50):.0f} veh/h/lane is plausible")
    else:
        print("  Network file not found.")

except Exception as e:
    import traceback
    print(f"  ERROR reading network: {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY & RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  SUMMARY & QUANTIFIED RECOMMENDATIONS")
print(SEP)
print("""
  Based on the analysis above, the following changes are recommended.
  (Specific numbers will be filled by the findings in each section above.)

  R1. [flowCapacityFactor]
      If D/C ratio < 0.80: reduce flowCapacityFactor so that it equals
      the true sample size (e.g. 0.028 for 300k/10.5M). This ensures roads
      are not over-capacitated relative to demand, allowing congestion to form.

  R2. [stuckTime]
      If > 5% of trips have speed < 5 km/h AND trav_time > 60 min:
      reduce stuckTime from 600 s to 200 s. Stuck agents teleport faster,
      avoiding cascade gridlock on bottleneck links.

  R3. [Network freespeed]
      If > 5% of links have freespeed > 120 km/h: cap link freespeed at
      110 km/h in preprocessing. Unrealistically fast links allow agents
      to race between nodes and suppress realistic congestion.

  R4. [AM/PM peak congestion]
      If AM peak median travel time ≤ midday: the simulation is not
      capturing temporal demand variation. Check whether the activity chains
      produce realistic peak hours, or consider adding time-of-day capacity
      reduction (road pricing / signal timing).

  R5. [Short-distance trips (0-5 km)]
      If 0-5 km trips have median speed > 25 km/h: signal delays and
      intersection controls are not effective. Increase signal cycle times
      or add missing traffic lights at major intersections.

  R6. [Sample size correction]
      The "correct" calibration: flowCapacityFactor = storageCapacityFactor
      = sample_fraction. For 300k agents / 10.5M pop = 0.0286 ≈ 0.03.
      This is the standard MATSim sub-sampling rule (Horni et al. 2016 ch.4).
""")
print(SEP)
print("  Analysis complete.")
print(SEP)
