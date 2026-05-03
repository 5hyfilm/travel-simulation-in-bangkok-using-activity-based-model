import gzip, re, os

ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
net_normal = os.path.join(ROOT, "data", "processed", "network.xml.gz")
net_cond   = os.path.join(ROOT, "data", "processed", "network_condition.xml.gz")
target_ids = {"6235", "200"}

def find_links(path):
    results = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if "<link " not in line:
                continue
            m_id = re.search(r'\bid="([^"]+)"', line)
            if not m_id:
                continue
            lid = m_id.group(1)
            if lid not in target_ids:
                continue
            fs  = re.search(r'\bfreespeed="([^"]+)"', line)
            cap = re.search(r'\bcapacity="([^"]+)"', line)
            results[lid] = {
                "freespeed": fs.group(1)  if fs  else "?",
                "capacity":  cap.group(1) if cap else "?",
            }
    return results

print("=== BASELINE network ===")
n = find_links(net_normal)
for lid in sorted(target_ids):
    if lid in n:
        print(f"  link {lid}: freespeed={n[lid]['freespeed']}  capacity={n[lid]['capacity']}")
    else:
        print(f"  link {lid}: NOT FOUND in file")

print()
print("=== CONDITIONED network ===")
c = find_links(net_cond)
for lid in sorted(target_ids):
    if lid in c:
        print(f"  link {lid}: freespeed={c[lid]['freespeed']}  capacity={c[lid]['capacity']}")
    else:
        print(f"  link {lid}: NOT FOUND in file")

print()
print("=== CHANGE SUMMARY ===")
for lid in sorted(target_ids):
    if lid in n and lid in c:
        fs_before  = float(n[lid]["freespeed"])
        fs_after   = float(c[lid]["freespeed"])
        cap_before = float(n[lid]["capacity"])
        cap_after  = float(c[lid]["capacity"])
        fs_chg  = (fs_after  - fs_before)  / fs_before  * 100 if fs_before  != 0 else float("inf")
        cap_chg = (cap_after - cap_before) / cap_before * 100 if cap_before != 0 else float("inf")
        applied = "OK" if abs(fs_chg) > 0.1 or abs(cap_chg) > 0.1 else "NO CHANGE - condition did NOT apply"
        print(f"  link {lid}: freespeed {fs_before:.4f} -> {fs_after:.6f} ({fs_chg:+.1f}%)  "
              f"capacity {cap_before:.1f} -> {cap_after:.1f} ({cap_chg:+.1f}%)  [{applied}]")
    elif lid not in n:
        print(f"  link {lid}: NOT in baseline — link ID does not exist in this network")
    elif lid not in c:
        print(f"  link {lid}: NOT in conditioned — may have been removed")
