
from pathlib import Path
import pandas as pd


RAW_PATH = Path(__file__).resolve().parent.parent / "raw" / "cfpb_complaints.csv"


def clean_complaints():
    # 1. Load raw data
    df = pd.read_csv(RAW_PATH, dtype="string")

    # 2. Convert complaint identifier
    df["Complaint ID"] = pd.to_numeric(
        df["Complaint ID"], errors="coerce"
    ).astype("Int64")

    # 3. Convert dates
    for col in ["Date received", "Date sent to company"]:
        df[col] = pd.to_datetime(
            df[col], format="%Y-%m-%d", errors="coerce"
        )

    # 4. Convert timely response to boolean
    df["Timely response?"] = (
        df["Timely response?"]
        .map({"Yes": True, "No": False})
        .astype("boolean")
    )

    # 5. Harmonize product categories
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

    df["PRODUCT_HARMONIZED"] = (
        df["Product"].map(product_mapping).fillna(df["Product"])
    )

    return df


if __name__ == "__main__":
    df = clean_complaints()

    print("\n--- Dataset Shape ---")
    print(df.shape)

    print("\n--- Product Harmonization ---")
    print(
        df.groupby(["Product", "PRODUCT_HARMONIZED"])
        .size()
        .to_string()
    )

    print("\n--- Data Types ---")
    print(df.dtypes)
