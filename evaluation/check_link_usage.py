"""
check_link_usage.py
Check whether any agents traveled through links 6235 and 200.
Scans the most recent output folder (conditioned_output).
"""
import gzip, re, os
from collections import defaultdict

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
target_links = {"6235", "200"}

# Find which output folder to check
candidates = [
    os.path.join(ROOT, "conditioned_output"),
    os.path.join(ROOT, "demo_conditioned_output"),
    os.path.join(ROOT, "output"),
]
events_path = None
for c in candidates:
    p = os.path.join(c, "output_events.xml.gz")
    if os.path.exists(p):
        events_path = p
        break

if not events_path:
    print("ERROR: No output_events.xml.gz found!")
    exit(1)

print(f"Checking: {events_path}\n")

# ── get link attributes from the network used in this run ──────────────────
net_path = os.path.join(os.path.dirname(events_path), "output_network.xml.gz")
link_attrs = {}
with gzip.open(net_path, "rt", encoding="utf-8") as f:
    for line in f:
        if "<link " not in line:
            continue
        m_id = re.search(r'\bid="([^"]+)"', line)
        if not m_id or m_id.group(1) not in target_links:
            continue
        lid = m_id.group(1)
        fs  = re.search(r'\bfreespeed="([^"]+)"', line)
        cap = re.search(r'\bcapacity="([^"]+)"', line)
        link_attrs[lid] = {
            "freespeed": float(fs.group(1))  if fs  else 0,
            "capacity":  float(cap.group(1)) if cap else 0,
        }

print("=== Network attributes used in this run ===")
for lid in sorted(target_links):
    a = link_attrs.get(lid)
    if a:
        baseline_fs = 16.67
        applied = "✓ conditioned" if a["freespeed"] < baseline_fs * 0.5 else "✗ baseline (conditions NOT applied!)"
        print(f"  link {lid}: freespeed={a['freespeed']:.6f} m/s  capacity={a['capacity']:.1f}  [{applied}]")
    else:
        print(f"  link {lid}: NOT FOUND in network")

# ── scan events ─────────────────────────────────────────────────────────────
entered_time = defaultdict(dict)
traverse_sec = defaultdict(list)

with gzip.open(events_path, "rt", encoding="utf-8") as f:
    for line in f:
        if "entered link" not in line and "left link" not in line:
            continue
        m_link = re.search(r'\blink="([^"]+)"', line)
        if not m_link or m_link.group(1) not in target_links:
            continue
        lid   = m_link.group(1)
        m_veh = re.search(r'\b(?:person|vehicle|agentId)="([^"]+)"', line)
        m_t   = re.search(r'\btime="([^"]+)"', line)
        if not m_veh or not m_t:
            continue
        vid = m_veh.group(1)
        t   = float(m_t.group(1))
        if "entered link" in line:
            entered_time[lid][vid] = t
        elif "left link" in line:
            if vid in entered_time[lid]:
                traverse_sec[lid].append(t - entered_time[lid][vid])

# ── report ───────────────────────────────────────────────────────────────────
print()
print("=" * 58)
print("  LINK TRAVERSAL REPORT")
print("=" * 58)

import statistics

for lid in sorted(target_links):
    entered = entered_time.get(lid, {})
    times   = traverse_sec.get(lid, [])
    stuck   = len(entered) - len(times)

    print(f"\nLink {lid}:")
    print(f"  Vehicles entered          : {len(entered)}")
    print(f"  Vehicles fully crossed    : {len(times)}")
    print(f"  Vehicles stuck/teleported : {max(stuck, 0)}")

    if len(times) == 0:
        print(f"  RESULT: No agent successfully passed through link {lid} ✓")
    else:
        med = statistics.median(times)
        print(f"  Crossing time — min: {min(times):.0f}s  median: {med:.0f}s  max: {max(times):.0f}s")
        print(f"  RESULT: {len(times)} agents passed through link {lid} ✗")
