import gzip, re, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Check a range of link IDs around 6235 and 200 in both networks
check_ids = {str(i) for i in range(198, 203)} | {str(i) for i in range(6233, 6238)}

for label, path in [
    ("BASELINE  (network.xml.gz)",           os.path.join(ROOT, "data", "processed", "network.xml.gz")),
    ("CONDITIONED (network_condition.xml.gz)", os.path.join(ROOT, "data", "processed", "network_condition.xml.gz")),
]:
    found = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if "<link " not in line:
                continue
            m = re.search(r'\bid="([^"]+)"', line)
            if not m or m.group(1) not in check_ids:
                continue
            lid = m.group(1)
            fs  = re.search(r'\bfreespeed="([^"]+)"', line)
            cap = re.search(r'\bcapacity="([^"]+)"', line)
            found[lid] = (fs.group(1) if fs else "?", cap.group(1) if cap else "?")

    print(f"\n{label}")
    print(f"  {'Link ID':<10} {'freespeed':>14} {'capacity':>12} {'status'}")
    print(f"  {'-'*50}")
    for lid in sorted(check_ids, key=lambda x: int(x)):
        if lid in found:
            fs, cap = found[lid]
            print(f"  {lid:<10} {fs:>14} {cap:>12}   exists")
        else:
            print(f"  {lid:<10} {'—':>14} {'—':>12}   REMOVED")
