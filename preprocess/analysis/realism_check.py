"""
realism_check.py
================
Compare simulation output against real-world Bangkok benchmarks to assess
how realistic the MATSim activity-based model is.

Real-world reference data sources:
  - TomTom Traffic Index 2023 (Bangkok congestion levels & speeds)
  - BMTA / BMA traffic survey data (peak hours, trip distances)
  - Google/Waze average speed data for Bangkok arterials
  - Thailand NESDC household travel survey (avg trip length ~11-14 km for car)

Reads:
  output/output_legs.csv.gz
  output/output_trips.csv.gz

Run from project root:
  python preprocess/analysis/realism_check.py
"""

import pandas as pd
import math

LEGS_FILE  = "output/output_legs.csv.gz"
TRIPS_FILE = "output/output_trips.csv.gz"

# ── Load ───────────────────────────────────────────────────────────────────
print("Loading simulation outputs...", flush=True)
legs  = pd.read_csv(LEGS_FILE,  sep=";", low_memory=False)
trips = pd.read_csv(TRIPS_FILE, sep=";", low_memory=False)

# ── Time helpers ───────────────────────────────────────────────────────────
def hms_to_sec(t):
    try:
        parts = str(t).split(":")
        return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
    except:
        return None

legs["dep_sec"]   = legs["dep_time"].apply(hms_to_sec)
legs["trav_sec"]  = legs["trav_time"].apply(hms_to_sec)
legs["dep_hour"]  = legs["dep_sec"] / 3600

trips["dep_sec"]  = trips["dep_time"].apply(hms_to_sec)
trips["trav_sec"] = trips["trav_time"].apply(hms_to_sec)
trips["dep_hour"] = trips["dep_sec"] / 3600

# Filter to valid simulation-day trips only (depart before midnight)
legs_day  = legs[legs["dep_hour"] < 24].copy()
trips_day = trips[trips["dep_hour"] < 24].copy()

legs_day["dist_km"]  = legs_day["distance"] / 1000
legs_day["speed_kph"] = legs_day["dist_km"] / (legs_day["trav_sec"] / 3600).replace(0, float("nan"))

trips_day["dist_km"]  = trips_day["traveled_distance"] / 1000
trips_day["speed_kph"] = trips_day["dist_km"] / (trips_day["trav_sec"] / 3600).replace(0, float("nan"))

# ── HEADER ─────────────────────────────────────────────────────────────────
W = 70
print("=" * W)
print("  Realism Check — MATSim Bangkok Simulation vs Real World")
print("=" * W)
print(f"  Agents simulated : {legs_day['person'].nunique():>10,}")
print(f"  Car legs (< 24h) : {len(legs_day):>10,}")
print(f"  Car trips (< 24h): {len(trips_day):>10,}")
print()

# ══════════════════════════════════════════════════════════════════════════
# 1. TRIP DISTANCE
# ══════════════════════════════════════════════════════════════════════════
print("─" * W)
print("  1. TRIP DISTANCE")
print("─" * W)

sim_dist_mean   = trips_day["dist_km"].mean()
sim_dist_median = trips_day["dist_km"].median()
sim_dist_p75    = trips_day["dist_km"].quantile(0.75)
sim_dist_p95    = trips_day["dist_km"].quantile(0.95)

# Real-world: Thailand NESDC Household Travel Survey & Bangkok Metropolitan
# Administration traffic studies put average car trip at 11–14 km.
# TomTom / INRIX for Bangkok: average trip length ~12 km.
REAL_DIST_MEAN   = 12.0   # km  (survey estimate)
REAL_DIST_MEDIAN = 8.5    # km  (right-skewed: many short trips)

print(f"  {'Metric':<30} {'Simulated':>12} {'Real-world':>12} {'Match?':>8}")
print(f"  {'─'*30} {'─'*12} {'─'*12} {'─'*8}")
def match(sim, real, tol=0.25):
    return "✅" if abs(sim - real) / real <= tol else "⚠️ "

print(f"  {'Mean trip distance':<30} {sim_dist_mean:>11.1f}km {REAL_DIST_MEAN:>11.1f}km {match(sim_dist_mean, REAL_DIST_MEAN):>8}")
print(f"  {'Median trip distance':<30} {sim_dist_median:>11.1f}km {REAL_DIST_MEDIAN:>11.1f}km {match(sim_dist_median, REAL_DIST_MEDIAN):>8}")
print(f"  {'75th pct trip distance':<30} {sim_dist_p75:>11.1f}km {'~15 km':>12} {'':>8}")
print(f"  {'95th pct trip distance':<30} {sim_dist_p95:>11.1f}km {'~30 km':>12} {'':>8}")

# Distance histogram
bins = [0,2,5,10,15,20,30,50,999]
labels = ["0–2","2–5","5–10","10–15","15–20","20–30","30–50","50+"]
trips_day["dist_bin"] = pd.cut(trips_day["dist_km"], bins=bins, labels=labels)
dist_hist = trips_day["dist_bin"].value_counts(normalize=True).sort_index() * 100
print()
print(f"  Trip distance distribution:")
for label, pct in dist_hist.items():
    bar = "█" * int(pct / 1.5)
    print(f"    {label:>6} km : {pct:5.1f}%  {bar}")

# ══════════════════════════════════════════════════════════════════════════
# 2. DEPARTURE TIME DISTRIBUTION (PEAK HOURS)
# ══════════════════════════════════════════════════════════════════════════
print()
print("─" * W)
print("  2. DEPARTURE TIME DISTRIBUTION — does the model reproduce Bangkok peaks?")
print("─" * W)

# Real-world Bangkok: AM peak 7–9 AM, PM peak 17–19 (5–7 PM)
# BMA traffic count data shows ~18–22% of daily car trips in AM peak (7–9)
# and ~20–25% in PM peak (17–19).
REAL_AM_PCT = 20.0   # % of daily trips departing 7:00–9:00
REAL_PM_PCT = 22.0   # % of daily trips departing 17:00–19:00

hour_counts = trips_day["dep_hour"].apply(math.floor).value_counts().sort_index()
total_trips = len(trips_day)

sim_am_pct = trips_day[(trips_day["dep_hour"] >= 7) & (trips_day["dep_hour"] < 9)].shape[0] / total_trips * 100
sim_pm_pct = trips_day[(trips_day["dep_hour"] >= 17) & (trips_day["dep_hour"] < 19)].shape[0] / total_trips * 100

print(f"  {'Peak window':<25} {'Simulated':>12} {'Real-world':>12} {'Match?':>8}")
print(f"  {'─'*25} {'─'*12} {'─'*12} {'─'*8}")
print(f"  {'AM peak (07:00–09:00)':<25} {sim_am_pct:>11.1f}% {REAL_AM_PCT:>11.1f}% {match(sim_am_pct, REAL_AM_PCT):>8}")
print(f"  {'PM peak (17:00–19:00)':<25} {sim_pm_pct:>11.1f}% {REAL_PM_PCT:>11.1f}% {match(sim_pm_pct, REAL_PM_PCT):>8}")

print()
print("  Hourly departure profile (% of daily trips):")
for hour in range(5, 23):
    cnt = hour_counts.get(hour, 0)
    pct = cnt / total_trips * 100
    bar = "█" * int(pct / 0.4)
    peak = "← AM peak" if hour in (7, 8) else ("← PM peak" if hour in (17, 18) else "")
    print(f"    {hour:02d}:00  {pct:5.1f}%  {bar} {peak}")

# ══════════════════════════════════════════════════════════════════════════
# 3. TRAVEL TIME
# ══════════════════════════════════════════════════════════════════════════
print()
print("─" * W)
print("  3. TRAVEL TIME")
print("─" * W)

sim_tt_mean   = trips_day["trav_sec"].mean() / 60
sim_tt_median = trips_day["trav_sec"].median() / 60

# Real-world: TomTom Traffic Index 2023 Bangkok
# Average commute (one-way) ~45–55 min in peak, ~25–30 min off-peak
# NESDC survey: average car trip duration ~35 min
REAL_TT_MEAN   = 35.0   # minutes (survey average across all trips)
REAL_TT_MEDIAN = 25.0   # minutes

print(f"  {'Metric':<30} {'Simulated':>12} {'Real-world':>12} {'Match?':>8}")
print(f"  {'─'*30} {'─'*12} {'─'*12} {'─'*8}")
print(f"  {'Mean travel time':<30} {sim_tt_mean:>10.1f}min {REAL_TT_MEAN:>10.1f}min {match(sim_tt_mean, REAL_TT_MEAN):>8}")
print(f"  {'Median travel time':<30} {sim_tt_median:>10.1f}min {REAL_TT_MEDIAN:>10.1f}min {match(sim_tt_median, REAL_TT_MEDIAN):>8}")

# Travel time by peak / off-peak
am   = trips_day[(trips_day["dep_hour"] >= 7)  & (trips_day["dep_hour"] < 9)]["trav_sec"].mean() / 60
pm   = trips_day[(trips_day["dep_hour"] >= 17) & (trips_day["dep_hour"] < 19)]["trav_sec"].mean() / 60
offp = trips_day[(trips_day["dep_hour"] >= 10) & (trips_day["dep_hour"] < 16)]["trav_sec"].mean() / 60

print()
print(f"  By time of day (simulated):")
print(f"    AM peak  (07–09) : {am:.1f} min   [real ~45–55 min]  {'✅' if 35 <= am <= 65 else '⚠️ '}")
print(f"    Midday   (10–16) : {offp:.1f} min   [real ~25–35 min]  {'✅' if 20 <= offp <= 40 else '⚠️ '}")
print(f"    PM peak  (17–19) : {pm:.1f} min   [real ~45–60 min]  {'✅' if 35 <= pm <= 70 else '⚠️ '}")

# ══════════════════════════════════════════════════════════════════════════
# 4. AVERAGE SPEED
# ══════════════════════════════════════════════════════════════════════════
print()
print("─" * W)
print("  4. AVERAGE TRAVEL SPEED")
print("─" * W)

# Remove outliers (teleported/stuck agents with unrealistic speed)
spd = legs_day["speed_kph"].dropna()
spd = spd[(spd > 0) & (spd < 150)]

sim_spd_mean   = spd.mean()
sim_spd_median = spd.median()

# Real-world Bangkok:
# TomTom 2023: Bangkok average speed ~26 km/h (all-day, all roads)
# Peak hour average ~18–22 km/h on arterials
# Off-peak ~35–45 km/h
# Motorway cruising ~80–100 km/h (free-flow)
REAL_SPD_MEAN   = 26.0   # km/h (TomTom all-day average)
REAL_SPD_MEDIAN = 22.0   # km/h

print(f"  {'Metric':<30} {'Simulated':>12} {'Real-world':>12} {'Match?':>8}")
print(f"  {'─'*30} {'─'*12} {'─'*12} {'─'*8}")
print(f"  {'Mean speed (all legs)':<30} {sim_spd_mean:>10.1f}kph {REAL_SPD_MEAN:>10.1f}kph {match(sim_spd_mean, REAL_SPD_MEAN):>8}")
print(f"  {'Median speed':<30} {sim_spd_median:>10.1f}kph {REAL_SPD_MEDIAN:>10.1f}kph {match(sim_spd_median, REAL_SPD_MEDIAN):>8}")

# Speed by time of day
print()
print("  Average speed by hour (simulated vs Bangkok expectation):")
print(f"  {'Hour':<8} {'Sim speed':>10} {'Expected':>10} {'Match?':>8}")
print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*8}")

real_speed_by_hour = {
    5: 55, 6: 40, 7: 22, 8: 18, 9: 25, 10: 35, 11: 38, 12: 35,
    13: 38, 14: 40, 15: 35, 16: 28, 17: 20, 18: 18, 19: 22,
    20: 30, 21: 40, 22: 50,
}
for hour in range(5, 23):
    mask = (legs_day["dep_hour"] >= hour) & (legs_day["dep_hour"] < hour + 1)
    s = legs_day[mask]["speed_kph"].dropna()
    s = s[(s > 0) & (s < 150)]
    if len(s) < 10:
        continue
    sim_s  = s.mean()
    real_s = real_speed_by_hour.get(hour, 30)
    ok = "✅" if abs(sim_s - real_s) / real_s <= 0.35 else "⚠️ "
    bar = "█" * int(sim_s / 3)
    print(f"  {hour:02d}:00   {sim_s:>8.1f}kph {real_s:>8}kph {ok:>8}  {bar}")

# ══════════════════════════════════════════════════════════════════════════
# 5. CONGESTION PATTERN — which hours are most congested?
# ══════════════════════════════════════════════════════════════════════════
print()
print("─" * W)
print("  5. CONGESTION PATTERN — volume by hour")
print("─" * W)
print("  (Real Bangkok: highest volumes 7–9 AM and 17–19 PM)")
print()

print(f"  {'Hour':<8} {'Trips':>8} {'%Daily':>8} {'Bar'}")
print(f"  {'─'*8} {'─'*8} {'─'*8}")
for hour in range(5, 23):
    mask = (trips_day["dep_hour"] >= hour) & (trips_day["dep_hour"] < hour + 1)
    cnt = mask.sum()
    pct = cnt / total_trips * 100
    bar = "█" * int(pct / 0.35)
    pk = " ◀ AM peak" if hour in (7,8) else (" ◀ PM peak" if hour in (17,18) else "")
    print(f"  {hour:02d}:00   {cnt:>8,} {pct:>7.1f}%  {bar}{pk}")

# ══════════════════════════════════════════════════════════════════════════
# 6. SUMMARY SCORECARD
# ══════════════════════════════════════════════════════════════════════════
print()
print("=" * W)
print("  REALISM SCORECARD")
print("=" * W)
checks = [
    ("Trip distance (mean)",      sim_dist_mean,   REAL_DIST_MEAN,   "km",  0.25),
    ("Trip distance (median)",    sim_dist_median, REAL_DIST_MEDIAN, "km",  0.25),
    ("AM peak share",             sim_am_pct,      REAL_AM_PCT,      "%",   0.30),
    ("PM peak share",             sim_pm_pct,      REAL_PM_PCT,      "%",   0.30),
    ("Mean travel time",          sim_tt_mean,     REAL_TT_MEAN,     "min", 0.30),
    ("Mean speed",                sim_spd_mean,    REAL_SPD_MEAN,    "kph", 0.35),
]
passed = 0
for label, sim, real, unit, tol in checks:
    ok = abs(sim - real) / real <= tol
    passed += ok
    status = "✅ PASS" if ok else "⚠️  FAIL"
    print(f"  {status}  {label:<28} sim={sim:.1f}{unit}  ref={real:.1f}{unit}")

print()
print(f"  Score: {passed}/{len(checks)} metrics within tolerance")
if passed >= 5:
    print("  ✅ Simulation is REALISTIC — outputs align with Bangkok real-world data")
elif passed >= 3:
    print("  ⚠️  Simulation is PARTIALLY REALISTIC — most metrics align, some deviate")
else:
    print("  ❌ Simulation needs calibration — significant deviations from real world")
print("=" * W)
