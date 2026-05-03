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
    # DOWNSAMPLE IF NEEDED
    # Cloning is handled upstream in assign_locations.py, so the input already
    # contains the target number of agents with independently assigned locations.
    # ==============================
    unique_persons = df["person_id"].unique()

    if sample_size is not None and sample_size != -1 and len(unique_persons) > sample_size:
        selected_persons = random.sample(list(unique_persons), sample_size)
        df = df[df["person_id"].isin(selected_persons)]
        print(f"Downsampled to {sample_size:,} agents from {len(unique_persons):,}.")

    print(f"Final plan generation for {df['person_id'].nunique():,} agents...")

    # ==============================
    # TIME FORMATTER
    # ==============================
    def to_hhmmss(t):
        # depart is in hours (e.g. 7 = 07:00, 18 = 18:00)
        # Adding a random jitter of up to +/- 30 minutes (distributed by seconds)
        # This is MUCH faster for MATSim to process than minute-level clumping.
        jitter_seconds = random.randint(-1800, 1800)
        
        total_sec = round(t * 3600) + jitter_seconds
        
        # Ensure time doesn't go negative or beyond 24h
        total_sec = max(0, min(86399, total_sec))
        
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
    generate_matsim_plans("pipeline/output/final_trips.csv", "pipeline/output/plan_300k.xml", sample_size=300000)
