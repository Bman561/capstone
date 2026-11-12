

# PURPOSE:
# This script creates a data quality report for all six cleaned datasets.
#
# It runs our cleaning functions, profiles each column for missing and
# distinct values, and documents specific data quality issues.
#
# For certain issues, we compare the original raw data against the
# cleaned data to measure how many records were affected and whether
# the cleaning rules worked.
#
# The results are saved to data_quality.csv, providing evidence of
# our cleaning decisions and making the ETL process easier to validate.

from pathlib import Path
import pandas as pd

# Import our existing cleaning functions so the audit uses
# the same cleaned datasets as the staging pipeline.
from cleaned.cleaned_institutions import clean_institutions
from cleaned.cleaned_financials import clean_financials
from cleaned.cleaned_failures import clean_failures
from cleaned.cleaned_complaints import clean_complaints
from cleaned.clean_macro import clean_macro
from company_crosswalk import build_company_crosswalk


# 1. Set up file paths and a list to collect audit results.

# __file__ is the location of this Python script.
# resolve() converts it to an absolute path.
# parent.parent moves up two directory levels to the project root.
# This avoids relying on the terminal's current working directory.
BASE_PATH = Path(__file__).resolve().parent.parent

# The / operator joins folder and file paths when using pathlib.
RAW_PATH = BASE_PATH / "raw"

# Store all audit results in one list.
# Each dictionary we append will eventually become one CSV row.
audit = []


# 2. Reusable function to profile every column in a DataFrame.
# Instead of writing separate null and distinct-count checks for
# every dataset, we use one function that works with any DataFrame.
def profile_table(table_name, df):

    # df.columns contains all column names in the DataFrame.
    # Loop through them to generate one profile entry per column.
    for column in df.columns:

        # isna() returns True for missing values.
        # sum() counts those True values because True equals 1.
        #
        # nunique() counts distinct non-NULL values by default.
        # This helps identify columns with little variation,
        # potential identifiers, and missing-data patterns.
        audit.append({
            "table_name": table_name,
            "column_name": column,

            # These fields are blank because this is a general
            # column profile, not a specific cleaning-rule check.
            "issue": "",
            "cleaning_rule": "",
            "rows_affected": 0,
            "action_taken": "",

            "null_count": df[column].isna().sum(),
            "distinct_count": df[column].nunique(),

            # No specific rule is being tested in this entry.
            "rule_failure_count": 0
        })


# 3. Reusable function to document a specific data quality issue.
# This complements profile_table().
#
# profile_table() describes the overall condition of each column.
# record_issue() documents an identified problem, the rule used
# to address it, and the result of that cleaning decision.
def record_issue(table_name, column, issue, rule, affected, action, failures=0):

    # failures=0 is a default argument.
    # If we don't provide a failure count, Python uses zero.
    #
    # The audit dictionary follows the same structure as
    # profile_table() so all entries can be combined into one CSV.
    audit.append({
        "table_name": table_name,
        "column_name": column,
        "issue": issue,
        "cleaning_rule": rule,

        # Number of source records affected by the issue or rule.
        "rows_affected": affected,

        # Describe what our cleaning process did.
        "action_taken": action,

        # These are blank because this row documents a specific issue,
        # rather than providing general column statistics.
        "null_count": "",
        "distinct_count": "",

        # Number of remaining problems according to the supplied check.
        "rule_failure_count": failures
    })


# 4. Audit the institutions dataset.
def audit_institutions():

    # Run our existing cleaning function.
    # This ensures we audit the actual cleaned output.
    df = clean_institutions()

    # Record null and distinct counts for every cleaned column.
    profile_table("institutions", df)

    # Load the original JSON separately to examine issues
    # before our cleaning rules were applied.
    raw = pd.read_json(RAW_PATH / "fdic_institutions.json")

    # The FDIC JSON contains institution records nested under "data".
    # tolist() extracts those records, and DataFrame() turns them
    # into normal rows and columns for analysis.
    raw = pd.DataFrame(raw["data"].tolist())

    # Count placeholder end dates in the original dataset.
    #
    # 12/31/9999 is not a realistic closing date.
    # It represents an open-ended institution record.
    #
    # eq() means equals, and sum() counts matching rows.
    placeholders = raw["ENDEFYMD"].eq("12/31/9999").sum()

    record_issue(
        "institutions", "ENDEFYMD",
        "Placeholder end dates",
        "Replace 12/31/9999 with NULL",
        placeholders,
        "Converted placeholder dates to NULL",

        # Check that no year-9999 placeholders remain.
        # astype("string") lets us perform string comparisons.
        # A zero result indicates this specific placeholder
        # is no longer present in the cleaned column.
        df["ENDEFYMD"].astype("string").eq("9999-12-31").sum()
    )

    # Count blank or whitespace-only holding-company names.
    #
    # fullmatch(r"\s*") is a regular expression:
    # \s matches whitespace, and * means zero or more occurrences.
    #
    # This identifies empty strings and values containing only spaces.
    # fillna(False) prevents missing comparisons from being counted.
    #
    # We check blanks because empty strings should be treated as
    # missing values rather than meaningful company names.
    blanks = raw["NAMEHCR"].astype("string").str.fullmatch(r"\s*").fillna(False).sum()

    record_issue(
        "institutions", "NAMEHCR",
        "Blank holding-company names",
        "Replace blank strings with NULL",
        blanks,
        "Normalized missing holding-company values",

        # Verify that blank strings no longer remain after cleaning.
        # Actual NULL values are allowed because some institutions
        # legitimately have no holding-company information.
        df["NAMEHCR"].astype("string").str.fullmatch(r"\s*").fillna(False).sum()
    )

    # Return cleaned institutions so the crosswalk audit can reuse them.
    # This avoids calling clean_institutions() again later.
    return df


# 5. Audit quarterly financial data.
def audit_financials():

    df = clean_financials()
    profile_table("financials", df)

    # These quarterly income fields were derived from YTD values.
    #
    # For Q1, the year-to-date amount represents that quarter.
    # For later quarters, we generally subtract the previous
    # quarter's YTD value to calculate the current quarter.
    #
    # If the previous consecutive quarter is unavailable,
    # we cannot reliably calculate the quarterly difference.
    for column in ["NETINC_Q", "INTINC_Q", "EINTEXP_Q",
                   "NONII_Q", "NONIX_Q", "ELNATR_Q"]:

        # Count quarterly values that could not be calculated.
        # Keeping these as NULL is safer than inventing values.
        missing = df[column].isna().sum()

        record_issue(
            "financials", column,
            "Quarterly income cannot always be calculated",
            "Q1 uses YTD; later quarters require consecutive prior quarter",
            missing,
            "Left unavailable quarterly income as NULL",

            # Zero here is the supplied audit status.
            # It does not mean the column contains no NULL values.
            0
        )


# 6. Audit the FDIC failures dataset.
def audit_failures():

    df = clean_failures()
    profile_table("failures", df)

    # Read the original CSV as strings so we can inspect the
    # exact missing-value placeholders used in the source.
    #
    # dtype="string" prevents automatic numeric type inference.
    # keep_default_na=False prevents pandas from automatically
    # interpreting strings such as "NA" as missing values.
    raw = pd.read_csv(
        RAW_PATH / "fdic_failures.csv",
        dtype="string",
        keep_default_na=False
    )

    # Examine each original column for missing-value conventions.
    for column in raw.columns:

        # First condition: detect empty or whitespace-only strings.
        # Second condition: detect explicit placeholder values.
        #
        # | performs element-wise OR across the two Boolean Series.
        # A row counts if either condition is True.
        #
        # The parentheses let us combine the conditions
        # before sum() counts the matching records.
        missing = (
            raw[column].str.fullmatch(r"\s*").fillna(False)
            | raw[column].isin(["NA", "N/A", "NULL"])
        ).sum()

        # Only add a specific issue entry if the source actually
        # contained at least one missing-value placeholder.
        if missing > 0:
            record_issue(
                "failures", column,
                "Missing-value placeholders",
                "Replace blanks, NA, N/A and NULL with actual NULL",
                missing,
                "Standardized missing values",

                # This entry records zero rule failures.
                # No separate post-cleaning placeholder check
                # is performed here.
                0
            )


# 7. Audit CFPB complaints.
def audit_complaints():

    df = clean_complaints()
    profile_table("complaints", df)

    # Read the original complaints dataset.
    # This creates a raw DataFrame for reference.
    raw = pd.read_csv(
        RAW_PATH / "cfpb_complaints.csv",
        dtype="string"
    )

    # The CFPB uses product labels that may vary across time.
    # We created PRODUCT_HARMONIZED to group equivalent labels
    # into consistent categories for downstream analysis.
    #
    # Compare the harmonized category with the original product.
    # ne() means "not equal".
    # Each True value indicates the labels are different.
    #
    # fillna(False) excludes missing comparisons.
    # sum() counts how many rows received a different label.
    changed = (
        df["PRODUCT_HARMONIZED"]
        .ne(df["Product"])
        .fillna(False)
        .sum()
    )

    record_issue(
        "complaints", "PRODUCT_HARMONIZED",
        "Inconsistent product categories",
        "Map equivalent products to common categories",
        changed,
        "Created harmonized product categories",
        0
    )

    # Return cleaned complaints for the company crosswalk audit.
    # This lets us reuse the same cleaned dataset.
    return df


# 8. Audit the CFPB-to-FDIC company crosswalk.
def audit_crosswalk(complaints, institutions):

    # Build the crosswalk using the cleaned complaints and institutions.
    # This attempts to connect CFPB company names to FDIC records.
    df = build_company_crosswalk(complaints, institutions)

    # Profile all crosswalk columns for missing and distinct values.
    profile_table("company_crosswalk", df)

    # The crosswalk can classify companies as:
    # matched, holding_company, ambiguous, or unmatched.
    #
    # value_counts() counts companies in each category.
    # items() returns each status together with its count.
    #
    # We record these results to show how much of the company
    # matching process produced confident versus uncertain matches.
    for status, count in df["match_status"].value_counts().items():

        record_issue(
            "company_crosswalk", "match_status",
            f"Company matching result: {status}",
            "Match CFPB company names to FDIC bank or holding-company names",
            count,
            f"Classified {count} companies as {status}",

            # This is a descriptive matching outcome,
            # not a validation check for remaining rule failures.
            0
        )


# 9. Audit macroeconomic indicators.
def audit_macro():

    df = clean_macro()
    profile_table("macro", df)

    # Our macroeconomic data comes from separate FRED files.
    # These indicators have different original reporting frequencies.
    #
    # We convert them into quarterly observations so they can
    # be compared with the FDIC quarterly financial dataset.
    for name in ["DGS10", "FEDFUNDS", "MORTGAGE30US", "UNRATE"]:

        # f"fred_{name}.csv" dynamically creates the filename.
        # Example: when name is "DGS10", it reads fred_DGS10.csv.
        raw = pd.read_csv(RAW_PATH / f"fred_{name}.csv")

        # Convert the original observations to numeric values.
        #
        # errors="coerce" converts values that cannot be interpreted
        # as numbers into NaN instead of raising an exception.
        #
        # This allows us to identify missing or invalid observations.
        numeric = pd.to_numeric(raw[name], errors="coerce")
        missing = numeric.isna().sum()

        record_issue(
            "macro", name,
            "Missing source observations and mixed reporting frequencies",
            "Convert to numeric and aggregate to quarterly mean",
            missing,
            "Ignored missing observations when calculating quarterly averages",

            # Check whether any quarterly values are still missing
            # after the cleaning and aggregation process.
            #
            # A quarter with no usable numeric observations
            # may still have a NULL value.
            df[name].isna().sum()
        )


# 10. Run every audit when this script is executed directly.
#
# __name__ == "__main__" ensures this block only runs when
# we execute this file directly.
#
# If another Python file imports these functions, the audit
# does not automatically execute.
if __name__ == "__main__":

    print("Auditing institutions...")
    institutions = audit_institutions()

    print("Auditing financials...")
    audit_financials()

    print("Auditing failures...")
    audit_failures()

    print("Auditing complaints...")
    complaints = audit_complaints()

    # The crosswalk depends on both cleaned complaints and institutions.
    # That's why we save their DataFrames and pass them here.
    print("Auditing company crosswalk...")
    audit_crosswalk(complaints, institutions)

    print("Auditing macro...")
    audit_macro()

    # All audit functions append dictionaries to the same audit list.
    # Convert that list into one DataFrame for exporting.
    #
    # Each dictionary becomes one row, and dictionary keys
    # become the column names.
    data_quality = pd.DataFrame(audit)

    # Save the audit report in the project root.
    # index=False prevents pandas from adding an unnecessary
    # DataFrame index column to the CSV.
    output_path = BASE_PATH / "data_quality.csv"
    data_quality.to_csv(output_path, index=False)

    # value_counts() summarizes how many audit entries
    # were generated for each dataset.
    print("\n--- Audit Rows by Dataset ---")
    print(data_quality["table_name"].value_counts())

    # len() gives the total number of rows in the audit report.
    print("\n--- Total Audit Rows ---")
    print(len(data_quality))

    # Display the file location so we can find the generated CSV.
    print("\n--- Saved To ---")
    print(output_path)
