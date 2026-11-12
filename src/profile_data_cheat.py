
# Explore the raw FDIC institutions dataset before cleaning.
import json
from pathlib import Path
import pandas as pd

# Locate the raw JSON dataset.
raw_path = Path("../raw/fdic_institutions.json")

# Load the JSON file into a Python object.
with open(raw_path, "r", encoding="utf-8") as file:
    institutions = json.load(file)

# Inspect the number of records and the original JSON structure.
print("Total records:", len(institutions))
print("First record:", institutions[0])


# Extract the nested institution data from each JSON record.
records = []

for institution in institutions:
    records.append(institution["data"])

print("Extracted records:", len(records))
print("First extracted record:", records[0])


# Convert the extracted records into a pandas DataFrame.
df = pd.DataFrame(records)

# Examine dataset dimensions, column names, and data types.
print("Shape:", df.shape)
print("\nColumns:", df.columns.tolist())
print("\nData types:")
print(df.dtypes)

# Count missing values in every column.
print("\nMissing values by column:")
print(df.isna().sum())


# Filter institutions with missing asset values.
missing_rows = df[df["ASSET"].isna()]

# Inspect whether missing assets are associated with inactive banks.
print(missing_rows[["NAME", "ACTIVE", "NAMEHCR", "ASSET", "DEP"]].head(10))


# Group by ACTIVE status and count missing assets within each group.
# apply() runs the lambda function separately for each group.
print(df.groupby("ACTIVE")["ASSET"].apply(lambda x: x.isna().sum()))


# Check whether any active institutions are missing asset values.
# & combines two conditions; both must be True.
active_missing = df[
    (df["ACTIVE"] == 1) &
    (df["ASSET"].isna())
]

print(active_missing[["CERT", "NAME", "ACTIVE", "ASSET", "DEP"]])


# Validate the expected grain: one record per FDIC certificate.
# nunique() counts unique CERT values; duplicated() identifies repeats.
print("Total rows:", len(df))
print("Unique CERT values:", df["CERT"].nunique())
print("Duplicate CERT values:", df["CERT"].duplicated().sum())


# Validate institution establishment and end dates.
print("\n--- Date Validation ---")

for col in ["ESTYMD", "ENDEFYMD"]:

    # Convert strings to dates; errors="coerce" turns invalid dates into NaT.
    parsed_dates = pd.to_datetime(df[col], errors="coerce")

    print(f"\n{col}")
    print("Invalid or missing dates:", parsed_dates.isna().sum())
    print("Earliest date:", parsed_dates.min())
    print("Latest date:", parsed_dates.max())


# Inspect common raw date values to identify patterns or placeholders.
print("\n--- Raw Date Samples ---")

for col in ["ESTYMD", "ENDEFYMD"]:
    print(f"\n{col}")

    # value_counts() shows the most frequent dates.
    print(df[col].value_counts().head(10))


# Investigate the 12/31/9999 placeholder used for institution end dates.
print("\n--- End Date Placeholder ---")

print("9999 dates:", (df["ENDEFYMD"] == "12/31/9999").sum())

# Determine how often this placeholder occurs by ACTIVE status.
print(
    df.groupby("ACTIVE")["ENDEFYMD"]
    .apply(lambda x: (x == "12/31/9999").sum())
)


# Inspect a specific institution with a missing charter classification.
print(df[df["CERT"] == 15656][["CERT", "NAME", "BKCLASS"]])


# Identify blank strings that isna() would not detect.
print("\n--- Blank String Check ---")

# Check only text columns.
for col in df.select_dtypes(include=["str", "object"]).columns:

    # Replace NULLs with empty strings, strip whitespace, then count blanks.
    # This count includes both original NULLs and blank strings.
    blank_count = df[col].fillna("").str.strip().eq("").sum()
    print(f"{col}: {blank_count}")


# Validate that ACTIVE contains only the expected binary values.
print("\n--- ACTIVE Validation ---")

# Include missing values in the frequency count.
print(df["ACTIVE"].value_counts(dropna=False))

# ~ negates isin(), identifying values other than 0 or 1.
print(
    "Unexpected ACTIVE values:",
    (~df["ACTIVE"].isin([0, 1])).sum()
)


# Check asset and deposit values for missing, negative, or zero amounts.
print("\n--- Numeric Validation ---")

for col in ["ASSET", "DEP"]:
    print(f"\n{col}")
    print("Missing:", df[col].isna().sum())
    print("Negative:", (df[col] < 0).sum())
    print("Zero:", (df[col] == 0).sum())

    # Inspect the range to identify potentially unusual values.
    print("Minimum:", df[col].min())
    print("Maximum:", df[col].max())
