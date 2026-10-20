
import pandas as pd
from pathlib import Path


# 1. Load and clean the four FRED datasets
def clean_macro():

    # Find the raw data folder
    raw_path = Path(__file__).resolve().parent.parent / "raw"

    # List the four economic indicators
    series = [
        "DGS10",
        "FEDFUNDS",
        "MORTGAGE30US",
        "UNRATE"
    ]

    cleaned_series = []

    # 2. Read each CSV file
    for name in series:

        file_path = raw_path / f"fred_{name}.csv"

        df = pd.read_csv(file_path)

        # Convert observation dates to datetime
        df["observation_date"] = pd.to_datetime(
            df["observation_date"],
            errors="coerce"
        )

        # Convert interest rates and unemployment to numeric values
        # Invalid values become NULL (NaN)
        df[name] = pd.to_numeric(
            df[name],
            errors="coerce"
        )

        # 3. Remove rows with invalid dates
        df = df.dropna(subset=["observation_date"])

        # Keep only the financial reporting period
        df = df[
            (df["observation_date"] >= "2006-01-01")
            & (df["observation_date"] <= "2026-06-30")
        ].copy()

        # 4. Assign each observation to its quarter-end date
        df["quarter_end"] = (
            df["observation_date"]
            .dt.to_period("Q")
            .dt.to_timestamp(how="end")
            .dt.normalize()
        )

        # 5. Calculate the quarterly average
        quarterly = (
            df.groupby("quarter_end")[name]
            .mean()
            .reset_index()
        )

        cleaned_series.append(quarterly)

    # 6. Create all quarter-end dates in the reporting period
    quarters = pd.DataFrame({
        "quarter_end": pd.date_range(
            start="2006-03-31",
            end="2026-06-30",
            freq="QE-DEC"
        )
    })

    # 7. Combine the four economic indicators
    macro = quarters.copy()

    for quarterly in cleaned_series:

        macro = macro.merge(
            quarterly,
            on="quarter_end",
            how="left"
        )

    # 8. Round values to two decimal places
    for name in series:
        macro[name] = macro[name].round(2)

    # 9. Sort by quarter and reset the index
    macro = (
        macro.sort_values("quarter_end")
        .reset_index(drop=True)
    )

    return macro


if __name__ == "__main__":

    # 10. Run the cleaning function
    macro = clean_macro()

    # 11. Display the cleaned data
    print("\n--- Cleaned Macro Shape ---")
    print(macro.shape)

    print("\n--- First 5 Rows ---")
    print(macro.head())

    print("\n--- Last 5 Rows ---")
    print(macro.tail())

    # 12. Check data types
    print("\n--- Data Types ---")
    print(macro.dtypes)

    # 13. Check missing values
    print("\n--- Missing Values ---")
    print(macro.isna().sum())

    # 14. Check for duplicate quarters
    print("\n--- Duplicate Quarters ---")
    print(macro["quarter_end"].duplicated().sum())

    # 15. Verify the date range
    print("\n--- Date Range ---")
    print("Earliest:", macro["quarter_end"].min())
    print("Latest:", macro["quarter_end"].max())

    # 16. Display summary statistics
    print("\n--- Summary Statistics ---")
    print(macro.describe())
