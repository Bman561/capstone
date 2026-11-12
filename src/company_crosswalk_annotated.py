# PURPOSE:
# Build a CFPB-to-FDIC company crosswalk by comparing cleaned company
# names with bank and holding-company names. The matching rules prioritize
# direct bank matches, avoid guessing a CERT for parent-company matches,
# and report coverage and uncertain cases for manual review.

#I built a company crosswalk because the CFPB and FDIC datasets don't share a common identifier.
# I standardized company names and used a prioritized matching process.
# I also separated direct bank matches from holding-company matches because I didn't want to incorrectly attribute complaints
# to individual banks."


# Regular expression
import re
import pandas as pd

from cleaned.cleaned_complaints import clean_complaints
from cleaned.cleaned_institutions import clean_institutions


# 1. Standardize company names so CFPB and FDIC names can be compared.
def normalize_name(name):

    # Return None for missing names.
    if pd.isna(name):
        return None

    # Make matching case-insensitive and remove surrounding spaces.
    name = str(name).upper().strip()

    # Standardize common naming variations.
    name = name.replace("&", " AND ")
    # Regex word boundaries (\b) help match N.A. as a standalone abbreviation.
    name = re.sub(r"\bN\.?\s*A\.?\b", " NATIONAL ASSOCIATION ", name)

    # Remove punctuation and collapse repeated whitespace.
    # [^...] means anything NOT in the allowed set of letters, digits, or spaces.
    name = re.sub(r"[^A-Z0-9\s]", " ", name)
    name = " ".join(name.split())

    # Expand common corporate abbreviations.
    replacements = {
        "CO": "COMPANY",
        "CORP": "CORPORATION",
        "INC": "INCORPORATED"
    }

    # Replace abbreviations word by word, leaving other words unchanged.
    words = name.split()
    # dict.get() uses the replacement when present; otherwise keeps the original word.
    words = [replacements.get(word, word) for word in words]

    return " ".join(words) if words else None


# 2. Remove corporate suffixes to support less restrictive name matching.
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

    # Repeatedly remove suffixes from the END of the name.
    # Example: "ABC BANK HOLDINGS INCORPORATED" becomes "ABC BANK".
    # words[-1] is the last word; the loop removes multiple trailing suffixes.
    while words and words[-1] in suffixes:
        words.pop()
    # If words contains something: Join all the words into one string, separated by spaces.
    # If words is empty: Return None.
    return " ".join(words) if words else None


# 3. Categorize companies that could not be matched to FDIC records.
def categorize_unmatched(name):

    if pd.isna(name):
        return "unknown"

    name = normalize_name(name)

    # Classify unmatched companies using keywords in their names.
    # These are descriptive categories, not confirmed institution types.
    if "CREDIT UNION" in name:
        return "credit union"

    # any() becomes True when at least one keyword appears in the name.
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


# 4. Build the CFPB-to-FDIC company crosswalk.
# The CFPB identifies companies by name, while the FDIC uses bank CERT numbers.
# Our goal is to connect these datasets without incorrectly assigning
# complaints to the wrong banking institution.
def build_company_crosswalk(complaints, institutions):

    # Group complaints by company so we only need to match each
    # unique company once instead of matching every individual complaint.
    # dropna=False includes complaints with missing company names.
    companies = (
        complaints.groupby("Company", dropna=False)
        .size()  # Count complaints belonging to each company.
        # Convert the grouped result back into a normal DataFrame.
        # The counts become a new column called complaint_count.
        .reset_index(name="complaint_count")
    )

    # Standardize CFPB company names before comparing them to FDIC names.
    # This handles differences in capitalization, punctuation,
    # abbreviations, and formatting across the two datasets.
    # apply() runs normalize_name() on every value in the Company column.
    companies["normalized_name"] = (
        companies["Company"].apply(normalize_name)
    )

    # Create a second version without corporate suffixes.
    # This gives us a less restrictive matching option if an exact
    # normalized match fails.
    # Example: "ABC BANK INCORPORATED" becomes "ABC BANK".
    companies["short_name"] = (
        companies["normalized_name"].apply(remove_suffixes)
    )

    # Identify the earliest and latest complaint dates.
    # We use this range to avoid comparing complaints against banks
    # that operated entirely outside the complaint reporting period.
    start_date = complaints["Date received"].min()
    end_date = complaints["Date received"].max()

    # Keep only the FDIC fields needed for matching.
    # CERT identifies a bank, NAME is the bank name, and NAMEHCR
    # identifies its holding company.
    # ESTYMD and ENDEFYMD describe when the institution operated.
    # .copy() creates an independent DataFrame.
    banks = institutions[
        ["CERT", "NAME", "NAMEHCR", "ESTYMD", "ENDEFYMD"]
    ].copy()

    # Filter banks to those whose operating dates overlap
    # at least some part of the complaint reporting period.
    #
    # First condition:
    # The bank was established before the complaint period ended,
    # OR its establishment date is missing.
    #
    # Second condition:
    # The bank closed after the complaint period began,
    # OR it has no recorded closing date.
    #
    # & means BOTH conditions must be true.
    # | means EITHER condition can be true.
    #
    # Missing dates are allowed rather than automatically excluding
    # an institution when we don't have complete date information.
    #
    # Example: A bank that closed in 2018 could still be relevant
    # if our complaint dataset includes complaints from 2015.
    banks = banks[
        (banks["ESTYMD"].isna() | (banks["ESTYMD"] <= end_date))
        &
        (banks["ENDEFYMD"].isna() | (banks["ENDEFYMD"] >= start_date))
    ].copy()

    # 5. Prepare normalized FDIC bank names.
    # We create a separate DataFrame for matching against actual banks.
    # Bank-name matches are important because they can potentially
    # identify a specific institution and its unique CERT.
    bank_names = banks.copy()

    bank_names["normalized_name"] = (
        bank_names["NAME"].apply(normalize_name)
    )

    # Also prepare suffix-stripped bank names as a fallback.
    bank_names["short_name"] = (
        bank_names["normalized_name"].apply(remove_suffixes)
    )

    # 6. Prepare normalized FDIC holding-company names.
    # We handle these separately because one holding company can own
    # several banks, each with a different CERT.
    #
    # Matching a holding company does not automatically tell us
    # which individual bank received the complaints.
    holding_names = banks.copy()

    holding_names["normalized_name"] = (
        holding_names["NAMEHCR"].apply(normalize_name)
    )

    holding_names["short_name"] = (
        holding_names["normalized_name"].apply(remove_suffixes)
    )

    # 7. Attempt to match every unique CFPB company to FDIC records.
    # Each company's result will be stored in this list.
    # After processing all companies, we convert it into a DataFrame.
    results = []

    # itertuples() loops through the companies DataFrame row by row.
    # It allows us to access values using company.column_name.
    # index=False prevents the DataFrame index from being included.
    for company in companies.itertuples(index=False):

        # Retrieve both versions of the current CFPB company name.
        name = company.normalized_name
        short_name = company.short_name

        # Start each company with no matches.
        # banks.iloc[0:0] returns zero rows but preserves the columns.
        # This ensures matches has the correct structure from the start.
        matches = banks.iloc[0:0].copy()

        # Track HOW we matched the company.
        # method tells us whether the match was exact or rule-based.
        # source tells us whether it came from a bank or holding name.
        method = "unmatched"
        source = pd.NA

        # Only attempt matching when a usable company name exists.
        if name is not None:

            # PRIORITY 1: Exact normalized bank-name match.
            # We start here because matching an actual bank name
            # gives us the best opportunity to identify a specific CERT.
            #
            # This expression compares the CFPB name against every
            # normalized FDIC bank name and keeps matching rows.
            matches = bank_names[
                bank_names["normalized_name"] == name
            ]

            # .empty is True when the DataFrame contains no rows.
            # If we found matches, record the method and source.
            if not matches.empty:
                method = "exact"
                source = "bank_name"

            # PRIORITY 2: Exact normalized holding-company match.
            # Only try this if the bank-name search found nothing.
            # A holding-company match is useful, but it might represent
            # multiple subsidiary banks rather than one specific CERT.
            if matches.empty:
                matches = holding_names[
                    holding_names["normalized_name"] == name
                ]

                if not matches.empty:
                    method = "exact"
                    source = "holding_company"

            # PRIORITY 3: Bank-name match after removing suffixes.
            # This is a fallback for naming differences such as
            # "ABC BANK INCORPORATED" versus "ABC BANK".
            #
            # We only reach this step when both exact searches failed.
            # The match_method becomes "rule" because we needed
            # additional name transformations to find the match.
            if matches.empty and short_name is not None:
                matches = bank_names[
                    bank_names["short_name"] == short_name
                ]

                if not matches.empty:
                    method = "rule"
                    source = "bank_name"

            # PRIORITY 4: Holding-company match without suffixes.
            # This is our final matching attempt.
            # We use it only when the earlier matching rules failed.
            #
            # Keeping the searches in priority order prevents a
            # broader match from replacing a stricter match.
            if matches.empty and short_name is not None:
                matches = holding_names[
                    holding_names["short_name"] == short_name
                ]

                if not matches.empty:
                    method = "rule"
                    source = "holding_company"

        # 8. Determine whether the match is specific or ambiguous.
        #
        # Finding a matching name is only the first step.
        # We still need to determine whether the match identifies
        # one specific bank or only a possible parent company.
        #
        # pd.NA represents a missing value in pandas.
        matched_cert = pd.NA
        matched_holding = pd.NA
        status = "unmatched"
        possible_certs = ""

        # Only evaluate candidate institutions if matching found rows.
        if not matches.empty:

            # Remove duplicate CERTs so the same bank is not counted
            # multiple times when evaluating how many candidates exist.
            matches = matches.drop_duplicates(subset=["CERT"])

            # dropna() removes missing CERT values.
            # unique() returns the distinct remaining certificate numbers.
            certs = matches["CERT"].dropna().unique()

            # Store all possible CERTs as a comma-separated string.
            # This is useful for investigating ambiguous matches later.
            # str(cert) converts each certificate number to text.
            possible_certs = ", ".join(str(cert) for cert in certs)

            # Retrieve distinct, nonmissing holding-company names
            # associated with the candidate banks.
            holdings = matches["NAMEHCR"].dropna().unique()

            # Normalize the holding names again to compare them fairly.
            # A set comprehension creates a collection of unique values.
            #
            # This helps identify whether multiple candidate banks
            # belong to the same parent company.
            normalized_holdings = {
                normalize_name(holding)
                for holding in holdings
            }

            # CASE 1: The match came from a holding-company name.
            #
            # Even if multiple bank records match, we should not
            # assign one of their CERTs because the complaint may
            # concern any subsidiary belonging to that parent.
            if source == "holding_company":

                # If all candidates point to one distinct holding
                # company, record the parent company only.
                if len(normalized_holdings) == 1:
                    matched_holding = holdings[0]
                    status = "holding_company"

                # If multiple parent companies are possible,
                # we cannot confidently identify the correct one.
                else:
                    status = "ambiguous"

            # CASE 2: The match came from a bank name and only
            # one unique CERT was found.
            #
            # This is our strongest match outcome because we can
            # identify one specific FDIC institution.
            elif len(certs) == 1:

                # certs[0] retrieves the only candidate certificate.
                matched_cert = certs[0]

                # iloc[0] retrieves the first matching bank row.
                # We also preserve its holding-company name if available.
                matched_holding = matches.iloc[0]["NAMEHCR"]

                status = "matched"

            # CASE 3: Multiple banks match, but they all appear
            # to belong to one holding company.
            #
            # len(certs) > 1 means more than one bank is possible.
            # len(normalized_holdings) == 1 means one parent is identified.
            # .notna().all() confirms every candidate has a parent name.
            #
            # We preserve the holding-company match but leave CERT missing.
            elif (
                len(certs) > 1
                and len(normalized_holdings) == 1
                and matches["NAMEHCR"].notna().all()
            ):

                matched_holding = holdings[0]
                status = "holding_company"

            # CASE 4: Multiple possible institutions exist and
            # we cannot safely identify one bank or shared parent.
            #
            # Rather than guessing, mark the result ambiguous
            # so it can be reviewed later.
            else:
                status = "ambiguous"

        # 9. Categorize companies that could not be matched.
        #
        # Some CFPB companies may not be FDIC-insured banks.
        # They could be credit unions, mortgage servicers,
        # fintech companies, or other lenders.
        #
        # Categorizing them helps explain unmatched complaint volume
        # rather than treating every unmatched company as an error.
        category = pd.NA

        if status == "unmatched":
            category = categorize_unmatched(company.Company)

        # Save the result for the current CFPB company.
        #
        # Each dictionary represents one row in the final crosswalk.
        # We preserve the match status and matching method so
        # downstream analysis can distinguish confident matches
        # from holding-company-only or ambiguous matches.
        #
        # complaint_count tells us how many complaints the company
        # represents, which helps measure matching coverage later.
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

    # Convert the list of dictionaries into a pandas DataFrame.
    # Each row now represents one unique CFPB company and its
    # matching outcome against FDIC records.
    crosswalk = pd.DataFrame(results)

    # Convert CERT to pandas' nullable integer type.
    #
    # Normal NumPy integer columns cannot represent pd.NA.
    # Nullable Int64 allows real CERT values to remain integers
    # while unmatched companies can have missing certificate numbers.
    crosswalk["CERT"] = crosswalk["CERT"].astype("Int64")

    # Return the completed crosswalk for use in our staging pipeline.
    return crosswalk




# Run validation output only when this script is executed directly.
if __name__ == "__main__":

    # 10. Load the cleaned datasets and build the crosswalk.
    complaints = clean_complaints()
    institutions = clean_institutions()

    crosswalk = build_company_crosswalk(
        complaints, institutions
    )

    # 11. Show the number of crosswalk records and matching outcomes.
    print("\n--- Crosswalk Shape ---")
    print(crosswalk.shape)

    print("\n--- Match Status ---")
    print(crosswalk["match_status"].value_counts())

    # 12. Calculate complaint coverage using complaint counts,
    # rather than simply counting how many companies matched.
    # Coverage is weighted by complaint volume, not the number of company names.
    total = crosswalk["complaint_count"].sum()

    # .loc filters matched companies and selects their complaint counts.
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

    # 13. Display the 25 unmatched companies with the most complaints.
    print("\n--- Top Unmatched Companies ---")

    print(
        crosswalk[crosswalk["match_status"] == "unmatched"]
        # Sort descending so the highest-volume cases are reviewed first.
        .sort_values("complaint_count", ascending=False)
        [["Company", "complaint_count", "unmatched_category"]]
        .head(25)
        .to_string(index=False)
    )

    # 14. Review ambiguous matches and their candidate bank certificates.
    print("\n--- Top Ambiguous Companies ---")

    print(
        crosswalk[crosswalk["match_status"] == "ambiguous"]
        .sort_values("complaint_count", ascending=False)
        [["Company", "possible_certs", "complaint_count"]]
        .head(25)
        .to_string(index=False)
    )

    # 15. Review matches that identify a holding company but not a bank.
    print("\n--- Holding-Company Matches ---")

    print(
        crosswalk[crosswalk["match_status"] == "holding_company"]
        .sort_values("complaint_count", ascending=False)
        [["Company", "NAMEHCR", "possible_certs", "complaint_count"]]
        .head(25)
        .to_string(index=False)
    )

    # 16. Review high-volume matches assigned to specific banks.
    # The threshold of 300 complaints helps prioritize manual review.
    print("\n--- High-Volume Automatic Matches ---")

    print(
        crosswalk[
            (crosswalk["match_status"] == "matched")
            & (crosswalk["complaint_count"] >= 300)
        ]
        .sort_values("complaint_count", ascending=False)
        .to_string(index=False)
    )

    # 17. Summarize unmatched complaint volumes by category.
    print("\n--- Unmatched Complaint Categories ---")

    print(
        crosswalk[crosswalk["match_status"] == "unmatched"]
        .groupby("unmatched_category")["complaint_count"]
        .sum()
        .sort_values(ascending=False)
    )

