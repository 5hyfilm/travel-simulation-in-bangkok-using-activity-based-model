import xml.etree.ElementTree as ET
from collections import defaultdict

hour_trips = defaultdict(int)
hour_agents = defaultdict(set)
total_agents = set()

for event, elem in ET.iterparse("pipeline/output/plan_300k_cut.xml", events=["end"]):
    if elem.tag == "person":
        person_id = elem.get("id")
        total_agents.add(person_id)
        plan = elem.find(".//plan[@selected='yes']")
        if plan is not None:
            for act in plan.findall("activity"):
                end_time = act.get("end_time")
                if end_time:
                    try:
                        h = int(end_time.split(":")[0])
                        hour_trips[h] += 1
                        hour_agents[h].add(person_id)
                    except:
                        pass
        elem.clear()

total_trips = sum(hour_trips.values())
print(f"=== Plan XML trip distribution ===")
print(f"Total car trips : {total_trips:,}")
print(f"Total agents    : {len(total_agents):,}\n")

for h in range(0, 30):
    count = hour_trips.get(h, 0)
    agents = len(hour_agents.get(h, set()))
    bar = "█" * int(count/total_trips*300) if total_trips > 0 else ""
    print(f"  {h:02d}:00  trips={count:>7,} ({count/total_trips*100:4.1f}%)  agents={agents:>6,}  {bar}")