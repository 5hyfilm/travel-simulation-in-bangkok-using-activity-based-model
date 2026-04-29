import pandas as pd

legs = pd.read_csv("output/output_legs.csv.gz", sep=";", low_memory=False)
acts = pd.read_csv("output/output_activities.csv.gz", sep=";", low_memory=False)

def to_hours(t):
    try:
        h, m, s = str(t).split(":")
        return int(h) + int(m)/60 + int(s)/3600
    except:
        return None

legs["dep_hour"] = legs["dep_time"].apply(to_hours)
acts_lookup = acts[["activity_id","activity_type"]].copy()
late = legs[legs["dep_hour"] >= 20]
late = late.merge(acts_lookup, left_on="trip_id", right_on="activity_id", how="left")

late_work = late[late["activity_type"] == "work"].copy()
late_work["is_clone"] = late_work["person"].astype(str).str.contains("clone")

print("=== Work trips หลัง 20:00 ===")
print(late_work["is_clone"].value_counts().rename({True: "clone", False: "original"}))
print(f"\nตัวอย่าง departure time ของ original agents:")
print(late_work[~late_work["is_clone"]][["person","dep_time"]].head(10))