#import json loads Python’s built‑in JSON module, which lets you convert between JSON text and Python objects using  certain functions
import json
from pathlib import Path
import pandas as pd


# Load and clean FDIC institution records.
def clean_institutions():

    # 1. Locate and load the raw JSON file.
    raw_path = Path(__file__).resolve().parent.parent / "raw" / "fdic_institutions.json"
# Open the raw JSON file in read mode using UTF-8 encoding.
# The "with" statement automatically closes the file when finished.
    with open(raw_path, "r", encoding="utf-8") as file:
        # Parse the JSON contents into a Python object
        # (usually a dictionary or list).
        institutions = json.load(file)

    # Each institution is nested inside a "data" dictionary.
    # List comprehension extracts that dictionary from every record.
    # Pandas then converts the list of dictionaries into a DataFrame.
    df = pd.DataFrame([institution["data"] for institution in institutions])

    # 2. Convert CERT (bank identifier) to a nullable integer.
    # Invalid values become missing rather than causing an error.
    df["CERT"] = pd.to_numeric(df["CERT"], errors="coerce").astype("Int64")

    # 3. Convert ACTIVE from 0/1 into False/True.
    # Nullable boolean also supports missing or unexpected values.
    df["ACTIVE"] = df["ACTIVE"].map({0: False, 1: True}).astype("boolean")

    # 4. Replace the placeholder end date with NULL.
    # 12/31/9999 represents an unspecified end date, not an actual closure.
    df["ENDEFYMD"] = df["ENDEFYMD"].replace("12/31/9999", pd.NA)

    # Convert establishment and end dates from strings to datetime.
    # errors="coerce" turns invalid dates into NaT.
    for col in ["ESTYMD", "ENDEFYMD"]:
        df[col] = pd.to_datetime(df[col], format="%m/%d/%Y", errors="coerce")

    # 5. Standardize missing holding-company names.
    # The regex matches empty strings and whitespace-only values.
    # This prevents blank names from being treated as actual companies.
    df["NAMEHCR"] = df["NAMEHCR"].replace(r"^\s*$", pd.NA, regex=True)

    # Return the cleaned DataFrame for warehouse loading.
    return df


# Run these checks only when executing this file directly,
# not when importing clean_institutions() into another script.
if __name__ == "__main__":

    df = clean_institutions()

    # Preview the most important cleaned fields.
    print(df[["CERT", "ACTIVE", "ESTYMD", "ENDEFYMD", "NAMEHCR"]].head())

    # Confirm the number of rows and columns.
    print("\nShape:", df.shape)
