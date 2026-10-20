#Profiling to browse over our dataset, see what we're working with.
import json
from pathlib import Path
import pandas as pd
# Locate the raw dataset
raw_path = Path("../raw/fdic_institutions.json")

# Load the JSON file
with open(raw_path, "r", encoding="utf-8") as file:
    institutions = json.load(file)

print("Total records:", len(institutions))
print("First record:", institutions[0])



# Extract the nested institution records from the JSON
records = []

for institution in institutions:
    records.append(institution["data"])

print("Extracted records:", len(records))
print("First extracted record:", records[0])


df = pd.DataFrame(records)
print("Shape:", df.shape)
print("\nColumns:", df.columns.tolist())
print("\nData types:")
print(df.dtypes)

print("\nMissing values by column:")
print(df.isna().sum())


missing_rows = df[df["ASSET"].isna()]

print(missing_rows[["NAME", "ACTIVE", "NAMEHCR", "ASSET", "DEP"]].head(10))


print(df.groupby("ACTIVE")["ASSET"].apply(lambda x: x.isna().sum()))

active_missing = df[
    (df["ACTIVE"] == 1) &
    (df["ASSET"].isna())
]

print(active_missing[["CERT", "NAME", "ACTIVE", "ASSET", "DEP"]])

# Since One row per cert in intructions check if any  duplicates. (No dupes)

print("Total rows:", len(df))
print("Unique CERT values:", df["CERT"].nunique())
print("Duplicate CERT values:", df["CERT"].duplicated().sum())


print("\n--- Date Validation ---")

for col in ["ESTYMD", "ENDEFYMD"]:
    parsed_dates = pd.to_datetime(df[col], errors="coerce")

    print(f"\n{col}")
    print("Invalid or missing dates:", parsed_dates.isna().sum())
    print("Earliest date:", parsed_dates.min())
    print("Latest date:", parsed_dates.max())

print("\n--- Raw Date Samples ---")

for col in ["ESTYMD", "ENDEFYMD"]:
    print(f"\n{col}")
    print(df[col].value_counts().head(10))

print("\n--- End Date Placeholder ---")

print("9999 dates:", (df["ENDEFYMD"] == "12/31/9999").sum())

print(
    df.groupby("ACTIVE")["ENDEFYMD"]
    .apply(lambda x: (x == "12/31/9999").sum())
)


print(df[df["CERT"] == 15656][["CERT", "NAME", "BKCLASS"]])


print("\n--- Blank String Check ---")

for col in df.select_dtypes(include=["str", "object"]).columns:
    blank_count = df[col].fillna("").str.strip().eq("").sum()
    print(f"{col}: {blank_count}")


print("\n--- ACTIVE Validation ---")

print(df["ACTIVE"].value_counts(dropna=False))

print(
    "Unexpected ACTIVE values:",
    (~df["ACTIVE"].isin([0, 1])).sum()
)


print("\n--- Numeric Validation ---")

for col in ["ASSET", "DEP"]:
    print(f"\n{col}")
    print("Missing:", df[col].isna().sum())
    print("Negative:", (df[col] < 0).sum())
    print("Zero:", (df[col] == 0).sum())
    print("Minimum:", df[col].min())
    print("Maximum:", df[col].max())