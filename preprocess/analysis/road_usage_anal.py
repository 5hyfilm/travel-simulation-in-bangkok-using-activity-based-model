"""
road_usage_anal.py
==================
Analyse which road types agents actually used during the simulation.

Reads:
  output/output_links.csv.gz  — MATSim link-level output (volume, speed, capacity, type)

Run from project root:
  python preprocess/analysis/road_usage_anal.py
"""

import pandas as pd

LINKS_FILE = "output/output_links.csv.gz"

df = pd.read_csv(LINKS_FILE, sep=";", low_memory=False)

# ── basic derived columns ──────────────────────────────────────────────────
df["length_km"]     = df["length"] / 1000
df["freespeed_kph"] = df["freespeed"] * 3.6
df["used"]          = df["vol_car"] > 0

# volume × length = veh·km (distance driven on each link)
df["veh_km"] = df["vol_car"] * df["length_km"]

# utilisation = vol_car / capacity  (dimensionless; >1 means over-capacity for 1 hr)
df["utilisation"] = df["vol_car"] / df["capacity"].replace(0, float("nan"))

total_links   = len(df)
total_vol     = df["vol_car"].sum()
total_veh_km  = df["veh_km"].sum()

print("=" * 65)
print("  Road Usage Analysis — MATSim Simulation Output")
print("=" * 65)
print(f"  Total links in network : {total_links:>10,}")
print(f"  Links with vol_car > 0 : {df['used'].sum():>10,}  ({df['used'].mean()*100:.1f}% of network)")
print(f"  Total car passages     : {int(total_vol):>10,}")
print(f"  Total veh·km           : {total_veh_km:>10,.1f} km")
print()

# ── per road-type summary ──────────────────────────────────────────────────
grp = df.groupby("type").agg(
    n_links        = ("link",        "count"),
    n_used         = ("used",        "sum"),
    vol_total      = ("vol_car",     "sum"),
    vol_mean       = ("vol_car",     "mean"),
    vol_max        = ("vol_car",     "max"),
    veh_km         = ("veh_km",      "sum"),
    length_km_sum  = ("length_km",   "sum"),
    freespeed_kph  = ("freespeed_kph","mean"),
    util_mean      = ("utilisation", "mean"),
    util_max       = ("utilisation", "max"),
).reset_index()

grp["pct_vol"]     = grp["vol_total"]  / total_vol * 100
grp["pct_veh_km"]  = grp["veh_km"]    / total_veh_km * 100
grp["pct_used"]    = grp["n_used"]     / grp["n_links"] * 100

grp = grp.sort_values("vol_total", ascending=False)

# ── Table 1: Volume by road type ───────────────────────────────────────────
print("─" * 65)
print("  Table 1 — Car passages by road type (sorted by volume)")
print("─" * 65)
print(f"  {'Type':<18} {'Links':>7} {'Used%':>6} {'Volume':>9} {'Vol%':>6} {'Bar'}")
print(f"  {'─'*18} {'─'*7} {'─'*6} {'─'*9} {'─'*6}")
for _, r in grp.iterrows():
    bar = "█" * int(r["pct_vol"] / 1.5)
    print(f"  {r['type']:<18} {int(r['n_links']):>7,} {r['pct_used']:>5.1f}% "
          f"{int(r['vol_total']):>9,} {r['pct_vol']:>5.1f}%  {bar}")

# ── Table 2: Distance (veh·km) by road type ───────────────────────────────
print()
print("─" * 65)
print("  Table 2 — Vehicle·km by road type (where agents spend time)")
print("─" * 65)
print(f"  {'Type':<18} {'Veh·km':>10} {'VKm%':>6} {'Avg speed':>10} {'Bar'}")
print(f"  {'─'*18} {'─'*10} {'─'*6} {'─'*10}")
for _, r in grp.iterrows():
    bar = "█" * int(r["pct_veh_km"] / 1.5)
    print(f"  {r['type']:<18} {r['veh_km']:>10,.0f} {r['pct_veh_km']:>5.1f}%"
          f" {r['freespeed_kph']:>8.1f}kph  {bar}")

# ── Table 3: Congestion (utilisation) by road type ────────────────────────
print()
print("─" * 65)
print("  Table 3 — Congestion proxy (vol / capacity) by road type")
print("  (>1 means link processed more vehicles than 1hr capacity)")
print("─" * 65)
print(f"  {'Type':<18} {'Util mean':>10} {'Util max':>10} {'Overloaded links':>17}")
print(f"  {'─'*18} {'─'*10} {'─'*10} {'─'*17}")
for _, r in grp.iterrows():
    type_df = df[df["type"] == r["type"]]
    overloaded = (type_df["utilisation"] > 1).sum()
    print(f"  {r['type']:<18} {r['util_mean']:>10.2f} {r['util_max']:>10.1f} "
          f"{overloaded:>10,} / {int(r['n_links']):,}")

# ── Top 10 most-used links ─────────────────────────────────────────────────
print()
print("─" * 65)
print("  Top 10 most-used links")
print("─" * 65)
top = df.nlargest(10, "vol_car")[["link","type","length_km","freespeed_kph","capacity","vol_car","utilisation"]]
top["length_km"]     = top["length_km"].round(3)
top["freespeed_kph"] = top["freespeed_kph"].round(1)
top["utilisation"]   = top["utilisation"].round(2)
print(top.to_string(index=False))

# ── Zero-volume links (unused roads) ──────────────────────────────────────
print()
print("─" * 65)
print("  Unused links (vol_car = 0) by road type")
print("─" * 65)
unused = df[~df["used"]].groupby("type").size().sort_values(ascending=False)
total_unused = (~df["used"]).sum()
print(f"  Total unused links: {total_unused:,} ({total_unused/total_links*100:.1f}% of network)\n")
for rtype, cnt in unused.items():
    pct = cnt / df[df["type"]==rtype]["link"].count() * 100
    print(f"  {rtype:<20} {cnt:>7,}  ({pct:.0f}% of that type unused)")
