
from pathlib import Path
import pandas as pd


# Define the location of our raw FDIC bank failures dataset.
#
# __file__ refers to the current Python script.
# .resolve() gets its absolute path.
# .parent.parent moves up two folders to the project root.
# / "raw" / "fdic_failures.csv" points to the original CSV file.
RAW_PATH = Path(__file__).resolve().parent.parent / "raw" / "fdic_failures.csv"


# Load and clean the FDIC failures dataset.
# This dataset contains information about failed banks,
# including failure dates, financial balances, and resolution costs.
def clean_failures():

    # 1. Read the raw CSV into a pandas DataFrame.
    #
    # dtype="string" initially loads all columns as text,
    # allowing us to control how each field gets converted.
    #
    # keep_default_na=False prevents pandas from automatically
    # interpreting strings like "NA" as missing values.
    #
    # We do this because we want to handle missing-value
    # conventions ourselves in the next step.
    df = pd.read_csv(RAW_PATH, dtype="string", keep_default_na=False)

    # 2. Standardize missing values.
    #
    # Different datasets may represent missing information
    # using empty strings, spaces, "NA", "N/A", or "NULL".
    #
    # First, replace blank strings and whitespace-only
    # values with pandas' missing-value marker (pd.NA).
    #
    # r"^\s*$" is a regular expression:
    # ^  = beginning of the string
    # \s = any whitespace character (space, tab, etc.)
    # *  = zero or more occurrences
    # $  = end of the string
    #
    # Together, this matches empty strings and values
    # containing only whitespace.
    #
    # regex=True tells pandas to interpret the pattern
    # as a regular expression rather than literal text.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # Replace additional missing-value placeholders with pd.NA.
    #
    # These are exact text matches, so regex isn't needed.
    # This ensures all missing values use a consistent format.
    df = df.replace(["NA", "N/A", "NULL"], pd.NA)

    # 3. Convert identifiers and financial amounts to numeric types.
    #
    # The dataset initially stores everything as strings.
    # We need numeric values for calculations, comparisons,
    # and database loading.
    #
    # CERT     = FDIC certificate number identifying the bank
    # FAILYR   = Year the bank failed
    # QBFASSET = Bank assets reported around the failure period
    # QBFDEP   = Bank deposits reported around the failure period
    # COST     = Reported resolution cost
    # UNINSDEP = Uninsured deposits
    # FUND     = Fund-related numeric field
    #
    # Looping through the column names avoids repeating
    # the same conversion statement seven times.
    for col in ["CERT", "FAILYR", "QBFASSET", "QBFDEP",
                "COST", "UNINSDEP", "FUND"]:

        # Convert the current column from strings to numbers.
        #
        # errors="coerce" replaces invalid numeric values
        # with NaN rather than raising an exception.
        #
        # Example:
        # "25000" -> 25000
        # "unknown" -> NaN
        #
        # This allows us to identify problematic records
        # without stopping the entire cleaning process.
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Convert date columns into datetime values.
    #
    # The failure dataset uses two different date formats.
    # We handle them separately to avoid parsing errors.

    # These columns use the MM/DD/YYYY format.
    # Example: "03/10/2023" -> March 10, 2023.
    for col in ["FAILDATE", "RESDATE"]:

        # Convert the current column into datetime.
        #
        # format="%m/%d/%Y" specifies:
        # %m = month
        # %d = day
        # %Y = four-digit year
        #
        # Invalid or missing dates become NaT (Not a Time).
        df[col] = pd.to_datetime(
            df[col], format="%m/%d/%Y", errors="coerce"
        )

    # These columns use the YYYY-MM-DD format.
    # Example: "2023-03-10" -> March 10, 2023.
    for col in ["COSTMOSTRECENTASOF", "PTRDATE", "BRDATE"]:

        # Convert these dates using their expected format.
        #
        # %Y = four-digit year
        # %m = month
        # %d = day
        #
        # errors="coerce" handles invalid values consistently.
        df[col] = pd.to_datetime(
            df[col], format="%Y-%m-%d", errors="coerce"
        )

    # Return the cleaned DataFrame.
    #
    # Other scripts can import clean_failures() and use
    # the result to load failure records into PostgreSQL
    # or compare failed banks against financial data.
    return df


# This block executes only when we run this script directly.
#
# If another Python script imports clean_failures(),
# the function can be reused without automatically
# printing all these validation results.
if __name__ == "__main__":

    # Run the cleaning function and store its returned DataFrame.
    df = clean_failures()

    # Display the total number of rows and columns.
    # This helps confirm that the dataset loaded successfully.
    print("\n--- Dataset Shape ---")
    print(df.shape)

    # Display the first 10 cleaned records, focusing on
    # the identifiers, dates, and important financial fields.
    print("\n--- Cleaned Failure Examples ---")

    print(
        df[["CERT", "NAME", "FAILDATE", "RESDATE",
            "QBFASSET", "QBFDEP", "COST"]]

        # Select the first 10 records.
        .head(10)

        # Convert the DataFrame into readable text.
        # index=False hides the pandas row index.
        .to_string(index=False)
    )

    # Display each column's data type to confirm that
    # numeric and date conversions worked as expected.
    print("\n--- Data Types ---")
    print(df.dtypes)
