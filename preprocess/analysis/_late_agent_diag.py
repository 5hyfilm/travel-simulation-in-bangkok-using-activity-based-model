"""
Diagnose WHY late agents (dep_hour >= 24) are late.
Are they naturally late-night travellers, or genuine congestion victims?
"""
import pandas as pd
from lxml import etree

PLAN_FILE = "preprocess/output/plan_300k_cut.xml"

legs = pd.read_csv("output/output_legs.csv.gz", sep=";", low_memory=False)

def to_sec(t):
    try:
        h, m, s = str(t).split(":")
        return int(h)*3600 + int(m)*60 + int(s)
    except:
        return None

legs["dep_sec"]  = legs["dep_time"].apply(to_sec)
legs["dep_hour"] = legs["dep_sec"] / 3600

late_agents = set(legs[legs["dep_hour"] >= 24]["person"].astype(str).unique())
print(f"Late agents: {len(late_agents):,}")

# ── For late agents: find their first leg departure (planned) ──────────────
planned_first_dep = {}   # person → first planned end_time (seconds)
all_end_times     = []   # every end_time across all late agents

for event, elem in etree.iterparse(PLAN_FILE, tag="person"):
    pid = str(elem.get("id"))
    if pid in late_agents:
        plan = elem.find(".//plan[@selected='yes']")
        if plan is not None:
            for act in plan.findall("activity"):
                et = act.get("end_time")
                if et:
                    sec = to_sec(et)
                    if sec is not None:
                        all_end_times.append(sec / 3600)  # in hours
                        if pid not in planned_first_dep:
                            planned_first_dep[pid] = sec / 3600
    elem.clear()

s = pd.Series(all_end_times)
print(f"\n── Planned activity end_times (hours) for late agents ──")
print(f"  Count  : {len(s):,}")
print(f"  Mean   : {s.mean():.1f}h")
print(f"  Median : {s.median():.1f}h")
print(f"  Planned after 20:00 : {(s > 20).sum():,} ({(s > 20).mean()*100:.1f}%)")
print(f"  Planned after 21:00 : {(s > 21).sum():,} ({(s > 21).mean()*100:.1f}%)")
print(f"  Planned after 22:00 : {(s > 22).sum():,} ({(s > 22).mean()*100:.1f}%)")
print(f"  Planned after 23:00 : {(s > 23).sum():,} ({(s > 23).mean()*100:.1f}%)")

# ── Actual late departure distribution ────────────────────────────────────
late_legs = legs[legs["person"].astype(str).isin(late_agents) & (legs["dep_hour"] >= 24)]
print(f"\n── Actual late legs (dep_hour >= 24) ──")
print(f"  Count: {len(late_legs):,}")
print(f"  dep_hour distribution:")
h = late_legs["dep_hour"]
print(f"    24–25h: {((h>=24)&(h<25)).sum():,}")
print(f"    25–27h: {((h>=25)&(h<27)).sum():,}")
print(f"    27–30h: {((h>=27)&(h<30)).sum():,}")
print(f"    30h+  : {(h>=30).sum():,}")

# ── Travel time of the late legs ──────────────────────────────────────────
if "trav_time" in late_legs.columns:
    late_legs = late_legs.copy()
    late_legs["trav_sec"] = late_legs["trav_time"].apply(to_sec)
    print(f"\n── Travel time of late legs (minutes) ──")
    print((late_legs["trav_sec"] / 60).describe().round(1))
