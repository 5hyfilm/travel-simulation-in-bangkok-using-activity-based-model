import gzip
import xml.etree.ElementTree as ET
from collections import Counter

root = ET.parse(gzip.open("data/processed/network.xml.gz", "rb")).getroot()

type_count = Counter()
for link in root.findall(".//link"):
    for attr in link.findall("attributes/attribute"):
        if attr.attrib.get("name") == "type":
            type_count[attr.text] += 1

total = sum(type_count.values())
print(f"{'type':<20} {'count':>7}  {'%':>6}")
print("-" * 38)
for t, c in sorted(type_count.items(), key=lambda x: -x[1]):
    print(f"{t:<20} {c:>7}  {c/total*100:>5.1f}%")