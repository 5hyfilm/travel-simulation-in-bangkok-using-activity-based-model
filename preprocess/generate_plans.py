import random
import pandas as pd
from pyproj import Transformer
from lxml import etree
from tqdm import tqdm

# ==============================
# SETTINGS
# ==============================
INPUT_FILE = "final_trips.csv"
OUTPUT_FILE = "plan_50k.xml"
SAMPLE_SIZE = 50000
RANDOM_SEED = 42

# ==============================
# LOAD DATA
# ==============================
df = pd.read_csv(INPUT_FILE)
df = df.sort_values(["person_id", "tour_id", "trip_num"])

# ==============================
# FILTER CAR MODE ONLY
# ==============================
df = df[df["mode"] == "car"]

# ==============================
# SAMPLE 50,000 PERSONS
# ==============================
random.seed(RANDOM_SEED)
unique_persons = df["person_id"].unique()
if len(unique_persons) < SAMPLE_SIZE:
    print(f"Warning: มีคนแค่ {len(unique_persons)} คน")
    SAMPLE_SIZE = len(unique_persons)
selected_persons = set(random.sample(list(unique_persons), SAMPLE_SIZE))
df = df[df["person_id"].isin(selected_persons)]
print(f"Generating CAR-only plan for {len(selected_persons)} persons...")

# ==============================
# TIME FORMATTER
# ==============================
def to_hhmmss(t):
    total_sec = round(t * 60)  # float minutes → seconds (rounded)
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
tree.write(OUTPUT_FILE, pretty_print=True, xml_declaration=True, encoding="UTF-8")
print(f"{OUTPUT_FILE} generated successfully.")
