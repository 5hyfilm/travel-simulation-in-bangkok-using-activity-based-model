import random
import pandas as pd
from pyproj import Transformer
from lxml import etree
from tqdm import tqdm
import os

def generate_matsim_plans(input_file, output_file, sample_size=50000):
    """
    Generate MATSim XML plans from trip data (final_trips.csv)
    """
    RANDOM_SEED = 42

    if not os.path.exists(input_file):
        print(f"!!! Error: Input file {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} trips from {input_file}")
    print("Columns available:", df.columns.tolist())

    df = df.sort_values(["person_id", "tour_id", "trip_num"])

    # === แก้ปัญหา KeyError 'mode' ===
    if "mode" in df.columns:
        df = df[df["mode"] == "car"]
        print(f"Filtered to car mode only: {len(df)} trips")
    elif "trip_mode" in df.columns:
        df = df[df["trip_mode"] == "car"]
        print(f"Filtered using 'trip_mode' column: {len(df)} trips")
    else:
        print("Warning: No 'mode' or 'trip_mode' column found. Using ALL trips (no car filter)")

    # Sample persons
    random.seed(RANDOM_SEED)
    unique_persons = df["person_id"].unique()

    if sample_size is not None and sample_size != -1:
        if len(unique_persons) < sample_size:
            print(f"Warning: มีคนแค่ {len(unique_persons)} คน → ใช้ทั้งหมด")
            sample_size = len(unique_persons)
        selected_persons = set(random.sample(list(unique_persons), sample_size))
        print(f"Generating plans for {len(selected_persons)} persons (sampled)")
    else:
        selected_persons = set(unique_persons)
        print(f"Generating plans for ALL {len(selected_persons)} persons")

    df = df[df["person_id"].isin(selected_persons)]

    # Time formatter
    def to_hhmmss(t):
        total_sec = round(t * 60)
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # CRS: WGS84 → UTM Zone 47N (Bangkok)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True)

    # Build XML
    population = etree.Element("population")
    grouped = df.groupby("person_id")

    print(f"Creating MATSim plans for {len(grouped)} persons...")
    for person_id, person_trips in tqdm(grouped, total=len(grouped)):
        rows = person_trips.to_dict("records")

        person_elem = etree.SubElement(population, "person", id=str(person_id))
        plan_elem = etree.SubElement(person_elem, "plan", selected="yes")

        # First activity = home
        first = rows[0]
        x0, y0 = transformer.transform(first["origin_lon"], first["origin_lat"])
        etree.SubElement(plan_elem, "activity",
                        type="home",
                        x=f"{x0:.2f}",
                        y=f"{y0:.2f}",
                        end_time=to_hhmmss(first["depart"]))

        # Trips + activities
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

    # Save
    tree = etree.ElementTree(population)
    tree.write(output_file,
               pretty_print=True,
               xml_declaration=True,
               encoding="UTF-8",
               doctype='<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd">')

    print(f"✅ Success! Generated {output_file}")
    print(f"   Persons: {len(grouped)} | Total trips: {len(df)}")


if __name__ == "__main__":
    generate_matsim_plans(
        input_file="preprocess/output/final_trips.csv",           # หรือ "preprocess/output/final_trips.csv" ก็ได้
        output_file="preprocess/output/plan_50k.xml",
        sample_size=50000                                  # หรือใส่ -1 ถ้าอยากใช้ทั้งหมด
    )