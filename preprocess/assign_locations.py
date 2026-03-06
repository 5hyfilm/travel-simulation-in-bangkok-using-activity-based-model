import random
import pandas as pd
from tqdm import tqdm

random.seed(42)

# ==============================
# LOAD DATA
# ==============================
trips = pd.read_csv("res8/trips.csv")
facilities = pd.read_csv("facilities_cleaned.csv")

# ==============================
# PREPARE FACILITY GROUPS
# ==============================
facility_groups = {}
for activity, group in facilities.groupby("activity_type"):
    facility_groups[activity] = group[
        ["osmid", "name", "activity_type", "latitude", "longitude"]
    ].to_dict("records")

def pick_random_facility(purpose):
    subset = facility_groups.get(purpose)
    if not subset:
        return None
    return random.choice(subset)

# ==============================
# STATE TRACKING
# ==============================
current_location = {}
fixed_facility = {}
fixed_purpose = ["home", "work", "education"]

results = []

# ==============================
# SORT (ensure trip chain order)
# ==============================
trips = trips.sort_values(["person_id", "tour_id", "trip_num"]).reset_index(drop=True)

# ==============================
# MAIN LOOP
# ==============================
for row in tqdm(trips.itertuples(), total=len(trips)):
    person_id = row.person_id
    purpose = row.purpose

    # -------- INITIALIZE PERSON --------
    if person_id not in current_location:
        fixed_facility[person_id] = {}
        home_fac = pick_random_facility("home")
        if home_fac is None:
            continue
        fixed_facility[person_id]["home"] = home_fac
        current_location[person_id] = home_fac

    # -------- ORIGIN --------
    origin_fac = current_location[person_id]

    # -------- DESTINATION --------
    if purpose in fixed_purpose:
        if purpose not in fixed_facility[person_id]:
            fac = pick_random_facility(purpose)
            if fac is None:
                continue
            fixed_facility[person_id][purpose] = fac
        dest_fac = fixed_facility[person_id][purpose]
    else:
        dest_fac = pick_random_facility(purpose)
        if dest_fac is None:
            continue

    current_location[person_id] = dest_fac

    results.append({
        # ===== behavior layer =====
        "person_id": person_id,
        "tour_id": row.tour_id,
        "trip_id": row.trip_id,
        "trip_num": row.trip_num,
        "depart": row.depart,
        "purpose": purpose,
        "mode": getattr(row, "mode", "car"),
        # ===== origin =====
        "origin_osmid": origin_fac["osmid"],
        "origin_name": origin_fac["name"],
        "origin_lat": origin_fac["latitude"],
        "origin_lon": origin_fac["longitude"],
        # ===== destination =====
        "dest_osmid": dest_fac["osmid"],
        "dest_name": dest_fac["name"],
        "dest_lat": dest_fac["latitude"],
        "dest_lon": dest_fac["longitude"],
    })

# ==============================
# SAVE OUTPUT
# ==============================
result_df = pd.DataFrame(results)
result_df = result_df.sort_values(["person_id", "tour_id", "trip_num"])
result_df.to_csv("final_trips.csv", index=False)
print("Done.")
