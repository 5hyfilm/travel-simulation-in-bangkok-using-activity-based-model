"""
bottleneck_anal.py
==================
Identify the actual Bangkok road names behind the most congested
MATSim links by cross-referencing origid (OSM way ID) back to the
OSM network file.

Reads:
  output/output_links.csv.gz   — MATSim link output (vol_car, capacity, type, origid)
  pipeline/output/network.osm — raw OSM from which the network was built

Run from project root:
  python pipeline/analysis/bottleneck_anal.py
"""

import pandas as pd
from lxml import etree

LINKS_FILE = "output/output_links.csv.gz"
OSM_FILE   = "pipeline/output/network.osm"
TOP_N      = 30   # number of top links to name

# ── Load link stats ────────────────────────────────────────────────────────
print("Loading link stats...", flush=True)
df = pd.read_csv(LINKS_FILE, sep=";", low_memory=False)
df["veh_km"]      = df["vol_car"] * df["length"] / 1000
df["utilisation"] = df["vol_car"] / df["capacity"].replace(0, float("nan"))

# Collect the unique origids we need to look up
top_links = df.nlargest(TOP_N, "vol_car").copy()
needed_ids = set(top_links["origid"].astype(str).tolist())

# Also build per-origid aggregates (a single OSM way → multiple MATSim links)
agg = (df.groupby("origid")
         .agg(vol_total   = ("vol_car",     "sum"),
              veh_km      = ("veh_km",      "sum"),
              util_max    = ("utilisation", "max"),
              n_links     = ("link",        "count"),
              length_km   = ("length",      lambda x: x.sum() / 1000),
              road_type   = ("type",        "first"))
         .reset_index()
         .sort_values("vol_total", ascending=False)
         .head(TOP_N))
needed_ids |= set(agg["origid"].astype(str).tolist())

# ── Parse OSM for road names ───────────────────────────────────────────────
print(f"Scanning OSM file for {len(needed_ids)} way IDs "
      f"(this may take 30-60 s on a 400 MB file)...", flush=True)

way_names  = {}   # origid (str) → {"name": ..., "name:en": ..., "ref": ...}

# NOTE: do NOT filter by tag= in iterparse — child <tag> elements would be
# suppressed. Instead parse all events and filter manually.
context = etree.iterparse(OSM_FILE, events=("start", "end"))
current_id   = None
current_tags = {}

for event, el in context:
    if event == "start" and el.tag == "way":
        current_id   = el.get("id")
        current_tags = {}
    elif event == "end" and el.tag == "way":
        if current_id in needed_ids:
            way_names[current_id] = {
                "name":    current_tags.get("name",    ""),
                "name_en": current_tags.get("name:en", ""),
                "ref":     current_tags.get("ref",     ""),
            }
        el.clear()
        current_id   = None
        current_tags = {}
    elif event == "start" and el.tag == "tag" and current_id in needed_ids:
        current_tags[el.get("k")] = el.get("v", "")

print(f"Found names for {len(way_names)} of {len(needed_ids)} ways.\n")


def road_label(origid):
    info = way_names.get(str(origid), {})
    name    = info.get("name",    "")
    name_en = info.get("name_en", "")
    ref     = info.get("ref",     "")
    parts = []
    if name_en: parts.append(name_en)
    elif name:  parts.append(name)
    if ref:     parts.append(f"[{ref}]")
    return " / ".join(parts) if parts else "(unnamed)"


# ── Table 1: Top links by raw volume ──────────────────────────────────────
print("=" * 75)
print("  Bottleneck Analysis — MATSim Simulation")
print("=" * 75)
print()
print("─" * 75)
print("  Table 1 — Top links by car volume (individual MATSim link segments)")
print("─" * 75)
print(f"  {'Link':>8}  {'Type':<10}  {'Vol':>7}  {'Util':>5}  Road name")
print(f"  {'─'*8}  {'─'*10}  {'─'*7}  {'─'*5}  {'─'*35}")
for _, r in top_links.iterrows():
    label = road_label(r["origid"])
    print(f"  {int(r['link']):>8}  {str(r['type']):<10}  "
          f"{int(r['vol_car']):>7,}  {r['utilisation']:>5.2f}  {label}")

# ── Table 2: Top OSM ways by aggregated volume ────────────────────────────
print()
print("─" * 75)
print("  Table 2 — Top OSM ways by total volume (all MATSim segments summed)")
print("  (better for identifying which ROAD is the bottleneck)")
print("─" * 75)
print(f"  {'OSM way':>12}  {'Type':<10}  {'Segs':>5}  {'Len km':>7}  "
      f"{'Vol':>8}  {'MaxUtil':>7}  Road name")
print(f"  {'─'*12}  {'─'*10}  {'─'*5}  {'─'*7}  {'─'*8}  {'─'*7}  {'─'*35}")
for _, r in agg.iterrows():
    label = road_label(r["origid"])
    print(f"  {int(r['origid']):>12}  {str(r['road_type']):<10}  "
          f"{int(r['n_links']):>5}  {r['length_km']:>7.2f}  "
          f"{int(r['vol_total']):>8,}  {r['util_max']:>7.2f}  {label}")

# ── Table 3: Top bottleneck ROADS with both Thai + English name ────────────
print()
print("─" * 75)
print("  Table 3 — Road name summary (Thai + English + route ref)")
print("─" * 75)
seen = set()
rank = 1
for _, r in agg.iterrows():
    oid  = str(int(r["origid"]))
    info = way_names.get(oid, {})
    name    = info.get("name",    "")
    name_en = info.get("name_en", "")
    ref     = info.get("ref",     "")
    key = name_en or name or oid
    if key in seen:
        continue
    seen.add(key)
    print(f"  #{rank:<3}  OSM {oid:<12}  [{r['road_type']:<10}]  "
          f"vol={int(r['vol_total']):>8,}  util_max={r['util_max']:.2f}")
    if name:    print(f"        Thai   : {name}")
    if name_en: print(f"        English: {name_en}")
    if ref:     print(f"        Ref    : {ref}")
    if not (name or name_en or ref):
        print(f"        (no name tag in OSM)")
    print()
    rank += 1
    if rank > 20:
        break
