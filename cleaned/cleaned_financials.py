
from pathlib import Path
import pandas as pd


RAW_PATH = Path(__file__).resolve().parent.parent / "raw" / "fdic_financials.csv"

YTD_COLUMNS = ["NETINC", "INTINC", "EINTEXP", "NONII", "NONIX", "ELNATR"]


def clean_financials():
    # 1. Load raw data
    df = pd.read_csv(RAW_PATH, dtype="string")

    # 2. Convert identifiers and dates
    df["CERT"] = pd.to_numeric(df["CERT"], errors="coerce").astype("Int64")
    df["REPDTE"] = pd.to_datetime(df["REPDTE"], format="%Y%m%d", errors="coerce")

    # 3. Convert financial columns to numeric
    numeric_columns = [col for col in df.columns if col not in ["CERT", "REPDTE", "ID"]]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Organize records by bank and quarter
    df = df.sort_values(["CERT", "REPDTE"]).reset_index(drop=True)

    df["YEAR"] = df["REPDTE"].dt.year
    df["QUARTER"] = df["REPDTE"].dt.quarter

    quarter_number = df["YEAR"] * 4 + df["QUARTER"]
    previous_quarter = quarter_number.groupby(df["CERT"]).shift(1)

    consecutive = (quarter_number - previous_quarter == 1).fillna(False)

    # 5. Convert year-to-date income to quarterly income (Appendix B)
    for col in YTD_COLUMNS:
        previous_ytd = df.groupby("CERT")[col].shift(1)

        quarterly_col = f"{col}_Q"

        df[quarterly_col] = df[col].where(
            df["QUARTER"] == 1,
            (df[col] - previous_ytd).where(consecutive)
        )

    return df


if __name__ == "__main__":
    df = clean_financials()

    print(df[["CERT", "REPDTE", "NETINC", "NETINC_Q"]].head(12))
    print("\nShape:", df.shape)
