
import re
import pandas as pd

from cleaned.cleaned_complaints import clean_complaints
from cleaned.cleaned_institutions import clean_institutions


# 1. Normalize company names so CFPB and FDIC names are comparable
def normalize_name(name):

    if pd.isna(name):
        return None

    name = str(name).upper().strip()

    # Standardize common abbreviations
    name = name.replace("&", " AND ")
    name = re.sub(r"\bN\.?\s*A\.?\b", " NATIONAL ASSOCIATION ", name)

    # Remove punctuation and extra spaces
    name = re.sub(r"[^A-Z0-9\s]", " ", name)
    name = " ".join(name.split())

    replacements = {
        "CO": "COMPANY",
        "CORP": "CORPORATION",
        "INC": "INCORPORATED"
    }

    words = name.split()
    words = [replacements.get(word, word) for word in words]

    return " ".join(words) if words else None


# 2. Remove corporate suffixes from the end of a name
def remove_suffixes(name):

    if pd.isna(name) or not name:
        return None

    suffixes = {
        "INCORPORATED",
        "CORPORATION",
        "COMPANY",
        "LLC",
        "LTD",
        "LIMITED",
        "BANCORP",
        "HOLDINGS",
        "FINANCIAL"
    }

    words = name.split()

    while words and words[-1] in suffixes:
        words.pop()

    return " ".join(words) if words else None


# 3. Categorize companies that could not be matched
def categorize_unmatched(name):

    if pd.isna(name):
        return "unknown"

    name = normalize_name(name)

    if "CREDIT UNION" in name:
        return "credit union"

    elif any(word in name for word in [
        "MORTGAGE", "SERVICING", "HOME LOANS"
    ]):
        return "mortgage servicer or lender"

    elif any(word in name for word in [
        "PAYMENTS", "PAYPAL", "FINTECH", "CHIME"
    ]):
        return "fintech or payments"

    elif any(word in name for word in [
        "EQUIFAX", "EXPERIAN", "TRANSUNION", "CREDIT BUREAU"
    ]):
        return "credit bureau"

    elif any(word in name for word in [
        "AUTO FINANCE", "AUTO CREDIT", "MOTOR CREDIT"
    ]):
        return "auto finance"

    elif any(word in name for word in [
        "LENDING", "LOANS", "FINANCE"
    ]):
        return "other lender"

    return "unknown"


# 4. Build the company crosswalk
def build_company_crosswalk(complaints, institutions):

    # Get each unique CFPB company and its complaint count
    companies = (
        complaints.groupby("Company", dropna=False)
        .size()
        .reset_index(name="complaint_count")
    )

    companies["normalized_name"] = (
        companies["Company"].apply(normalize_name)
    )

    companies["short_name"] = (
        companies["normalized_name"].apply(remove_suffixes)
    )

    # Determine the complaint date range
    start_date = complaints["Date received"].min()
    end_date = complaints["Date received"].max()

    # Include banks that existed during the complaint period
    banks = institutions[
        ["CERT", "NAME", "NAMEHCR", "ESTYMD", "ENDEFYMD"]
    ].copy()

    banks = banks[
        (banks["ESTYMD"].isna() | (banks["ESTYMD"] <= end_date))
        &
        (banks["ENDEFYMD"].isna() | (banks["ENDEFYMD"] >= start_date))
    ].copy()

    # 5. Prepare FDIC bank names
    bank_names = banks.copy()

    bank_names["normalized_name"] = (
        bank_names["NAME"].apply(normalize_name)
    )

    bank_names["short_name"] = (
        bank_names["normalized_name"].apply(remove_suffixes)
    )

    # 6. Prepare FDIC holding-company names
    holding_names = banks.copy()

    holding_names["normalized_name"] = (
        holding_names["NAMEHCR"].apply(normalize_name)
    )

    holding_names["short_name"] = (
        holding_names["normalized_name"].apply(remove_suffixes)
    )

    # 7. Match each CFPB company against FDIC
    results = []

    for company in companies.itertuples(index=False):

        name = company.normalized_name
        short_name = company.short_name

        matches = banks.iloc[0:0].copy()
        method = "unmatched"
        source = pd.NA

        if name is not None:

            # First try exact bank-name matching
            matches = bank_names[
                bank_names["normalized_name"] == name
            ]

            if not matches.empty:
                method = "exact"
                source = "bank_name"

            # Next try exact holding-company matching
            if matches.empty:
                matches = holding_names[
                    holding_names["normalized_name"] == name
                ]

                if not matches.empty:
                    method = "exact"
                    source = "holding_company"

            # Next try suffix-stripped bank-name matching
            if matches.empty and short_name is not None:
                matches = bank_names[
                    bank_names["short_name"] == short_name
                ]

                if not matches.empty:
                    method = "rule"
                    source = "bank_name"

            # Finally try suffix-stripped holding-company matching
            if matches.empty and short_name is not None:
                matches = holding_names[
                    holding_names["short_name"] == short_name
                ]

                if not matches.empty:
                    method = "rule"
                    source = "holding_company"

        # 8. Decide whether the match identifies a bank or holding company
        matched_cert = pd.NA
        matched_holding = pd.NA
        status = "unmatched"
        possible_certs = ""

        if not matches.empty:

            matches = matches.drop_duplicates(subset=["CERT"])
            certs = matches["CERT"].dropna().unique()

            possible_certs = ", ".join(str(cert) for cert in certs)

            holdings = matches["NAMEHCR"].dropna().unique()

            normalized_holdings = {
                normalize_name(holding)
                for holding in holdings
            }

            # FIX: A holding-company name does not prove a specific CERT
            if source == "holding_company":

                if len(normalized_holdings) == 1:
                    matched_holding = holdings[0]
                    status = "holding_company"
                else:
                    status = "ambiguous"

            # Bank-name matches can identify a specific CERT
            elif len(certs) == 1:

                matched_cert = certs[0]
                matched_holding = matches.iloc[0]["NAMEHCR"]
                status = "matched"

            # Multiple bank certificates, but one shared holding company
            elif (
                len(certs) > 1
                and len(normalized_holdings) == 1
                and matches["NAMEHCR"].notna().all()
            ):

                matched_holding = holdings[0]
                status = "holding_company"

            # Multiple certificates without a clear shared parent
            else:
                status = "ambiguous"

        # 9. Categorize companies that remain unmatched
        category = pd.NA

        if status == "unmatched":
            category = categorize_unmatched(company.Company)

        results.append({
            "Company": company.Company,
            "CERT": matched_cert,
            "NAMEHCR": matched_holding,
            "match_method": method,
            "match_source": source,
            "match_status": status,
            "possible_certs": possible_certs,
            "unmatched_category": category,
            "complaint_count": company.complaint_count
        })

    crosswalk = pd.DataFrame(results)

    crosswalk["CERT"] = crosswalk["CERT"].astype("Int64")

    return crosswalk


if __name__ == "__main__":

    # 10. Load cleaned datasets
    complaints = clean_complaints()
    institutions = clean_institutions()

    crosswalk = build_company_crosswalk(
        complaints, institutions
    )

    # 11. Display crosswalk size and match status
    print("\n--- Crosswalk Shape ---")
    print(crosswalk.shape)

    print("\n--- Match Status ---")
    print(crosswalk["match_status"].value_counts())

    # 12. Calculate complaint coverage
    total = crosswalk["complaint_count"].sum()

    bank_matched = crosswalk.loc[
        crosswalk["match_status"] == "matched",
        "complaint_count"
    ].sum()

    holding_matched = crosswalk.loc[
        crosswalk["match_status"] == "holding_company",
        "complaint_count"
    ].sum()

    print("\n--- Complaint Coverage ---")
    print(f"Total complaints: {total:,}")
    print(f"Unique-CERT coverage: {bank_matched / total * 100:.2f}%")
    print(f"Holding-company-only coverage: {holding_matched / total * 100:.2f}%")
    print(
        f"Combined provisional coverage: "
        f"{(bank_matched + holding_matched) / total * 100:.2f}%"
    )

    # 13. Show the largest unmatched companies
    print("\n--- Top Unmatched Companies ---")

    print(
        crosswalk[crosswalk["match_status"] == "unmatched"]
        .sort_values("complaint_count", ascending=False)
        [["Company", "complaint_count", "unmatched_category"]]
        .head(25)
        .to_string(index=False)
    )

    # 14. Show companies with ambiguous matches
    print("\n--- Top Ambiguous Companies ---")

    print(
        crosswalk[crosswalk["match_status"] == "ambiguous"]
        .sort_values("complaint_count", ascending=False)
        [["Company", "possible_certs", "complaint_count"]]
        .head(25)
        .to_string(index=False)
    )

    # 15. Show holding-company matches
    print("\n--- Holding-Company Matches ---")

    print(
        crosswalk[crosswalk["match_status"] == "holding_company"]
        .sort_values("complaint_count", ascending=False)
        [["Company", "NAMEHCR", "possible_certs", "complaint_count"]]
        .head(25)
        .to_string(index=False)
    )

    # 16. Review high-volume automatic bank matches
    print("\n--- High-Volume Automatic Matches ---")

    print(
        crosswalk[
            (crosswalk["match_status"] == "matched")
            & (crosswalk["complaint_count"] >= 300)
        ]
        .sort_values("complaint_count", ascending=False)
        .to_string(index=False)
    )

    # 17. Show unmatched complaint categories
    print("\n--- Unmatched Complaint Categories ---")

    print(
        crosswalk[crosswalk["match_status"] == "unmatched"]
        .groupby("unmatched_category")["complaint_count"]
        .sum()
        .sort_values(ascending=False)
    )
