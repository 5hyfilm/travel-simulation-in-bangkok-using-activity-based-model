import pandas as pd

df = pd.read_csv("pipeline/data/final_trips.csv")

car_modes = ["DRIVEALONEFREE", "DRIVEALONEPAY", "SHARED2FREE", "SHARED2PAY", "SHARED3FREE", "SHARED3PAY"]
df_car = df[df["trip_mode"].isin(car_modes)]

total = len(df_car)
total_agents = df_car["person_id"].nunique()

print(f"=== Input car trip distribution (ทีละ 1 ชม.) ===")
print(f"Total car trips : {total:,}")
print(f"Total agents    : {total_agents:,}\n")

for h in range(0, 30):
    count = len(df_car[df_car["depart"] == h])
    agents = df_car[df_car["depart"] == h]["person_id"].nunique()
    bar = "█" * int(count/total*300)
    print(f"  {h:02d}:00  trips={count:>6,} ({count/total*100:4.1f}%)  agents={agents:>5,}  {bar}")