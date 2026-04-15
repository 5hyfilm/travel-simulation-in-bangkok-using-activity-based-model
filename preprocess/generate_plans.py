import random
import pandas as pd
from pyproj import Transformer
from lxml import etree
from tqdm import tqdm
import os

def generate_matsim_plans(input_file, output_file, sample_size=50000, bbox=None):
    """
    Generate MATSim XML plans from trip data.
    - sample_size: Total agents target (will clone if original data is less)
    - bbox: (north, south, east, west)
    """
    RANDOM_SEED = 42
    random.seed(RANDOM_SEED)

    # ActivitySim purpose → MATSim activity type
    PURPOSE_TO_ACTTYPE = {
        "home":     "home",
        "work":     "work",
        "atwork":   "work",
        "school":   "education",
        "univ":     "education",
        "shopping": "shopping",
        "eatout":   "dining",
        "social":   "leisure",
        "othdiscr": "leisure",
        "escort":   "home",
        "othmaint": "other",
    }

    # ==============================
    # LOAD DATA
    # ==============================
    if not os.path.exists(input_file):
        print(f"!!! Error: Input file {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    df = df.sort_values(["person_id", "tour_id", "trip_num"])

    # ==============================
    # FILTER CAR MODE ONLY
    # ==============================
    df = df[df["mode"] == "car"]

    # ==============================
    # BBOX FILTER (INNER BANGKOK)
    # ==============================
    if bbox is not None:
        north, south, east, west = bbox
        # Keep only people who have at least ONE trip activity inside the CBD box
        in_bbox = df[
            ((df["origin_lat"] <= north) & (df["origin_lat"] >= south) & 
             (df["origin_lon"] <= east) & (df["origin_lon"] >= west)) |
            ((df["dest_lat"] <= north) & (df["dest_lat"] >= south) & 
             (df["dest_lon"] <= east) & (df["dest_lon"] >= west))
        ]
        cbd_persons = in_bbox["person_id"].unique()
        df = df[df["person_id"].isin(cbd_persons)]
        print(f"Filtered to {len(cbd_persons)} persons touching the CBD area.")
    
    # ==============================
    # SAMPLE OR UPSCALE (CLONE)
    # ==============================
    unique_persons = df["person_id"].unique()
    
    if sample_size is not None and sample_size != -1:
        if len(unique_persons) < sample_size:
            # --- UPSCALING (CLONE) ---
            needed = sample_size - len(unique_persons)
            print(f"Upscaling: Cloning {needed} agents to reach target of {sample_size}...")
            
            # Draw random samples from unique persons to clone
            clones_to_make = random.choices(unique_persons, k=needed)
            
            # We will create a list of dataframes to concat later
            upscaled_dfs = [df]
            
            # Group by person to make duplication easier
            grouped = df.groupby("person_id")
            
            # Simple clone counter
            clone_id_map = {} # person_id -> count
            
            for pid in tqdm(clones_to_make, desc="Cloning agents"):
                clone_df = grouped.get_group(pid).copy()
                
                # Assign new ID
                clone_id_map[pid] = clone_id_map.get(pid, 0) + 1
                new_id = f"{pid}_clone{clone_id_map[pid]}"
                clone_df["person_id"] = new_id
                
                # Apply random jitter to departure time (+/- 10 mins = 0.16 hours)
                jitter = random.uniform(-0.16, 0.16)
                clone_df["depart"] = clone_df["depart"] + jitter
                
                upscaled_dfs.append(clone_df)
                
            df = pd.concat(upscaled_dfs)
        else:
            # --- DOWN-SAMPLING ---
            selected_persons = random.sample(list(unique_persons), sample_size)
            df = df[df["person_id"].isin(selected_persons)]
            print(f"Sampling: Selected {sample_size} agents out of {len(unique_persons)}.")
    
    print(f"Final plan generation for {df['person_id'].nunique()} agents...")

    # ==============================
    # TIME FORMATTER
    # ==============================
    def to_hhmmss(t):
        # depart is in hours (e.g. 7 = 07:00, 18 = 18:00)
        total_sec = round(t * 3600)
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ==============================
    # CRS TRANSFORM (Bangkok UTM 47N)
    # ==============================
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True)

    # ==============================
    # CREATE XML
    # ==============================
    population = etree.Element("population")
    grouped = df.groupby("person_id")

    for person_id, person_trips in tqdm(grouped, total=df["person_id"].nunique()):
        rows = person_trips.to_dict("records")

        person_elem = etree.SubElement(population, "person", id=str(person_id))
        plan_elem = etree.SubElement(person_elem, "plan", selected="yes")

        # ---------- FIRST ACTIVITY ----------
        first = rows[0]
        x0, y0 = transformer.transform(first["origin_lon"], first["origin_lat"])
        etree.SubElement(
            plan_elem,
            "activity",
            type="home",
            x=f"{x0:.2f}",
            y=f"{y0:.2f}",
            end_time=to_hhmmss(first["depart"]),
        )

        # ---------- CAR TRIPS ----------
        for i, row in enumerate(rows):
            etree.SubElement(plan_elem, "leg", mode="car")
            x, y = transformer.transform(row["dest_lon"], row["dest_lat"])
            act_type = PURPOSE_TO_ACTTYPE.get(str(row["purpose"]), "other")
            attrs = {
                "type": act_type,
                "x": f"{x:.2f}",
                "y": f"{y:.2f}",
            }
            if i < len(rows) - 1:
                attrs["end_time"] = to_hhmmss(rows[i + 1]["depart"])
            etree.SubElement(plan_elem, "activity", **attrs)

    # ==============================
    # SAVE FILE
    # ==============================
    tree = etree.ElementTree(population)
    tree.write(
        output_file, 
        pretty_print=True, 
        xml_declaration=True, 
        encoding="UTF-8", 
        doctype='<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd">'
    )
    print(f"✅ {output_file} generated successfully.")

if __name__ == "__main__":
    generate_matsim_plans("final_trips.csv", "plan_50k.xml", SAMPLE_SIZE=50000)
