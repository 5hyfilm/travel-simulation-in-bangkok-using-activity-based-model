"""Quick check: what tags does OSM way 153265299 have?"""
from lxml import etree

OSM_FILE = "pipeline/output/network.osm"
targets = {"153265299", "680482041", "90423215"}  # top 3 congested ways
found = {}

context = etree.iterparse(OSM_FILE, events=("start", "end"), tag=("way",))
current_id = None
current_tags = {}

for event, el in context:
    if event == "start" and el.tag == "way":
        current_id = el.get("id")
        current_tags = {}
    elif event == "end" and el.tag == "way":
        if current_id in targets:
            found[current_id] = dict(current_tags)
            if len(found) == len(targets):
                break
        el.clear()
        current_id = None
        current_tags = {}
    elif el.tag == "tag" and current_id in targets:
        current_tags[el.get("k")] = el.get("v", "")

for wid, tags in found.items():
    print(f"Way {wid}:")
    for k, v in tags.items():
        print(f"  {k} = {v}")
    print()
