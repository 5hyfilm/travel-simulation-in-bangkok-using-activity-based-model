import pandas as pd

df = pd.read_csv("output/output_legs.csv.gz", sep=";", low_memory=False)

def to_hours(t):
    try:
        h, m, s = str(t).split(":")
        return int(h) + int(m)/60 + int(s)/3600
    except:
        return None

df["dep_hour_float"] = df["dep_time"].apply(to_hours)
df["dep_hour"] = df["dep_hour_float"].apply(lambda x: int(x) if x is not None else None)
total = len(df)

print(f"=== Output legs distribution (simulation) ===")
print(f"Total legs: {total:,}\n")

for h in range(0, 30):
    count = len(df[df["dep_hour"] == h])
    agents = df[df["dep_hour"] == h]["person"].nunique()
    bar = "█" * int(count/total*300)
    print(f"  {h:02d}:00  trips={count:>7,} ({count/total*100:4.1f}%)  agents={agents:>6,}  {bar}")