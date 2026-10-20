
from pathlib import Path
import pandas as pd

from cleaned.cleaned_institutions import clean_institutions
from cleaned.cleaned_financials import clean_financials
from cleaned.cleaned_failures import clean_failures
from cleaned.cleaned_complaints import clean_complaints
from cleaned.clean_macro import clean_macro
from company_crosswalk import build_company_crosswalk


# 1. Set up our output
BASE_PATH = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_PATH / "raw"

audit = []


# 2. Reusable function: profile every column
def profile_table(table_name, df):

    for column in df.columns:
        audit.append({
            "table_name": table_name,
            "column_name": column,
            "issue": "",
            "cleaning_rule": "",
            "rows_affected": 0,
            "action_taken": "",
            "null_count": df[column].isna().sum(),
            "distinct_count": df[column].nunique(),
            "rule_failure_count": 0
        })


# 3. Reusable function: record important cleaning decisions
def record_issue(table_name, column, issue, rule, affected, action, failures=0):

    audit.append({
        "table_name": table_name,
        "column_name": column,
        "issue": issue,
        "cleaning_rule": rule,
        "rows_affected": affected,
        "action_taken": action,
        "null_count": "",
        "distinct_count": "",
        "rule_failure_count": failures
    })


# 4. Audit institutions
def audit_institutions():

    df = clean_institutions()
    profile_table("institutions", df)

    # Check placeholder dates
    raw = pd.read_json(RAW_PATH / "fdic_institutions.json")
    raw = pd.DataFrame(raw["data"].tolist())

    placeholders = raw["ENDEFYMD"].eq("12/31/9999").sum()

    record_issue(
        "institutions", "ENDEFYMD",
        "Placeholder end dates",
        "Replace 12/31/9999 with NULL",
        placeholders,
        "Converted placeholder dates to NULL",
        df["ENDEFYMD"].astype("string").eq("9999-12-31").sum()
    )

    # Check blank holding-company names
    blanks = raw["NAMEHCR"].astype("string").str.fullmatch(r"\s*").fillna(False).sum()

    record_issue(
        "institutions", "NAMEHCR",
        "Blank holding-company names",
        "Replace blank strings with NULL",
        blanks,
        "Normalized missing holding-company values",
        df["NAMEHCR"].astype("string").str.fullmatch(r"\s*").fillna(False).sum()
    )

    return df


# 5. Audit financials
def audit_financials():

    df = clean_financials()
    profile_table("financials", df)

    # Count missing quarterly income values
    for column in ["NETINC_Q", "INTINC_Q", "EINTEXP_Q",
                   "NONII_Q", "NONIX_Q", "ELNATR_Q"]:

        missing = df[column].isna().sum()

        record_issue(
            "financials", column,
            "Quarterly income cannot always be calculated",
            "Q1 uses YTD; later quarters require consecutive prior quarter",
            missing,
            "Left unavailable quarterly income as NULL",
            0
        )


# 6. Audit failures
def audit_failures():

    df = clean_failures()
    profile_table("failures", df)

    raw = pd.read_csv(
        RAW_PATH / "fdic_failures.csv",
        dtype="string",
        keep_default_na=False
    )

    # Count source missing-value placeholders
    for column in raw.columns:

        missing = (
            raw[column].str.fullmatch(r"\s*").fillna(False)
            | raw[column].isin(["NA", "N/A", "NULL"])
        ).sum()

        if missing > 0:
            record_issue(
                "failures", column,
                "Missing-value placeholders",
                "Replace blanks, NA, N/A and NULL with actual NULL",
                missing,
                "Standardized missing values",
                0
            )


# 7. Audit complaints
def audit_complaints():

    df = clean_complaints()
    profile_table("complaints", df)

    raw = pd.read_csv(
        RAW_PATH / "cfpb_complaints.csv",
        dtype="string"
    )

    # Count harmonized product categories
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

    return df


# 8. Audit company crosswalk
def audit_crosswalk(complaints, institutions):

    df = build_company_crosswalk(complaints, institutions)
    profile_table("company_crosswalk", df)

    # Record each matching outcome
    for status, count in df["match_status"].value_counts().items():

        record_issue(
            "company_crosswalk", "match_status",
            f"Company matching result: {status}",
            "Match CFPB company names to FDIC bank or holding-company names",
            count,
            f"Classified {count} companies as {status}",
            0
        )


# 9. Audit macroeconomic data
def audit_macro():

    df = clean_macro()
    profile_table("macro", df)

    for name in ["DGS10", "FEDFUNDS", "MORTGAGE30US", "UNRATE"]:

        raw = pd.read_csv(RAW_PATH / f"fred_{name}.csv")

        numeric = pd.to_numeric(raw[name], errors="coerce")
        missing = numeric.isna().sum()

        record_issue(
            "macro", name,
            "Missing source observations and mixed reporting frequencies",
            "Convert to numeric and aggregate to quarterly mean",
            missing,
            "Ignored missing observations when calculating quarterly averages",
            df[name].isna().sum()
        )


# 10. Run all audits
if __name__ == "__main__":

    print("Auditing institutions...")
    institutions = audit_institutions()

    print("Auditing financials...")
    audit_financials()

    print("Auditing failures...")
    audit_failures()

    print("Auditing complaints...")
    complaints = audit_complaints()

    print("Auditing company crosswalk...")
    audit_crosswalk(complaints, institutions)

    print("Auditing macro...")
    audit_macro()

    # Save everything to one CSV
    data_quality = pd.DataFrame(audit)

    output_path = BASE_PATH / "data_quality.csv"
    data_quality.to_csv(output_path, index=False)

    print("\n--- Audit Rows by Dataset ---")
    print(data_quality["table_name"].value_counts())

    print("\n--- Total Audit Rows ---")
    print(len(data_quality))

    print("\n--- Saved To ---")
    print(output_path)
