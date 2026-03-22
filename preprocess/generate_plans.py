import random
import pandas as pd
from pyproj import Transformer
from lxml import etree
from tqdm import tqdm
import os

def generate_matsim_plans(input_file, output_file, sample_size=50000):
    """
    Generate MATSim XML plans from trip data.
    """
    RANDOM_SEED = 42

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
    # SAMPLE PERSONS
    # ==============================
    random.seed(RANDOM_SEED)
    unique_persons = df["person_id"].unique()
    selected_persons = set(unique_persons)
    if sample_size is not None and sample_size != -1:
        if len(unique_persons) < sample_size:
            print(f"Warning: มีคนแค่ {len(unique_persons)} คนในไฟล์ทริป")
            sample_size = len(unique_persons)
        selected_persons = set(random.sample(list(unique_persons), sample_size))
        print(f"Generating CAR-only plan for {len(selected_persons)} persons (Sample)...")
    else:
        print(f"Generating CAR-only plan for ALL {len(selected_persons)} persons...")
    
    df = df[df["person_id"].isin(selected_persons)]

    # ==============================
    # TIME FORMATTER
    # ==============================
    def to_hhmmss(t):
        total_sec = round(t * 60)
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
            attrs = {
                "type": str(row["purpose"]),
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
