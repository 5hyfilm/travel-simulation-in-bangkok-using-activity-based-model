import gzip, re, os

ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
target = {"200", "6235"}

for label, net_path in [
    ("demo_conditioned_output (actual run)", os.path.join(ROOT, "demo_conditioned_output", "output_network.xml.gz")),
    ("current network_condition.xml.gz",     os.path.join(ROOT, "data", "processed", "network_condition.xml.gz")),
]:
    found = {}
    with gzip.open(net_path, "rt", encoding="utf-8") as f:
        for line in f:
            if "<link " not in line:
                continue
            m_id = re.search(r'\bid="([^"]+)"', line)
            if not m_id or m_id.group(1) not in target:
                continue
            lid = m_id.group(1)
            fs  = re.search(r'\bfreespeed="([^"]+)"', line)
            cap = re.search(r'\bcapacity="([^"]+)"', line)
            found[lid] = {
                "freespeed": fs.group(1) if fs else "?",
                "capacity":  cap.group(1) if cap else "?",
            }
    print(f"\n{label}:")
    for lid in sorted(target):
        if lid in found:
            print(f"  link {lid}: freespeed={found[lid]['freespeed']}  capacity={found[lid]['capacity']}")
        else:
            print(f"  link {lid}: NOT FOUND")
