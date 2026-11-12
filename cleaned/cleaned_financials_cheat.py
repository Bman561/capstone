
from pathlib import Path
import pandas as pd


# Locate the raw FDIC financials dataset.
#
# __file__ refers to this Python script.
# .resolve() gets its absolute path.
# .parent.parent moves up two folders to the project root.
# We then navigate into the raw folder to find the CSV.
RAW_PATH = Path(__file__).resolve().parent.parent / "raw" / "fdic_financials.csv"


# These financial fields contain YEAR-TO-DATE (YTD) values.
#
# YTD means the reported amount accumulates from the beginning
# of the calendar year rather than representing only one quarter.
#
# NETINC  = Net income
# INTINC  = Interest income
# EINTEXP = Interest expense
# NONII   = Noninterest income
# NONIX   = Noninterest expense
# ELNATR  = Provision for loan and lease losses
#
# We need to convert these into individual quarterly amounts
# so financial performance can be compared quarter by quarter.
YTD_COLUMNS = ["NETINC", "INTINC", "EINTEXP", "NONII", "NONIX", "ELNATR"]


# Clean the FDIC financial dataset and calculate quarterly
# income values from the original year-to-date figures.
def clean_financials():

    # 1. Load the raw CSV.
    #
    # dtype="string" initially reads every column as text.
    # This gives us control over which columns become
    # integers, dates, and other numeric types.
    df = pd.read_csv(RAW_PATH, dtype="string")

    # 2. Convert identifiers and reporting dates.

    # CERT identifies the FDIC-insured institution.
    #
    # pd.to_numeric() converts the identifier into a number.
    # errors="coerce" converts invalid values to missing.
    #
    # .astype("Int64") uses pandas' nullable integer type,
    # which supports missing values (pd.NA).
    df["CERT"] = pd.to_numeric(df["CERT"], errors="coerce").astype("Int64")

    # REPDTE is the financial reporting date.
    #
    # format="%Y%m%d" expects dates such as 20250331,
    # representing March 31, 2025.
    #
    # Invalid dates become NaT (Not a Time).
    df["REPDTE"] = pd.to_datetime(df["REPDTE"], format="%Y%m%d", errors="coerce")

    # 3. Identify all financial columns that need numeric conversion.
    #
    # df.columns contains every column name in the DataFrame.
    #
    # This list comprehension loops through those names
    # and keeps every column EXCEPT CERT, REPDTE, and ID.
    #
    # We exclude:
    # CERT   -> already converted to a nullable integer
    # REPDTE -> already converted to datetime
    # ID     -> identifier, not a financial measurement
    #
    # Example:
    # ["CERT", "REPDTE", "ID", "ASSET", "DEP", "NETINC"]
    # becomes ["ASSET", "DEP", "NETINC"].
    numeric_columns = [col for col in df.columns if col not in ["CERT", "REPDTE", "ID"]]

    # Convert each financial column from text to numeric values.
    #
    # errors="coerce" turns invalid numeric strings into NaN.
    # This prevents malformed values from crashing the script.
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Sort the financial records by bank and reporting date.
    #
    # This is essential because we will compare each record
    # with the PREVIOUS record for the same bank.
    #
    # Sorting ensures each bank's quarters appear in
    # chronological order.
    #
    # reset_index(drop=True) creates a clean sequential index
    # without preserving the old index as another column.
    df = df.sort_values(["CERT", "REPDTE"]).reset_index(drop=True)

    # Extract the calendar year and quarter from REPDTE.
    #
    # Example:
    # REPDTE = 2025-06-30
    # YEAR = 2025
    # QUARTER = 2
    df["YEAR"] = df["REPDTE"].dt.year
    df["QUARTER"] = df["REPDTE"].dt.quarter

    # Convert each year and quarter into one sequential number.
    #
    # Formula: YEAR * 4 + QUARTER
    #
    # Example:
    # 2024 Q4 = 2024 * 4 + 4 = 8100
    # 2025 Q1 = 2025 * 4 + 1 = 8101
    #
    # This makes it easy to determine whether two reporting
    # periods are exactly one quarter apart, even across years.
    quarter_number = df["YEAR"] * 4 + df["QUARTER"]

    # Find the previous quarter number for EACH bank.
    #
    # groupby("CERT") separates records by institution.
    #
    # .shift(1) moves the quarter numbers down one row
    # within each bank's group.
    #
    # This aligns the previous reporting period with
    # the current reporting period.
    #
    # Importantly, a bank's first record has no previous
    # quarter, so its shifted value is missing.
    previous_quarter = quarter_number.groupby(df["CERT"]).shift(1)

    # Check whether the current record follows the previous
    # record by exactly one calendar quarter.
    #
    # If current quarter - previous quarter == 1,
    # the reporting periods are consecutive.
    #
    # Example:
    # 2024 Q4 -> 2025 Q1 = consecutive (difference of 1)
    # 2024 Q4 -> 2025 Q2 = NOT consecutive (difference of 2)
    #
    # Missing previous quarters are treated as False.
    #
    # This prevents us from subtracting YTD values
    # across gaps in a bank's reporting history.
    consecutive = (quarter_number - previous_quarter == 1).fillna(False)

    # 5. Convert YTD income figures into individual quarterly values.
    #
    # According to Appendix B, these financial fields are cumulative.
    #
    # For Q1, the YTD amount already represents Q1 alone.
    #
    # For Q2, Q3, and Q4:
    # Quarterly amount = Current YTD - Previous quarter's YTD
    #
    # Example:
    # Q1 NETINC = 100 -> Q1 NETINC_Q = 100
    # Q2 NETINC = 250 -> Q2 NETINC_Q = 150
    # Q3 NETINC = 400 -> Q3 NETINC_Q = 150
    #
    # We only subtract when the previous quarter exists.
    for col in YTD_COLUMNS:

        # Retrieve the previous YTD value for the SAME bank.
        #
        # groupby("CERT") prevents values from different banks
        # from being accidentally subtracted from each other.
        #
        # shift(1) aligns the previous record's YTD value
        # with the current record.
        previous_ytd = df.groupby("CERT")[col].shift(1)

        # Dynamically create the name of the new quarterly column.
        #
        # Example:
        # col = "NETINC" -> quarterly_col = "NETINC_Q"
        # col = "INTINC" -> quarterly_col = "INTINC_Q"
        quarterly_col = f"{col}_Q"

        # Calculate the quarterly financial value.
        #
        # This is a nested .where() expression.
        #
        # OUTER .where():
        # If QUARTER == 1, keep the original YTD value.
        # Otherwise, use the calculation from the inner .where().
        #
        # INNER .where():
        # Calculate current YTD - previous YTD only when
        # consecutive is True.
        #
        # If the previous quarter is missing or there is a
        # reporting gap, the result becomes NaN.
        #
        # This avoids inventing quarterly amounts when we
        # do not have the required previous observation.
        df[quarterly_col] = df[col].where(
            df["QUARTER"] == 1,
            (df[col] - previous_ytd).where(consecutive)
        )

    # Return the cleaned DataFrame.
    #
    # It contains the original financial columns plus
    # YEAR, QUARTER, and six new quarterly income columns.
    return df


# This block runs only when the script is executed directly.
# It does not run when clean_financials() is imported elsewhere.
if __name__ == "__main__":

    # Run the cleaning function.
    df = clean_financials()

    # Display a sample of original YTD net income
    # alongside the calculated quarterly net income.
    #
    # This helps us visually verify the conversion.
    print(df[["CERT", "REPDTE", "NETINC", "NETINC_Q"]].head(12))

    # Display the final number of rows and columns.
    print("\nShape:", df.shape)
