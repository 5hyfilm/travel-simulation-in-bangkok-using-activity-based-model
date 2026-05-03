import pandas as pd
from lxml import etree

# โหลด output legs
legs = pd.read_csv("output/output_legs.csv.gz", sep=";", low_memory=False)

def to_seconds(t):
    try:
        h, m, s = str(t).split(":")
        return int(h)*3600 + int(m)*60 + int(s)
    except:
        return None

legs["dep_sec"] = legs["dep_time"].apply(to_seconds)
legs["dep_hour"] = legs["dep_sec"] / 3600

# หา late agents
late_agents = set(legs[legs["dep_hour"] >= 24]["person"].astype(str).unique())
print(f"Late agents: {len(late_agents):,}")

# อ่าน input plan XML เฉพาะ late agents
planned = []

for event, elem in etree.iterparse("pipeline/output/plan_300k_cut.xml", tag="person"):
    pid = str(elem.get("id"))
    if pid in late_agents:
        plan = elem.find(".//plan[@selected='yes']")
        if plan is not None:
            act_num = 0
            for act in plan.findall("activity"):
                end_time = act.get("end_time")
                if end_time:
                    planned.append({
                        "person": pid,
                        "act_num": act_num,
                        "planned_end_sec": to_seconds(end_time)
                    })
                act_num += 1
    elem.clear()

plan_df = pd.DataFrame(planned)

# เทียบกับ actual departure time
legs_late = legs[legs["person"].astype(str).isin(late_agents)].copy()
legs_late["person"] = legs_late["person"].astype(str)
legs_late = legs_late.sort_values(["person", "dep_sec"]).reset_index(drop=True)
legs_late["act_num"] = legs_late.groupby("person").cumcount()

merged = legs_late.merge(plan_df, on=["person", "act_num"], how="inner")
merged["delay_min"] = (merged["dep_sec"] - merged["planned_end_sec"]) / 60

print(f"\n=== Delay จาก input plan vs actual departure (late agents) ===")
print(f"Activities เปรียบเทียบได้: {len(merged):,}")
print(f"\nDelay distribution (นาที):")
print(merged["delay_min"].describe().round(1))

print(f"\nDelay > 30 นาที : {(merged['delay_min'] > 30).sum():,} ({(merged['delay_min'] > 30).mean()*100:.1f}%)")
print(f"Delay > 60 นาที : {(merged['delay_min'] > 60).sum():,} ({(merged['delay_min'] > 60).mean()*100:.1f}%)")
print(f"Delay > 120 นาที: {(merged['delay_min'] > 120).sum():,} ({(merged['delay_min'] > 120).mean()*100:.1f}%)")