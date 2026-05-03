import xml.etree.ElementTree as ET
from collections import Counter

# parse เฉพาะ way elements ไม่โหลดทั้งไฟล์
highway_types = Counter()

for event, elem in ET.iterparse("pipeline/output/network.osm", events=["end"]):
    if elem.tag == "way":
        for tag in elem.iter("tag"):
            if tag.get("k") == "highway":
                highway_types[tag.get("v")] += 1
        elem.clear()

print("=== Highway types in OSM ===")
for htype, count in sorted(highway_types.items(), key=lambda x: -x[1]):
    print(f"  {htype:<30} {count:>8,}")