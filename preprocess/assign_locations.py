import random
import pandas as pd
from tqdm import tqdm

# ActivitySim purpose → facility activity_type mapping
_PURPOSE_MAP = {
    "home":      "home",
    "work":      "work",
    "atwork":    "work",
    "shopping":  "shopping",
    "school":    "education",
    "univ":      "education",
    "eatout":    "dining",
    "social":    "leisure",
    "othdiscr":  "leisure",
    "escort":    "home",
    "othmaint":  "public_service",
}

# ActivitySim mode → MATSim mode mapping
_CAR_MODES = {
    "DRIVEALONEFREE", "DRIVEALONEPAY",
    "SHARED2FREE", "SHARED2PAY",
    "SHARED3FREE", "SHARED3PAY",
}

def _normalize_mode(raw_mode):
    """Map ActivitySim trip_mode values to MATSim mode strings."""
    if pd.isna(raw_mode):
        return "other"
    raw = str(raw_mode).upper()
    if raw in _CAR_MODES or "DRIVE" in raw:
        return "car"
    if raw == "WALK":
        return "walk"
    if raw == "BIKE":
        return "bike"
    if any(k in raw for k in ("TRANSIT", "BUS", "RAIL", "LOC", "LRF", "EXP", "HVY", "COM")):
        return "pt"
    return "other"


def assign_facility_locations(trips_path, facilities_path, output_path):
    """
    Assign facility locations to trips based on purpose and TAZ zone.

    Expects facilities_cleaned.csv to contain a 'taz_id' column (OBJECTID from
    subdistricts_180.geojson).  Trips must contain 'origin' and 'destination'
    columns with TAZ IDs matching those OBJECTID values.

    Falls back to a city-wide random pick when no facility of the required type
    exists inside the target TAZ.
    """
    random.seed(42)

    # ==============================
    # LOAD DATA
    # ==============================
    try:
        trips = pd.read_csv(trips_path)
        facilities = pd.read_csv(facilities_path)
    except Exception as e:
        print(f"!!! Error loading data in assign_locations: {e}")
        return

    # ==============================
    # BUILD FACILITY LOOKUP TABLES
    # ==============================
    # Primary:  (activity_type, taz_id) → list of facility dicts
    # Fallback: activity_type           → list of facility dicts
    facility_groups = {}          # keyed by (activity_type, taz_id)
    facility_groups_by_type = {}  # keyed by activity_type (city-wide fallback)

    for _, fac in facilities.iterrows():
        atype = fac["activity_type"]
        record = {
            "osmid":         fac["osmid"],
            "name":          fac["name"],
            "activity_type": atype,
            "latitude":      fac["latitude"],
            "longitude":     fac["longitude"],
        }
        # City-wide fallback
        facility_groups_by_type.setdefault(atype, []).append(record)
        # TAZ-specific
        taz = fac.get("taz_id")
        if pd.notna(taz):
            key = (atype, int(taz))
            facility_groups.setdefault(key, []).append(record)

    def pick_facility(purpose, taz_id):
        """Pick a random facility matching purpose, preferring the given TAZ.
        Maps ActivitySim purpose strings to facility activity_type before lookup.
        """
        fac_type = _PURPOSE_MAP.get(purpose, purpose)  # fallback to raw value if not in map
        if taz_id is not None and not pd.isna(taz_id):
            subset = facility_groups.get((fac_type, int(taz_id)))
            if subset:
                return random.choice(subset)
        # Fallback: city-wide
        subset = facility_groups_by_type.get(fac_type)
        if subset:
            return random.choice(subset)
        print(f"  ⚠️  No facility found for purpose='{purpose}' (mapped='{fac_type}')")
        return None

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
    print(f"Assigning locations for {len(trips)} trip legs...")
    for row in tqdm(trips.itertuples(), total=len(trips)):
        person_id  = row.person_id
        purpose    = row.purpose
        origin_taz = getattr(row, "origin", None)
        dest_taz   = getattr(row, "destination", None)

        # -------- INITIALIZE PERSON --------
        if person_id not in current_location:
            fixed_facility[person_id] = {}
            home_fac = pick_facility("home", origin_taz)
            if home_fac is None:
                continue
            fixed_facility[person_id]["home"] = home_fac
            current_location[person_id] = home_fac

        # -------- ORIGIN (= previous destination) --------
        origin_fac = current_location[person_id]

        # -------- DESTINATION --------
        if purpose in fixed_purpose:
            if purpose not in fixed_facility[person_id]:
                fac = pick_facility(purpose, dest_taz)
                if fac is None:
                    continue
                fixed_facility[person_id][purpose] = fac
            dest_fac = fixed_facility[person_id][purpose]
        else:
            dest_fac = pick_facility(purpose, dest_taz)
            if dest_fac is None:
                continue

        current_location[person_id] = dest_fac

        # -------- MODE (handles both 'trip_mode' and legacy 'mode' column) --------
        raw_mode = getattr(row, "trip_mode", None) or getattr(row, "mode", None)
        mode = _normalize_mode(raw_mode)

        results.append({
            "person_id": person_id,
            "tour_id":   row.tour_id,
            "trip_id":   row.trip_id,
            "trip_num":  row.trip_num,
            "depart":    row.depart,
            "purpose":   purpose,
            "mode":      mode,
            # Origin
            "origin_osmid": origin_fac["osmid"],
            "origin_name":  origin_fac["name"],
            "origin_lat":   origin_fac["latitude"],
            "origin_lon":   origin_fac["longitude"],
            # Destination
            "dest_osmid": dest_fac["osmid"],
            "dest_name":  dest_fac["name"],
            "dest_lat":   dest_fac["latitude"],
            "dest_lon":   dest_fac["longitude"],
        })

    # ==============================
    # SAVE OUTPUT
    # ==============================
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values(["person_id", "tour_id", "trip_num"])
    result_df.to_csv(output_path, index=False)
    print(f"✅ Location assignment completed. Saved to: {output_path}")


if __name__ == "__main__":
    assign_facility_locations(
        "data/final_trips.csv",
        "output/facilities_cleaned.csv",
        "output/assigned_trips.csv"
    )
