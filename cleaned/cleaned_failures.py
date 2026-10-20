
from pathlib import Path
import pandas as pd


RAW_PATH = Path(__file__).resolve().parent.parent / "raw" / "fdic_failures.csv"


def clean_failures():
    # 1. Load raw data
    df = pd.read_csv(RAW_PATH, dtype="string", keep_default_na=False)

    # 2. Convert missing-value conventions to NULL
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df = df.replace(["NA", "N/A", "NULL"], pd.NA)

    # 3. Convert identifiers and numeric amounts
    for col in ["CERT", "FAILYR", "QBFASSET", "QBFDEP",
                "COST", "UNINSDEP", "FUND"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Convert dates
    for col in ["FAILDATE", "RESDATE"]:
        df[col] = pd.to_datetime(
            df[col], format="%m/%d/%Y", errors="coerce"
        )

    for col in ["COSTMOSTRECENTASOF", "PTRDATE", "BRDATE"]:
        df[col] = pd.to_datetime(
            df[col], format="%Y-%m-%d", errors="coerce"
        )

    return df


if __name__ == "__main__":
    df = clean_failures()

    print("\n--- Dataset Shape ---")
    print(df.shape)

    print("\n--- Cleaned Failure Examples ---")
    print(
        df[["CERT", "NAME", "FAILDATE", "RESDATE",
            "QBFASSET", "QBFDEP", "COST"]]
        .head(10)
        .to_string(index=False)
    )

    print("\n--- Data Types ---")
    print(df.dtypes)
