import pandas as pd

df = pd.read_csv("output/output_activities.csv.gz", sep=";")

print("Columns:", df.columns.tolist())
print(df.head(3))