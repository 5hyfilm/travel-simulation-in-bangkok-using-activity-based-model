import pandas as pd

df = pd.read_csv("output/output_activities.csv.gz", sep=";", low_memory=False)

# หา last activity ของแต่ละ person
last_acts = df.sort_values(["person", "activity_number"]).groupby("person").last().reset_index()

# นับ activity_type สุดท้าย
print("=== Last activity type distribution ===")
print(last_acts["activity_type"].value_counts())
print(f"\nTotal agents: {len(last_acts)}")

# หา agent ที่ last activity ไม่ใช่ home
not_home = last_acts[last_acts["activity_type"] != "home"]
print(f"\nAgents ที่ plan ไม่ปิดด้วย home: {len(not_home)} ({len(not_home)/len(last_acts)*100:.1f}%)")

# ดู start_time ของ last activity ที่ไม่ใช่ home (เป็น seconds → แปลงเป็นชั่วโมง)
not_home = not_home.copy()
not_home["start_hour"] = not_home["start_time"] / 3600
print("\n=== Start time ของ last activity ที่ไม่ใช่ home ===")
print(not_home["start_hour"].describe().round(1))