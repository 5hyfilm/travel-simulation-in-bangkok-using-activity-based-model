import pandas as pd
import os

DATA = r"C:\CP49\2025_2\CAPSTONE\progess\travel-simulation-in-bangkok-using-activity-based-model"

df = pd.read_csv(os.path.join(DATA, "pipeline", "data", "final_trips.csv"))

CAR_MODES = {"DRIVEALONEFREE","DRIVEALONEPAY","SHARED2FREE","SHARED2PAY","SHARED3FREE","SHARED3PAY"}
df["is_car"] = df["trip_mode"].str.upper().isin(CAR_MODES) | df["trip_mode"].str.upper().str.contains("DRIVE", na=False)
car = df[df["is_car"]]

print("=== Raw ActivitySim data ===")
print("Total persons       :", df["person_id"].nunique())
print("Persons with car    :", car["person_id"].nunique())
print("Total car trips     :", len(car))
print("Car trips/car-person:", round(len(car)/car["person_id"].nunique(), 2))
print()
print("Trips per car-person distribution:")
print(car.groupby("person_id").size().describe().round(2))

proc = os.path.join(DATA, "pipeline", "output", "final_trips.csv")
if os.path.exists(proc):
    df2 = pd.read_csv(proc)
    c2 = df2[df2["mode"] == "car"]
    print("\n=== Processed output/final_trips.csv ===")
    print("Total rows    :", len(df2))
    print("Total persons :", df2["person_id"].nunique())
    print("Car trips     :", len(c2))
    print("Car persons   :", c2["person_id"].nunique())
else:
    print("\nProcessed final_trips.csv not found at:", proc)
