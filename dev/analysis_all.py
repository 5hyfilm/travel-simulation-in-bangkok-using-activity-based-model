#!/usr/bin/env python3
"""
MATSim Bangkok Simulation Analysis
Runs all 7 analysis sections on normal_output/output/output_trips.csv.gz
"""

import pandas as pd
import numpy as np
import gzip
import xml.etree.ElementTree as ET
import sys
import os

PROJECT = r"C:\CP49\2025_2\CAPSTONE\progess\travel-simulation-in-bangkok-using-activity-based-model"
TRIPS_FILE = os.path.join(PROJECT, "normal_output", "output", "output_trips.csv.gz")
NETWORK_FILE = os.path.join(PROJECT, "data", "processed", "network.xml.gz")
CONFIG_FILE = os.path.join(PROJECT, "data", "config.xml")

print("=" * 70)
print("MATSim Bangkok Simulation Analysis — normal_output")
print("=" * 70)

# ─────────────────────────────────────────────────────────────
# Load trips data
# ─────────────────────────────────────────────────────────────
print("\nLoading trips data...")
df = pd.read_csv(TRIPS_FILE, sep=";", compression="gzip", low_memory=False)
print(f"  Rows loaded: {len(df):,}")
print(f"  Columns: {list(df.columns)}")

# Convert trav_time to seconds
def hms_to_seconds(s):
    """Convert HH:MM:SS string to seconds. Handles >24h times."""
    try:
        parts = str(s).split(":")
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        return np.nan

df["trav_time_sec"] = df["trav_time"].apply(hms_to_seconds)
df["dep_time_sec"] = df["dep_time"].apply(hms_to_seconds)
df["dep_hour"] = (df["dep_time_sec"] // 3600).astype("Int64")

# implied speed km/h
df["implied_speed"] = df["traveled_distance"] / df["trav_time_sec"] * 3.6

# ─────────────────────────────────────────────────────────────
# SECTION 1: Travel time distribution
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 1: Travel Time Distribution")
print("=" * 70)

tt = df["trav_time_sec"].dropna()
print(f"  Median travel time : {tt.median()/60:.1f} min  ({tt.median():.0f} s)")
print(f"  P75 travel time    : {tt.quantile(0.75)/60:.1f} min  ({tt.quantile(0.75):.0f} s)")
print(f"  P95 travel time    : {tt.quantile(0.95)/60:.1f} min  ({tt.quantile(0.95):.0f} s)")
print(f"  Max travel time    : {tt.max()/60:.1f} min  ({tt.max():.0f} s)")

too_fast = df[df["implied_speed"] > 80]
stuck_slow = df[df["implied_speed"] < 5]

print(f"\n  Trips with implied speed > 80 km/h  : {len(too_fast):,}  ({100*len(too_fast)/len(df):.2f}%)")
print(f"  Trips with implied speed < 5 km/h   : {len(stuck_slow):,}  ({100*len(stuck_slow)/len(df):.2f}%)")

if len(too_fast) > 0:
    print(f"    [TOO FAST] Median distance: {too_fast['traveled_distance'].median()/1000:.2f} km, "
          f"median time: {too_fast['trav_time_sec'].median():.0f} s")
    print(f"    Sample modes: {too_fast['main_mode'].value_counts().head(5).to_dict()}")

# ─────────────────────────────────────────────────────────────
# SECTION 2: Cascade-stuck agents
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 2: Cascade-Stuck Agents")
print("=" * 70)

stuck = df[(df["trav_time_sec"] > 3600) & (df["traveled_distance"] < 10000)]
print(f"  Stuck trips (>60 min AND <10 km)    : {len(stuck):,}  ({100*len(stuck)/len(df):.2f}%)")

if len(stuck) > 0:
    st = stuck["trav_time_sec"]
    print(f"  Stuck group median trav_time : {st.median()/60:.1f} min")
    print(f"  Stuck group P90  trav_time   : {st.quantile(0.90)/60:.1f} min")
    print(f"  Stuck group P99  trav_time   : {st.quantile(0.99)/60:.1f} min")
    print(f"  Stuck group max  trav_time   : {st.max()/3600:.2f} h  ({st.max():.0f} s)")
    print(f"  Mode breakdown in stuck group:")
    for mode, cnt in stuck["main_mode"].value_counts().items():
        print(f"    {mode}: {cnt:,}  ({100*cnt/len(stuck):.1f}%)")

# ─────────────────────────────────────────────────────────────
# SECTION 3: Mode breakdown
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 3: Mode Breakdown")
print("=" * 70)

mode_counts = df["main_mode"].value_counts()
for mode, cnt in mode_counts.items():
    print(f"  {mode:<20s}: {cnt:>8,}  ({100*cnt/len(df):.2f}%)")

# ─────────────────────────────────────────────────────────────
# SECTION 4: Implied speed by distance bucket
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 4: Implied Speed by Distance Bucket")
print("=" * 70)

reference = {
    "0-5km":   18,
    "5-15km":  28,
    "15-30km": 38,
    "30+km":   50,
}

bins = [0, 5000, 15000, 30000, float("inf")]
labels = ["0-5km", "5-15km", "15-30km", "30+km"]
df["dist_bucket"] = pd.cut(df["traveled_distance"], bins=bins, labels=labels)

bucket_stats = df.groupby("dist_bucket", observed=True).agg(
    count=("implied_speed", "count"),
    med_speed=("implied_speed", "median"),
    med_time_min=("trav_time_sec", lambda x: x.median() / 60),
).reset_index()

print(f"  {'Bucket':<12} {'Count':>8} {'Median Speed (km/h)':>20} {'Ref Speed':>12} {'Diff':>8} {'Median Time (min)':>18}")
print("  " + "-" * 82)
for _, row in bucket_stats.iterrows():
    ref = reference[row["dist_bucket"]]
    diff = row["med_speed"] - ref
    flag = "<<< SLOW" if diff < -5 else (">>> FAST" if diff > 10 else "OK")
    print(f"  {str(row['dist_bucket']):<12} {int(row['count']):>8,} {row['med_speed']:>20.1f} {ref:>12} {diff:>+8.1f} {row['med_time_min']:>18.1f}  {flag}")

# ─────────────────────────────────────────────────────────────
# SECTION 5: Time-of-day congestion
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 5: Time-of-Day Congestion")
print("=" * 70)

hourly = df.groupby("dep_hour", observed=True).agg(
    count=("trav_time_sec", "count"),
    mean_time_min=("trav_time_sec", lambda x: x.mean() / 60),
    median_time_min=("trav_time_sec", lambda x: x.median() / 60),
).reset_index()

print(f"  {'Hour':>6} {'Trips':>8} {'Mean (min)':>12} {'Median (min)':>14}")
print("  " + "-" * 44)
for _, row in hourly.iterrows():
    hour = int(row["dep_hour"])
    flag = ""
    if 7 <= hour <= 9:
        flag = " [AM PEAK]"
    elif 11 <= hour <= 13:
        flag = " [MIDDAY]"
    print(f"  {hour:>6} {int(row['count']):>8,} {row['mean_time_min']:>12.1f} {row['median_time_min']:>14.1f}{flag}")

# AM peak vs midday comparison
am_peak = df[df["dep_hour"].isin([7, 8, 9])]["trav_time_sec"].mean() / 60
midday  = df[df["dep_hour"].isin([11, 12, 13])]["trav_time_sec"].mean() / 60
print(f"\n  AM peak (7-9h) mean travel time : {am_peak:.2f} min")
print(f"  Midday (11-13h) mean travel time: {midday:.2f} min")
if am_peak > midday:
    print(f"  -> AM peak is {am_peak - midday:.2f} min LONGER than midday (congestion signal PRESENT)")
else:
    print(f"  -> Midday is {midday - am_peak:.2f} min longer than AM peak (no classic AM peak signal)")

# ─────────────────────────────────────────────────────────────
# SECTION 6: Network freespeed check
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 6: Network Freespeed Check")
print("=" * 70)

print("  Parsing network.xml.gz (iterative, sampling 2000 links)...")
freespeeds = []
link_count = 0
sample_every = None  # determined after first pass count or streaming sample

try:
    with gzip.open(NETWORK_FILE, "rb") as f:
        # stream parse for memory efficiency
        context = ET.iterparse(f, events=("start",))
        for event, elem in context:
            if elem.tag == "link":
                link_count += 1
                fs = elem.get("freespeed")
                if fs is not None:
                    freespeeds.append(float(fs))
                elem.clear()

    print(f"  Total links in network: {link_count:,}")
    print(f"  Links with freespeed attr: {len(freespeeds):,}")

    # Sample 2000 if more available
    if len(freespeeds) > 2000:
        rng = np.random.default_rng(42)
        sample = rng.choice(freespeeds, size=2000, replace=False)
    else:
        sample = np.array(freespeeds)

    # Convert m/s -> km/h
    sample_kmh = sample * 3.6

    percs = [5, 25, 50, 75, 90, 95, 99]
    print(f"\n  Freespeed distribution (km/h) — sample of {len(sample_kmh):,} links:")
    for p in percs:
        print(f"    P{p:>2}: {np.percentile(sample_kmh, p):.1f} km/h")
    print(f"    Max : {sample_kmh.max():.1f} km/h")

    # Breakdown
    all_kmh = np.array(freespeeds) * 3.6
    under30  = np.sum(all_kmh < 30)
    b30_60   = np.sum((all_kmh >= 30) & (all_kmh < 60))
    b60_90   = np.sum((all_kmh >= 60) & (all_kmh < 90))
    over90   = np.sum(all_kmh >= 90)
    total_fs = len(all_kmh)

    print(f"\n  Freespeed breakdown (all {total_fs:,} links):")
    print(f"    < 30 km/h   : {under30:>7,}  ({100*under30/total_fs:.1f}%)")
    print(f"    30–60 km/h  : {b30_60:>7,}  ({100*b30_60/total_fs:.1f}%)")
    print(f"    60–90 km/h  : {b60_90:>7,}  ({100*b60_90/total_fs:.1f}%)")
    print(f"    90+ km/h    : {over90:>7,}  ({100*over90/total_fs:.1f}%)")

except Exception as e:
    print(f"  ERROR parsing network: {e}")

# ─────────────────────────────────────────────────────────────
# SECTION 7: Config parameters
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 7: flowCapacityFactor Check")
print("=" * 70)

try:
    tree = ET.parse(CONFIG_FILE)
    root = tree.getroot()

    params_of_interest = {
        "flowCapacityFactor": None,
        "storageCapacityFactor": None,
        "stuckTime": None,
        "lastIteration": None,
    }

    # MATSim config XML: <module name="qsim"><param name="..." value="..."/>
    for module in root.iter("module"):
        for param in module.iter("param"):
            name = param.get("name")
            if name in params_of_interest:
                params_of_interest[name] = param.get("value")

    # Also check parameterset structure
    for ps in root.iter("parameterset"):
        for param in ps.iter("param"):
            name = param.get("name")
            if name in params_of_interest:
                params_of_interest[name] = param.get("value")

    for k, v in params_of_interest.items():
        print(f"  {k:<25}: {v}")

    fcf = float(params_of_interest.get("flowCapacityFactor") or 1.0)
    agents = 300_000
    network_cap = 10_500_000  # veh/h assumed
    raw_dc = agents / network_cap
    eff_dc = raw_dc / fcf
    print(f"\n  Agents in simulation  : {agents:,}")
    print(f"  Assumed network cap   : {network_cap:,} veh/h")
    print(f"  Raw D/C ratio         : {raw_dc:.4f}  ({100*raw_dc:.2f}%)")
    print(f"  Effective D/C ratio   : {eff_dc:.4f}  ({100*eff_dc:.2f}%)")
    if eff_dc > 0.15:
        print(f"  WARNING: Effective D/C > 15% — network likely undersized or flowCapacityFactor too low")
    else:
        print(f"  OK: Effective D/C is within reasonable bounds")

except Exception as e:
    print(f"  ERROR reading config: {e}")

print("\n" + "=" * 70)
print("Analysis complete.")
print("=" * 70)
