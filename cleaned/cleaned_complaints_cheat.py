
from pathlib import Path
import pandas as pd


# Build the absolute path to the CFPB complaints CSV file.
#
# __file__ refers to the current Python script.
# .resolve() gets its absolute location.
# .parent.parent moves up two folders to the project root.
# / "raw" / "cfpb_complaints.csv" points to the source dataset.
#
# We define this outside the function because the file location
# is a constant that doesn't need to be recalculated each time.
RAW_PATH = Path(__file__).resolve().parent.parent / "raw" / "cfpb_complaints.csv"


# Clean the CFPB complaints dataset and return a DataFrame
# ready for further transformation and warehouse loading.
def clean_complaints():

    # 1. Load the raw CFPB complaints dataset.
    #
    # dtype="string" initially reads all columns as pandas strings.
    # This prevents pandas from guessing incorrect data types,
    # especially for identifiers and categorical information.
    #
    # We then explicitly convert the columns that need other types.
    df = pd.read_csv(RAW_PATH, dtype="string")

    # 2. Convert the Complaint ID column into an integer.
    #
    # pd.to_numeric() converts the string identifiers into numbers.
    # errors="coerce" turns invalid values into NaN instead
    # of causing the program to crash.
    #
    # .astype("Int64") uses pandas' nullable integer type.
    # Unlike regular NumPy int64, this supports missing values (pd.NA).
    #
    # This is useful because complaint IDs should be integers,
    # but invalid or missing IDs still need to be identifiable.
    df["Complaint ID"] = pd.to_numeric(
        df["Complaint ID"], errors="coerce"
    ).astype("Int64")

    # 3. Convert both complaint date columns into datetime values.
    #
    # Looping avoids repeating the same conversion code twice.
    for col in ["Date received", "Date sent to company"]:

        # format="%Y-%m-%d" expects dates like 2024-03-15.
        # errors="coerce" converts invalid dates into NaT.
        #
        # Datetime values allow us to filter complaints by date,
        # calculate time differences, and group them by month/year.
        df[col] = pd.to_datetime(
            df[col], format="%Y-%m-%d", errors="coerce"
        )

    # 4. Convert timely response values into booleans.
    #
    # The original dataset stores responses as text:
    # "Yes" and "No".
    #
    # .map() replaces these with their corresponding Boolean values:
    # "Yes" -> True
    # "No"  -> False
    #
    # Any unexpected value not found in the dictionary
    # becomes missing (pd.NA after conversion).
    #
    # .astype("boolean") uses pandas' nullable Boolean type,
    # allowing True, False, and missing values.
    #
    # This makes it easier to calculate timely response rates.
    df["Timely response?"] = (
        df["Timely response?"]
        .map({"Yes": True, "No": False})
        .astype("boolean")
    )

    # 5. Harmonize product categories.
    #
    # CFPB product names have changed over time.
    # Some categories describe essentially the same product
    # but use different names depending on when the complaint
    # was submitted.
    #
    # This dictionary maps older and newer category names
    # into consistent groups for analysis.
    #
    # Example:
    # "Bank account or service" and "Checking or savings account"
    # are both grouped as "Checking or savings account".
    #
    # Keeping these categories consistent makes historical
    # complaint trends easier to compare.
    product_mapping = {
        "Checking or savings account": "Checking or savings account",
        "Bank account or service": "Checking or savings account",

        "Credit card": "Credit card",
        "Credit card or prepaid card": "Credit card",

        "Mortgage": "Mortgage",

        "Vehicle loan or lease": "Vehicle loan or lease",

        "Consumer Loan": "Personal loan",
        "Payday loan, title loan, or personal loan": "Personal loan",
        "Payday loan, title loan, personal loan, or advance loan": "Personal loan",
    }

    # Create a NEW column containing standardized product names.
    #
    # Step 1: .map(product_mapping)
    # Looks up each original product name in the dictionary.
    # If a match exists, it returns the standardized category.
    #
    # Example:
    # "Bank account or service" -> "Checking or savings account"
    #
    # If a product isn't listed in the dictionary,
    # .map() returns a missing value.
    #
    # Step 2: .fillna(df["Product"])
    # Replaces those missing mapping results with the original
    # product names instead of losing their information.
    #
    # Example:
    # "Student loan" is not in our dictionary,
    # so it remains "Student loan".
    #
    # We preserve the original Product column so we can still
    # examine the source categories when necessary.
    df["PRODUCT_HARMONIZED"] = (
        df["Product"].map(product_mapping).fillna(df["Product"])
    )

    # Return the cleaned DataFrame for use in other scripts,
    # such as our PostgreSQL warehouse-loading process.
    return df


# This block only runs when this Python file is executed directly.
#
# If another script imports clean_complaints(), this section
# will not automatically execute.
#
# This lets us reuse the cleaning function without printing
# validation results every time it is imported.
if __name__ == "__main__":

    # Execute the cleaning function and store the result.
    df = clean_complaints()

    # Display the number of rows and columns.
    # This helps confirm the dataset loaded successfully.
    print("\n--- Dataset Shape ---")
    print(df.shape)

    # Display the original product categories alongside
    # their harmonized categories.
    print("\n--- Product Harmonization ---")

    print(
        # Group complaints by their original and standardized names.
        df.groupby(["Product", "PRODUCT_HARMONIZED"])

        # Count how many complaints belong to each combination.
        .size()

        # Convert the grouped results into readable text
        # so the full output prints in the terminal.
        .to_string()
    )

    # Display each column's data type to verify our conversions.
    print("\n--- Data Types ---")
    print(df.dtypes)
