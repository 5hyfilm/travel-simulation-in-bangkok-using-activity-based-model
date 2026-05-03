import pandas as pd, os

for p in ["pipeline/data/final_trips.csv", "data/final_trips.csv",
          "pipeline/output/final_trips.csv"]:
    if os.path.exists(p):
        df = pd.read_csv(p, nrows=30)
        print(f"=== {p} ===")
        print("Columns:", list(df.columns))
        p1 = df[df["person_id"] == df["person_id"].iloc[0]]
        print(p1.to_string())
        print()
        break
