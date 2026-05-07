"""
validate_google_maps.py
=======================
Validate the MATSim Bangkok simulation against real-world travel times
fetched from the Google Maps Distance Matrix API.

Method
------
1. Use 30 predefined common Bangkok routes covering all major corridors.
2. For each route, find simulation agents whose origin/destination grid cell
   matches the route endpoints.
3. Compute the median simulated travel time per time window
   (AM peak, midday, PM peak).
4. Query Google Maps Distance Matrix API for the same O-D at the same hour.
5. Compare and produce a realism scorecard with MAPE and RMSE.

Requirements
------------
  pip install googlemaps
  Google Maps API key set in config.json → api_keys → google_maps

References
----------
  [1] TomTom Traffic Index 2024 – Bangkok
      https://www.tomtom.com/traffic-index/bangkok-traffic/
  [2] INRIX 2023 Global Traffic Scorecard  https://inrix.com/scorecard/
  [3] ADB Urban Transport Outlook for SEA (2023)
      https://www.adb.org/publications/urban-transport-outlook-southeast-asia
  [4] Thailand NESDC Household Travel Survey 2019
  [5] Waze Driver Satisfaction Index 2023

Run from project root:
  python evaluation/validate_google_maps.py
"""

import os
import json
import math
import datetime
import numpy as np
import pandas as pd
import googlemaps
from pyproj import Transformer

# ── Config ──────────────────────────────────────────────────────────────────
_cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(_cfg_path, encoding="utf-8") as _f:
    _cfg = json.load(_f)
GOOGLE_MAPS_API_KEY = _cfg.get("api_keys", {}).get("google_maps", "YOUR_API_KEY_HERE")

TRIPS_FILE        = os.path.join(os.path.dirname(__file__), "..", "normal_output", "output", "output_trips.csv.gz")
GRID_DEG          = 0.015    # ~1.7 km cell side (kept for coord snapping only)
MIN_AGENTS        = 10       # minimum agents per window to report
MAX_DIST_KM       = 60
MIN_DIST_KM       = 1.5
SEARCH_RADIUS_KM  = 3.0      # radius around each route endpoint to collect agents

QUERY_HOURS = {
    "AM peak  (07:00)": 7,
    "Midday   (12:00)": 12,
    "PM peak  (17:00)": 17,
}

# ── 30 Predefined Bangkok Common Routes ─────────────────────────────────────
# (name, origin_lat, origin_lon, dest_lat, dest_lon)
# Covers: CBD corridors, airport routes, suburb-to-CBD commutes,
#         cross-town routes, expressway corridors
ROUTES = [
    # ── CBD / Inner Ring ─────────────────────────────────────────────────────
    ("Silom → Chatuchak (Phahon Yothin N)",        13.7221, 100.5296, 13.8030, 100.5530),
    ("Chatuchak → Silom (Phahon Yothin S)",        13.8030, 100.5530, 13.7221, 100.5296),
    ("Silom → Sukhumvit Asok",                     13.7221, 100.5296, 13.7374, 100.5608),
    ("Sukhumvit Asok → Silom",                     13.7374, 100.5608, 13.7221, 100.5296),
    ("Silom → Victory Monument",                   13.7221, 100.5296, 13.7649, 100.5374),
    ("Victory Monument → Silom",                   13.7649, 100.5374, 13.7221, 100.5296),

    # ── Airport Routes ───────────────────────────────────────────────────────
    ("Charoennakorn → Victory Monument",           13.7201, 100.5072, 13.7649, 100.5374),
    ("Don Mueang Airport → Silom",                 13.9126, 100.6069, 13.7221, 100.5296),
    ("Chatuchak → Don Mueang Airport",             13.8030, 100.5530, 13.9126, 100.6069),
    ("Don Mueang Airport → Chatuchak",             13.9126, 100.6069, 13.8030, 100.5530),

    # ── North Corridor (Vibhavadi / Phahon Yothin) ───────────────────────────
    ("Bang Khen → Chatuchak",                      13.8700, 100.5900, 13.8030, 100.5530),
    ("Chatuchak → Bang Khen",                      13.8030, 100.5530, 13.8700, 100.5900),
    ("Ratchada → Victory Monument",                13.7670, 100.5700, 13.7649, 100.5374),
    ("Victory Monument → Ratchada",                13.7649, 100.5374, 13.7670, 100.5700),

    # ── East Corridor (Sukhumvit / Bangna / Srinakarin) ─────────────────────
    ("Bangna → Silom",                             13.6764, 100.6052, 13.7221, 100.5296),
    ("Silom → Bangna",                             13.7221, 100.5296, 13.6764, 100.6052),
    ("On Nut → Sukhumvit Asok",                    13.7016, 100.6014, 13.7374, 100.5608),
    ("Bearing → Sukhumvit Asok",                   13.6700, 100.6100, 13.7374, 100.5608),
    ("Lad Krabang → Silom",                        13.7271, 100.7507, 13.7221, 100.5296),
    ("Minburi → Ratchada",                         13.8012, 100.7500, 13.7670, 100.5700),

    # ── West Corridor (Pinklao / Taling Chan / Borommaratchachonnani) ────────
    ("Pinklao → Silom",                            13.7700, 100.4800, 13.7221, 100.5296),
    ("Silom → Pinklao",                            13.7221, 100.5296, 13.7700, 100.4800),
    ("Taling Chan → Victory Monument",             13.7811, 100.4600, 13.7649, 100.5374),

    # ── South Corridor (Rama II / On Nut) ───────────────────────────────────
    ("Udomsuk → Sukhumvit Asok",                   13.6760, 100.6300, 13.7374, 100.5608),
    ("Prawet → Silom",                             13.6869, 100.6550, 13.7221, 100.5296),

    # ── Northeast Corridor (Lat Phrao / Ram Intra / Kaset Nawamin) ──────────
    ("Lat Phrao → Victory Monument",               13.8122, 100.5701, 13.7649, 100.5374),
    ("Nawamin → Chatuchak",                        13.8400, 100.6200, 13.8030, 100.5530),
    ("Kaset Nawamin → Ratchada",                   13.8200, 100.6100, 13.7670, 100.5700),

    # ── Cross-Town ───────────────────────────────────────────────────────────
    ("Bang Kapi → Victory Monument",               13.7556, 100.6400, 13.7649, 100.5374),
    ("Thonburi → Silom (cross-river)",             13.7201, 100.4972, 13.7221, 100.5296),
]

# ── Helpers ──────────────────────────────────────────────────────────────────
_tf_to_wgs = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)

def hms_to_sec(t):
    try:
        h, m, s = str(t).split(":")
        return int(h)*3600 + int(m)*60 + int(s)
    except:
        return None

def next_tuesday():
    today = datetime.date.today()
    days  = (1 - today.weekday()) % 7
    return today + datetime.timedelta(days=days if days else 7)

NEXT_TUE = next_tuesday()

def gm_timestamp(hour):
    return datetime.datetime(NEXT_TUE.year, NEXT_TUE.month, NEXT_TUE.day, hour, 0, 0)

def snap_cell(lat, lon):
    """Snap lat/lon to grid cell centre."""
    clat = (math.floor(lat / GRID_DEG) + 0.5) * GRID_DEG
    clon = (math.floor(lon / GRID_DEG) + 0.5) * GRID_DEG
    return round(clat, 6), round(clon, 6)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ── Load trips ───────────────────────────────────────────────────────────────
print("Loading simulation trips...", flush=True)
trips = pd.read_csv(TRIPS_FILE, sep=";", low_memory=False)
trips["trav_sec"] = trips["trav_time"].apply(hms_to_sec)
trips["trav_min"] = trips["trav_sec"] / 60
trips["dep_sec"]  = trips["dep_time"].apply(hms_to_sec)
trips["dep_hour"] = trips["dep_sec"] / 3600
trips["dist_km"]  = trips["traveled_distance"] / 1000

trips = trips[
    (trips["dep_hour"] < 24) &
    (trips["dist_km"] >= MIN_DIST_KM) &
    (trips["dist_km"] <= MAX_DIST_KM) &
    (trips["trav_min"] > 0)
].copy()

print("Converting coordinates...", flush=True)
lons_o, lats_o = _tf_to_wgs.transform(trips["start_x"].values, trips["start_y"].values)
lons_d, lats_d = _tf_to_wgs.transform(trips["end_x"].values,   trips["end_y"].values)
trips["orig_lat"] = lats_o;  trips["orig_lon"] = lons_o
trips["dest_lat"] = lats_d;  trips["dest_lon"] = lons_d

trips = trips[
    ((trips["orig_lat"] - trips["dest_lat"])**2 +
     (trips["orig_lon"] - trips["dest_lon"])**2) > 1e-6
].copy()

# ── Google Maps client ───────────────────────────────────────────────────────
use_gmaps = GOOGLE_MAPS_API_KEY != "YOUR_API_KEY_HERE"
if use_gmaps:
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def get_gm_time(origin_ll, dest_ll, hour):
    if not use_gmaps:
        return None
    try:
        r = gmaps.distance_matrix(
            origins=[origin_ll], destinations=[dest_ll],
            mode="driving",
            departure_time=gm_timestamp(hour),
            traffic_model="best_guess",
        )
        el = r["rows"][0]["elements"][0]
        if el["status"] == "OK":
            dur = el.get("duration_in_traffic", el["duration"])
            return round(dur["value"] / 60, 1)
    except:
        pass
    return None

# ── Main comparison ──────────────────────────────────────────────────────────
W = 82
print("=" * W)
print("  Bangkok Simulation Validation — MATSim vs Google Maps")
print("=" * W)
print(f"  Reference date   : {NEXT_TUE} (Tuesday — typical weekday)")
print(f"  Routes           : {len(ROUTES)} predefined Bangkok corridors")
print(f"  Search radius    : {SEARCH_RADIUS_KM} km around each endpoint")
print(f"  Min agents/window: {MIN_AGENTS}")
print(f"  {'✅ Google Maps API connected' if use_gmaps else '⚠️  No API key — simulation only'}")
print()

all_rows = []

# Pre-compute degree-equivalent of search radius for fast bbox pre-filter
_DEG_LAT = SEARCH_RADIUS_KM / 111.0
_DEG_LON = SEARCH_RADIUS_KM / 111.0   # close enough for Bangkok latitude

def agents_near_route(o_lat, o_lon, d_lat, d_lon):
    """Return boolean mask of trips within SEARCH_RADIUS_KM of both endpoints."""
    # Coarse bbox pre-filter (fast)
    o_mask = (
        (trips["orig_lat"] >= o_lat - _DEG_LAT) & (trips["orig_lat"] <= o_lat + _DEG_LAT) &
        (trips["orig_lon"] >= o_lon - _DEG_LON) & (trips["orig_lon"] <= o_lon + _DEG_LON)
    )
    d_mask = (
        (trips["dest_lat"] >= d_lat - _DEG_LAT) & (trips["dest_lat"] <= d_lat + _DEG_LAT) &
        (trips["dest_lon"] >= d_lon - _DEG_LON) & (trips["dest_lon"] <= d_lon + _DEG_LON)
    )
    candidate = trips[o_mask & d_mask]
    if len(candidate) == 0:
        return candidate.index

    # Precise haversine filter on candidates only
    R = 6371.0
    def hav_col(lat1, lon1, lat2_col, lon2_col):
        dlat = np.radians(lat2_col - lat1)
        dlon = np.radians(lon2_col - lon1)
        a = np.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
            np.cos(np.radians(lat2_col)) * np.sin(dlon/2)**2
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    dist_o = hav_col(o_lat, o_lon, candidate["orig_lat"].values, candidate["orig_lon"].values)
    dist_d = hav_col(d_lat, d_lon, candidate["dest_lat"].values, candidate["dest_lon"].values)
    return candidate[(dist_o <= SEARCH_RADIUS_KM) & (dist_d <= SEARCH_RADIUS_KM)].index

for rank, (name, o_lat, o_lon, d_lat, d_lon) in enumerate(ROUTES, 1):
    dist_km = haversine_km(o_lat, o_lon, d_lat, d_lon)
    route_idx = agents_near_route(o_lat, o_lon, d_lat, d_lon)
    n_all = len(route_idx)

    print("─" * W)
    print(f"  Route #{rank:02d}  {name}")
    print(f"  Origin : ({o_lat:.4f}, {o_lon:.4f})  →  Dest: ({d_lat:.4f}, {d_lon:.4f})")
    print(f"  Straight-line: {dist_km:.1f} km   Agents within {SEARCH_RADIUS_KM} km radius: {n_all:,}")
    print()
    print(f"  {'Window':<16} {'Agents':>8} {'Sim median':>11} {'Google Maps':>12} {'Ratio':>7} {'Match?':>8}")
    print(f"  {'─'*16} {'─'*8} {'─'*11} {'─'*12} {'─'*7} {'─'*8}")

    for label, gm_hour in QUERY_HOURS.items():
        if   gm_hour == 7:  lo, hi = 7,  9
        elif gm_hour == 12: lo, hi = 11, 13
        else:               lo, hi = 17, 19

        mask = (
            trips.index.isin(route_idx) &
            (trips["dep_hour"] >= lo) & (trips["dep_hour"] < hi)
        )
        sample = trips[mask]["trav_min"].dropna()
        sample = sample[sample <= 120]
        n = len(sample)

        if n < MIN_AGENTS:
            print(f"  {label:<16} {n:>8} {'—':>11} {'—':>12} {'—':>7} {'—':>8}")
            all_rows.append({"route": rank, "name": name, "window": label,
                             "n": n, "sim": None, "gm": None, "ratio": None})
            continue

        sim_med = round(sample.median(), 1)
        gm_time = get_gm_time((o_lat, o_lon), (d_lat, d_lon), gm_hour)

        if gm_time:
            ratio = sim_med / gm_time
            ok    = "✅" if 0.65 <= ratio <= 1.35 else ("⚠️ " if 0.50 <= ratio <= 1.50 else "❌")
            r_str = f"{ratio:.2f}x"
        else:
            ok, r_str, ratio = "—", "—", None

        sim_str = f"{sim_med:.0f} min"
        gm_str  = f"{gm_time:.0f} min" if gm_time else "—"
        print(f"  {label:<16} {n:>8,} {sim_str:>11} {gm_str:>12} {r_str:>7} {ok:>8}")
        all_rows.append({"route": rank, "name": name, "window": label,
                         "n": n, "sim": sim_med, "gm": gm_time, "ratio": ratio})
    print()

# ── Scorecard ────────────────────────────────────────────────────────────────
df = pd.DataFrame(all_rows).dropna(subset=["sim", "gm"])

print("=" * W)
print("  REALISM SCORECARD")
print("=" * W)

if len(df) == 0:
    print("  No comparable windows — check API key or reduce MIN_AGENTS.")
else:
    n_pass = ((df["ratio"] >= 0.65) & (df["ratio"] <= 1.35)).sum()
    n_warn = (((df["ratio"] >= 0.50) & (df["ratio"] < 0.65)) |
              ((df["ratio"] > 1.35) & (df["ratio"] <= 1.50))).sum()
    n_fail = len(df) - n_pass - n_warn

    mape = float(np.mean(np.abs(df["sim"] - df["gm"]) / df["gm"]) * 100)
    rmse = float(np.sqrt(np.mean((df["sim"] - df["gm"])**2)))
    mae  = float(np.mean(np.abs(df["sim"] - df["gm"])))

    # Bias — systematic over/under-estimation
    bias     = float(np.mean(df["sim"] - df["gm"]))
    bias_pct = float(np.mean((df["sim"] - df["gm"]) / df["gm"]) * 100)

    # R² — does the simulation rank routes in the same order as Google Maps?
    ss_res = float(np.sum((df["sim"] - df["gm"])**2))
    ss_tot = float(np.sum((df["gm"]  - df["gm"].mean())**2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    # Pearson correlation
    corr = float(df["sim"].corr(df["gm"]))

    # Per time-window accuracy
    window_acc = {}
    for win in df["window"].unique():
        sub = df[df["window"] == win]
        n_p = ((sub["ratio"] >= 0.65) & (sub["ratio"] <= 1.35)).sum()
        window_acc[win.strip()] = (n_p, len(sub))

    accuracy_pct = n_pass / len(df) * 100

    print(f"  Comparable windows  : {len(df)}")
    print()
    print(f"  ── Accuracy ────────────────────────────────────────")
    print(f"  Accuracy (PASS rate): {n_pass}/{len(df)}  ({accuracy_pct:.0f}%)  "
          f"← % of routes within ±35% of Google Maps")
    print(f"  ✅ PASS (0.65–1.35) : {n_pass}  ({n_pass/len(df)*100:.0f}%)")
    print(f"  ⚠️  WARN (0.50–1.50) : {n_warn}  ({n_warn/len(df)*100:.0f}%)")
    print(f"  ❌ FAIL (<0.50/>1.50): {n_fail}  ({n_fail/len(df)*100:.0f}%)")
    print()
    print(f"  Accuracy by time window:")
    for win, (np_, nt) in window_acc.items():
        bar = "✅" if np_/nt >= 0.60 else ("⚠️ " if np_/nt >= 0.40 else "❌")
        print(f"    {bar} {win:<20}: {np_}/{nt}  ({np_/nt*100:.0f}%)")
    print()
    print(f"  ── Average travel time ─────────────────────────────")
    print(f"  Avg sim time    : {df['sim'].mean():.1f} min")
    print(f"  Avg Google time : {df['gm'].mean():.1f} min")
    print(f"  Difference      : {df['sim'].mean() - df['gm'].mean():+.1f} min")
    print()
    print(f"  ── Error metrics ───────────────────────────────────")
    print(f"  MAPE  : {mape:.1f}%   ← avg % error per route-window")
    print(f"  MAE   : {mae:.1f} min ← avg absolute error in minutes")
    print(f"  RMSE  : {rmse:.1f} min ← penalises large errors more")
    print()
    print(f"  ── Bias (systematic error) ─────────────────────────")
    direction = "slower" if bias > 0 else "faster"
    print(f"  Bias  : {bias:+.1f} min  ({bias_pct:+.1f}%)  "
          f"← simulation is systematically {direction} than reality")
    print(f"  Median ratio : {df['ratio'].median():.2f}x")
    print(f"  Mean ratio   : {df['ratio'].mean():.2f}x")
    print()
    # print(f"  ── Correlation ─────────────────────────────────────")
    # print(f"  R²   : {r2:.3f}  ← how well sim captures variation across routes")
    # print(f"  Corr : {corr:.3f} ← Pearson correlation with Google Maps")
    # r2_interp = "excellent" if r2 >= 0.80 else ("good" if r2 >= 0.60 else ("moderate" if r2 >= 0.40 else "poor"))
    # print(f"         ({r2_interp} fit — sim {'tracks' if r2 >= 0.60 else 'does not track'} "
    #       f"real-world route difficulty pattern)")
    # print()

    # if bias_pct < -20:
    #     print("  ⚠️  Simulation is systematically faster than reality.")
    #     print("     Sub-sampling effect: low demand → less congestion than real Bangkok.")
    #     print(f"     Calibration factor: ~{1/df['ratio'].median():.1f}x to match real travel times.")
    # elif bias_pct > 20:
    #     print("  ⚠️  Simulation is systematically slower than reality → over-congested.")
    #     print("     Consider raising flowCapacityFactor in config.xml.")
    # else:
    #     print("  ✅ No significant systematic bias — simulation is well-calibrated.")

    # Top 5 worst by absolute error
    # df["abs_error"] = (df["sim"] - df["gm"]).abs()
    # df["error_pct"] = (df["sim"] - df["gm"]) / df["gm"] * 100
    # worst = df.nlargest(5, "abs_error")[["name", "window", "sim", "gm", "abs_error", "error_pct"]]
    # if len(worst) > 0:
    #     print()
    #     print(f"  Top 5 worst windows (largest absolute error):")
    #     print(f"  {'Route':<45} {'Window':<20} {'Sim':>6} {'Real':>6} {'Error':>8} {'Error%':>8}")
    #     print(f"  {'─'*45} {'─'*20} {'─'*6} {'─'*6} {'─'*8} {'─'*8}")
    #     for _, row in worst.iterrows():
    #         sign = "+" if row["error_pct"] > 0 else ""
    #         print(f"  {row['name'][:45]:<45} {row['window'].strip():<20} "
    #               f"{row['sim']:>5.0f}m {row['gm']:>5.0f}m "
    #               f"{row['abs_error']:>7.1f}m {sign}{row['error_pct']:>6.1f}%")

# print()
# print("─" * W)
# print("  References")
# print("─" * W)
# print("  [1] TomTom Traffic Index 2024 — Bangkok")
# print("      https://www.tomtom.com/traffic-index/bangkok-traffic/")
# print("      Bangkok average: 36% extra travel time vs free-flow.")
# print()
# print("  [2] INRIX 2023 Global Traffic Scorecard")
# print("      https://inrix.com/scorecard/")
# print("      Bangkok: 64.5 hours/year lost to congestion per driver.")
# print()
# print("  [3] ADB — Urban Transport Outlook for Southeast Asia (2023)")
# print("      https://www.adb.org/publications/urban-transport-outlook-southeast-asia")
# print("      Bangkok modal split: private car ~38% of motorised trips.")
# print()
# print("  [4] Thailand NESDC Household Travel Survey 2019")
# print("      Average car trip distance BMA: 11–14 km.")
# print("      AM peak accounts for ~18–22% of daily car trips.")
# print()
# print("  [5] Waze Driver Satisfaction Index 2023")
# print("      Bangkok ranked 2nd most congested city in Southeast Asia.")
# print()
# print("  [6] Cambridge Systematics (2010) — Travel Model Validation and")
# print("      Reasonableness Checking Manual, §4.3 (prepared for FHWA/TMIP).")
# print("      Recommends ±25–35% tolerance for corridor-level travel time")
# print("      validation in sub-area and sub-sampled demand models.")
# print("      → Basis for PASS band (ratio 0.65–1.35).")
# print()
# print("  [7] Horni, A., Nagel, K. & Axhausen, K.W. (eds.) (2016)")
# print("      The Multi-Agent Transport Simulation MATSim, Chapter 4.")
# print("      Ubiquity Press. https://doi.org/10.5334/baw")
# print("      Sub-sampled scenarios (< 10% population) require wider tolerances")
# print("      due to stochastic demand effects.")
# print("      → Basis for WARN band (ratio 0.50–1.50).")
# print("=" * W)
