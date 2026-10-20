
import json
from pathlib import Path
import pandas as pd


def clean_institutions():
    # 1. Load raw data
    raw_path = Path(__file__).resolve().parent.parent / "raw" / "fdic_institutions.json"

    with open(raw_path, "r", encoding="utf-8") as file:
        institutions = json.load(file)

    df = pd.DataFrame([institution["data"] for institution in institutions])

    # 2. Convert CERT to integer
    df["CERT"] = pd.to_numeric(df["CERT"], errors="coerce").astype("Int64")

    # 3. Convert ACTIVE to boolean
    df["ACTIVE"] = df["ACTIVE"].map({0: False, 1: True}).astype("boolean")

    # 4. Convert dates
    df["ENDEFYMD"] = df["ENDEFYMD"].replace("12/31/9999", pd.NA)

    for col in ["ESTYMD", "ENDEFYMD"]:
        df[col] = pd.to_datetime(df[col], format="%m/%d/%Y", errors="coerce")

    # 5. Normalize missing holding-company names
    df["NAMEHCR"] = df["NAMEHCR"].replace(r"^\s*$", pd.NA, regex=True)

    return df


if __name__ == "__main__":
    df = clean_institutions()
    print(df[["CERT", "ACTIVE", "ESTYMD", "ENDEFYMD", "NAMEHCR"]].head())
    print("\nShape:", df.shape)
