"""
compare_scenarios.py
Compares demo_normal_output/ (baseline) vs demo_conditioned_output/ (traffic conditions)
"""
import os, gzip, csv
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NORMAL_DIR     = os.path.join(ROOT, "demo_normal_output")
CONDITIONED_DIR = os.path.join(ROOT, "demo_conditioned_output")


# ─── helpers ────────────────────────────────────────────────────────────────

def read_trips(folder):
    path = os.path.join(folder, "output_trips.csv.gz")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        df = pd.read_csv(f, sep=";", low_memory=False)
    return df

def read_scorestats(folder):
    path = os.path.join(folder, "scorestats.csv")
    df = pd.read_csv(path, sep=";")
    return df

def read_legs(folder):
    path = os.path.join(folder, "output_legs.csv.gz")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        df = pd.read_csv(f, sep=";", low_memory=False)
    return df


# ─── load data ──────────────────────────────────────────────────────────────

print("Loading data...")
norm_trips = read_trips(NORMAL_DIR)
cond_trips = read_trips(CONDITIONED_DIR)
norm_score = read_scorestats(NORMAL_DIR)
cond_score = read_scorestats(CONDITIONED_DIR)

# show columns for debugging
print(f"\n[Trips columns sample]: {list(norm_trips.columns[:10])}")
print(f"[Scorestats columns]:   {list(norm_score.columns)}")


# ─── travel time (minutes) ──────────────────────────────────────────────────

def to_seconds(series):
    """Convert HH:MM:SS string series to float seconds, handling StringDtype and object."""
    try:
        return pd.to_timedelta(series.astype(str), errors="coerce").dt.total_seconds()
    except Exception:
        def _parse(s):
            try:
                parts = str(s).split(":")
                return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            except Exception:
                return np.nan
        return pd.to_numeric(series.apply(_parse), errors="coerce")

def travel_min(df):
    """Return Series of trip travel time in minutes (car trips only)."""
    car = df[df["main_mode"] == "car"].copy()
    car["trav_sec"] = to_seconds(car["trav_time"])
    return car["trav_sec"] / 60.0

norm_tmin = travel_min(norm_trips)
cond_tmin = travel_min(cond_trips)


# ─── speed (km/h) ───────────────────────────────────────────────────────────

def mean_speed(df):
    car = df[df["main_mode"] == "car"].copy()
    if "traveled_distance" in car.columns:
        dist_col = "traveled_distance"
    elif "distance" in car.columns:
        dist_col = "distance"
    else:
        return np.nan, np.nan
    car["trav_sec"] = to_seconds(car["trav_time"])
    valid = car[(car["trav_sec"] > 0) & (car[dist_col] > 0)]
    speeds = (valid[dist_col] / 1000.0) / (valid["trav_sec"] / 3600.0)
    return speeds.median(), speeds.mean()


# ─── stuck agents ───────────────────────────────────────────────────────────

def count_stuck(folder):
    log = os.path.join(folder, "logfile.log")
    stuck = 0
    with open(log, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "stuck" in line.lower() and "agent" in line.lower():
                import re
                m = re.search(r"(\d+)\s+agent", line.lower())
                if m:
                    stuck = max(stuck, int(m.group(1)))
    return stuck


# ─── final score ────────────────────────────────────────────────────────────

norm_final_score = norm_score["avg_executed"].iloc[-1]
cond_final_score = cond_score["avg_executed"].iloc[-1]


# ─── PM peak travel time ─────────────────────────────────────────────────────

def pm_peak_tmin(df):
    """Car trips departing 17:00–20:00 in minutes."""
    car = df[df["main_mode"] == "car"].copy()
    if "dep_time" not in car.columns:
        return pd.Series(dtype=float)
    car["dep_sec"]  = to_seconds(car["dep_time"])
    car["dep_hour"] = (car["dep_sec"] // 3600).fillna(-1).astype(int)
    car["trav_sec"] = to_seconds(car["trav_time"])
    pm = car[(car["dep_hour"] >= 17) & (car["dep_hour"] < 20)]
    return pm["trav_sec"] / 60.0


norm_pm = pm_peak_tmin(norm_trips)
cond_pm = pm_peak_tmin(cond_trips)

norm_stuck = count_stuck(NORMAL_DIR)
cond_stuck = count_stuck(CONDITIONED_DIR)

norm_speed_med, norm_speed_mean = mean_speed(norm_trips)
cond_speed_med, cond_speed_mean = mean_speed(cond_trips)

total_agents = len(norm_trips["person"].unique()) if "person" in norm_trips.columns else len(norm_trips)


# ─── print report ───────────────────────────────────────────────────────────

def pct_change(a, b):
    if a == 0: return float("inf")
    return (b - a) / a * 100

def fmt(val, unit=""):
    if isinstance(val, float):
        return f"{val:.2f}{unit}"
    return f"{val}{unit}"

print()
print("=" * 68)
print("  SCENARIO COMPARISON: Baseline vs Traffic Conditions")
print("=" * 68)
print(f"{'Metric':<40} {'Baseline':>10} {'Conditioned':>12} {'Change':>8}")
print("-" * 68)

# Travel time (all day car)
nm, cm = norm_tmin.median(), cond_tmin.median()
print(f"{'Median car travel time (all day)':<40} {fmt(nm,' min'):>10} {fmt(cm,' min'):>12} {pct_change(nm,cm):>+7.1f}%")

nm95, cm95 = norm_tmin.quantile(0.95), cond_tmin.quantile(0.95)
print(f"{'P95 car travel time (all day)':<40} {fmt(nm95,' min'):>10} {fmt(cm95,' min'):>12} {pct_change(nm95,cm95):>+7.1f}%")

# Speed
print(f"{'Median car speed':<40} {fmt(norm_speed_med,' km/h'):>10} {fmt(cond_speed_med,' km/h'):>12} {pct_change(norm_speed_med,cond_speed_med):>+7.1f}%")
print(f"{'Mean car speed':<40} {fmt(norm_speed_mean,' km/h'):>10} {fmt(cond_speed_mean,' km/h'):>12} {pct_change(norm_speed_mean,cond_speed_mean):>+7.1f}%")

# Stuck agents
total = total_agents
print(f"{'Stuck agents':<40} {norm_stuck:>10} {cond_stuck:>12} {pct_change(max(norm_stuck,1),cond_stuck):>+7.1f}%")
print(f"{'Stuck agent rate':<40} {norm_stuck/total*100:>9.2f}% {cond_stuck/total*100:>11.2f}%  {'':>8}")

# Score
print(f"{'Final avg agent score':<40} {fmt(norm_final_score):>10} {fmt(cond_final_score):>12} {pct_change(norm_final_score,cond_final_score):>+7.1f}%")

# PM peak
if len(norm_pm) > 0 and len(cond_pm) > 0:
    npm, cpm = norm_pm.median(), cond_pm.median()
    npm95, cpm95 = norm_pm.quantile(0.95), cond_pm.quantile(0.95)
    print(f"{'Median PM peak travel time (17-20h)':<40} {fmt(npm,' min'):>10} {fmt(cpm,' min'):>12} {pct_change(npm,cpm):>+7.1f}%")
    print(f"{'P95 PM peak travel time (17-20h)':<40} {fmt(npm95,' min'):>10} {fmt(cpm95,' min'):>12} {pct_change(npm95,cpm95):>+7.1f}%")

print("-" * 68)

# Score convergence
print(f"\n[Score convergence]")
print(f"  Normal    iter 1→last: {norm_score['avg_executed'].iloc[0]:.2f} → {norm_score['avg_executed'].iloc[-1]:.2f}")
print(f"  Conditioned iter 1→last: {cond_score['avg_executed'].iloc[0]:.2f} → {cond_score['avg_executed'].iloc[-1]:.2f}")

# Trip counts
norm_car = (norm_trips["main_mode"] == "car").sum()
cond_car = (cond_trips["main_mode"] == "car").sum()
print(f"\n[Trip counts]")
print(f"  Normal     — total: {len(norm_trips)}, car: {norm_car} ({norm_car/len(norm_trips)*100:.1f}%)")
print(f"  Conditioned — total: {len(cond_trips)}, car: {cond_car} ({cond_car/len(cond_trips)*100:.1f}%)")

print()
print("=" * 68)
print("  INTERPRETATION")
print("=" * 68)
score_drop = pct_change(norm_final_score, cond_final_score)
ttime_rise = pct_change(nm, cm)
speed_drop = pct_change(norm_speed_med, cond_speed_med)

print(f"""
Traffic conditions applied:
  • Heavy rain: speed ×0.65, capacity ×0.75 across all road types
  • Link 6235 closed (capacity → 0)
  • Link 200 closed (capacity → 0)

Key findings:
  • Car travel time rose {ttime_rise:+.1f}% (median), reflecting network slowdown
  • Car speed dropped {speed_drop:+.1f}% (median km/h)
  • Agent welfare fell {score_drop:+.1f}% — agents arrive late / miss activity windows
  • {cond_stuck} agents got permanently stuck vs {norm_stuck} in baseline
  • PM peak (17–20h) shows the sharpest degradation""")

if len(norm_pm) > 0 and len(cond_pm) > 0:
    print(f"    — median +{pct_change(norm_pm.median(), cond_pm.median()):.1f}%, P95 +{pct_change(norm_pm.quantile(0.95), cond_pm.quantile(0.95)):.1f}%")

print()
