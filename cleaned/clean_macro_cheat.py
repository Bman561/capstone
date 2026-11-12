
import pandas as pd
from pathlib import Path


# Cleans four FRED (Federal Reserve Economic Data) datasets and
# combines them into one DataFrame with one row per quarter.
def clean_macro():

    # __file__ is the location of this Python script.
    # resolve() gets its absolute path.
    # parent.parent moves up two directory levels to the project root.
    # / "raw" points to the folder containing our original CSV files.
    raw_path = Path(__file__).resolve().parent.parent / "raw"

    # These are the four economic indicators we want to analyze:
    # DGS10: 10-year Treasury yield
    # FEDFUNDS: Federal funds interest rate
    # MORTGAGE30US: 30-year fixed mortgage rate
    # UNRATE: Unemployment rate
    #
    # Each name corresponds to a CSV file and a column in that file.
    series = [
        "DGS10",
        "FEDFUNDS",
        "MORTGAGE30US",
        "UNRATE"
    ]

    # Stores the cleaned quarterly DataFrame for each indicator.
    # By the end of the loop, this list will contain four DataFrames.
    cleaned_series = []

    # Loop through each economic indicator and clean its CSV file.
    for name in series:

        # f-string inserts the current indicator name into the filename.
        # Example: name = "DGS10" -> raw/fred_DGS10.csv
        file_path = raw_path / f"fred_{name}.csv"

        # Load the current CSV into a pandas DataFrame.
        df = pd.read_csv(file_path)

        # Convert the observation_date column from text to datetime.
        # errors="coerce" replaces unparseable dates with NaT
        # (Not a Time), allowing us to identify and remove them.
        df["observation_date"] = pd.to_datetime(
            df["observation_date"],
            errors="coerce"
        )

        # Convert the current indicator column into numeric values.
        # FRED data can contain nonnumeric placeholders such as ".".
        # errors="coerce" converts these to NaN instead of crashing.
        # NaN represents a missing numeric value, not zero.
        df[name] = pd.to_numeric(
            df[name],
            errors="coerce"
        )

        # Remove observations whose dates could not be parsed.
        # We keep rows with missing indicator values for now because
        # pandas mean() will ignore NaN when calculating averages.
        df = df.dropna(subset=["observation_date"])

        # Restrict observations to our project's reporting period.
        # The & operator means BOTH conditions must be true.
        # .copy() creates an independent DataFrame from the filtered rows.
        df = df[
            (df["observation_date"] >= "2006-01-01")
            & (df["observation_date"] <= "2026-06-30")
        ].copy()

        # Convert each observation date into its calendar quarter-end.
        #
        # Example: 2023-02-15 becomes 2023-03-31.
        #
        # .dt.to_period("Q") identifies the quarter containing the date.
        # .dt.to_timestamp(how="end") gets the final instant of that quarter.
        # .dt.normalize() resets the time to midnight, leaving the date.
        #
        # This creates a common quarter_end field that we can use
        # to combine daily, weekly, and monthly economic observations.
        df["quarter_end"] = (
            df["observation_date"]
            .dt.to_period("Q")
            .dt.to_timestamp(how="end")
            .dt.normalize()
        )

        # Group all observations belonging to the same quarter.
        #
        # [name] selects the indicator being processed.
        # .mean() calculates its average value for each quarter.
        # .reset_index() turns quarter_end back into a regular column.
        #
        # Example:
        # 2023-01-01 -> 4.0
        # 2023-02-01 -> 4.5
        # 2023-03-01 -> 5.0
        # Quarterly average -> 4.5
        quarterly = (
            df.groupby("quarter_end")[name]
            .mean()
            .reset_index()
        )

        # Save this indicator's quarterly results.
        # After four iterations, we have four separate quarterly tables.
        cleaned_series.append(quarterly)

    # Create a master calendar containing every quarter-end date
    # between March 2006 and June 2026.
    #
    # QE-DEC means calendar quarters ending in March, June,
    # September, and December.
    #
    # This ensures every expected quarter exists in the final
    # dataset, even if an indicator is missing observations.
    quarters = pd.DataFrame({
        "quarter_end": pd.date_range(
            start="2006-03-31",
            end="2026-06-30",
            freq="QE-DEC"
        )
    })

    # Start with the master calendar as the foundation.
    # .copy() ensures macro is a separate DataFrame.
    macro = quarters.copy()

    # Merge each cleaned indicator into the master calendar.
    for quarterly in cleaned_series:

        # on="quarter_end" matches records with the same quarter.
        #
        # how="left" keeps ALL quarters from the master calendar,
        # even when the current indicator has no data for a quarter.
        #
        # Example:
        # Before: quarter_end
        # After first merge: quarter_end, DGS10
        # After second merge: quarter_end, DGS10, FEDFUNDS
        # Eventually all four indicators appear in one DataFrame.
        macro = macro.merge(
            quarterly,
            on="quarter_end",
            how="left"
        )

    # Round the four economic indicators to two decimal places.
    # This improves consistency and readability for reporting.
    for name in series:
        macro[name] = macro[name].round(2)

    # Sort the completed dataset chronologically.
    # reset_index(drop=True) replaces the old index with 0, 1, 2...
    # without adding the old index as another column.
    macro = (
        macro.sort_values("quarter_end")
        .reset_index(drop=True)
    )

    # Return the cleaned DataFrame so other scripts can reuse it.
    return macro


# This block runs ONLY when this file is executed directly.
# It does not run when another script imports clean_macro().
#
# This allows us to reuse the cleaning function in our pipeline
# without automatically printing all the validation results.
if __name__ == "__main__":

    # Call the function and store its returned DataFrame.
    macro = clean_macro()

    # Check the number of rows and columns.
    # Expected: one row per quarter and five columns
    # (quarter_end plus the four economic indicators).
    print("\n--- Cleaned Macro Shape ---")
    print(macro.shape)

    # Preview the first and last five rows to inspect the data.
    print("\n--- First 5 Rows ---")
    print(macro.head())

    print("\n--- Last 5 Rows ---")
    print(macro.tail())

    # Confirm quarter_end is datetime and indicators are numeric.
    print("\n--- Data Types ---")
    print(macro.dtypes)

    # Count missing values in each column.
    # Missing indicator values may indicate unavailable observations.
    print("\n--- Missing Values ---")
    print(macro.isna().sum())

    # Each quarter should appear exactly once.
    # A result of 0 confirms there are no duplicate quarter_end values.
    print("\n--- Duplicate Quarters ---")
    print(macro["quarter_end"].duplicated().sum())

    # Verify that the final dataset covers the expected period.
    print("\n--- Date Range ---")
    print("Earliest:", macro["quarter_end"].min())
    print("Latest:", macro["quarter_end"].max())

    # Display descriptive statistics for the numeric columns.
    # Includes count, mean, standard deviation, min, max,
    # and the 25th, 50th, and 75th percentiles.
    print("\n--- Summary Statistics ---")
    print(macro.describe())





