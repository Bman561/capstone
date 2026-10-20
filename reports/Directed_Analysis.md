# Part 5: Directed Analysis

## Question 1: Data Quality

**Question:** Where is the data missing, invalid, or inconsistent across the eight files? Include type mismatches, placeholder values, duplicate keys, orphaned keys between files, and values that do not make sense. For each, what did you do and what did it change?

### 1.1 Overview

Data quality was assessed during the profiling, cleaning, and warehouse-loading stages of the project. Python and pandas were used to inspect raw data, while SQL validation queries were used to verify identifiers and relationships after loading.

The primary objective was to identify problems that could affect financial calculations, bank identification, complaint attribution, and downstream reporting.

The findings below distinguish between issues identified in the raw data and integrity checks performed after loading.

### 1.2 Missing Values and Blank Strings

**Source layer:** Raw FDIC institutions dataset  
**Code reference:** `../src/profile_data.py` and the institution-cleaning script from Part 1

The institution dataset contained 27,835 records.

Profiling identified the following missing values:

| Column | Missing or blank values | Finding |
|---|---:|---|
| `ASSET` | 4,006 | Missing financial balances |
| `DEP` | 4,006 | Missing deposit balances |
| `WEBADDR` | 23,686 | Missing or blank website addresses |
| `NAMEHCR` | 10,760 | Missing or blank holding-company names |
| `BKCLASS` | 1 | Missing charter classification |

Of the 4,006 records missing assets, 4,001 belonged to inactive institutions and five belonged to active institutions.

**Action taken:** Blank text values were standardized to NULL during cleaning. Missing financial values were preserved rather than replaced with zero. The missing charter classification for Society Bank, Indiana (CERT 15656) was also preserved.

**Impact:** Missing values became consistently identifiable, and financial calculations were protected from treating unknown balances as actual zeros. Preserving missing holding-company names also avoided creating unsupported company matches.

### 1.3 Placeholder Dates and Date Types

**Source layer:** Raw FDIC institutions dataset  
**Code reference:** `../src/profile_data.py` and the institution-cleaning script from Part 1

The `ESTYMD` and `ENDEFYMD` fields were originally represented as strings.

The profiling process identified **4,242 records** where `ENDEFYMD` contained `12/31/9999`.

Of these:

- 4,220 were marked active.
- 22 were marked inactive.

Although the values could be interpreted as dates during profiling, the year 9999 was a placeholder rather than a meaningful institution closure date.

**Action taken:** Date strings were parsed into date values, and `12/31/9999` was replaced with NULL.

**Impact:** All 4,242 placeholder values were removed from the cleaned end-date field. This prevented an artificial future date from affecting chronological analysis.

### 1.4 Data Type and Categorical Validation

**Source layer:** Raw FDIC institutions dataset  
**Code reference:** `../src/profile_data.py` and the institution-cleaning script from Part 1

The original institution data included several fields requiring type standardization:

| Field | Original representation | Treatment |
|---|---|---|
| `ACTIVE` | Integer (`0` or `1`) | Converted to Boolean |
| `ESTYMD` | String | Converted to date |
| `ENDEFYMD` | String | Converted to date, with placeholder normalization |
| `CERT` | Integer | Retained as institution identifier |
| `ASSET`, `DEP` | Floating-point numeric | Validated for missing, negative, and zero values |

The `ACTIVE` field contained 23,615 inactive and 4,220 active records, with no unexpected values.

**Action taken:** Fields were standardized to appropriate types during cleaning and warehouse loading.

**Impact:** Consistent types made it easier to filter institutions, compare dates, join records, and perform numeric calculations.

### 1.5 Duplicate Keys

**Source layer:** Raw FDIC institutions dataset  
**Code reference:** `../src/profile_data.py`

The `CERT` field was evaluated as the institution identifier.

| Validation | Result |
|---|---:|
| Total records | 27,835 |
| Distinct CERT values | 27,835 |
| Duplicate CERT values | 0 |

**Action taken:** No duplicate CERT records required removal in the institution dataset.

**Impact:** CERT could be used as the unique bank identifier in the normalized warehouse and analytics mart.

The financial mart was subsequently created at a bank-quarter grain, with a composite primary key of `(cert, quarter_end)`.

**Additional code reference:** `../sql/04_create_mart.sql`

### 1.6 Orphaned Keys and Referential Integrity

**Source layer:** Normalized warehouse and analytics mart  
**Code reference:** `../sql/02_load_warehouse.sql` and `../sql/04_create_mart.sql`

Referential integrity was checked after data loading to ensure that financial and complaint records could be associated with valid dimension records.

The final mart validation confirmed:

- 517,842 financial records, with no missing bank references.
- 517,842 financial records, with no missing date references.
- No complaint records with invalid non-null bank CERT references.
- No invalid complaint references to the company, product, response, channel, or state dimensions.

Complaints without a reliable bank match were intentionally retained with NULL CERT values.

**Action taken:** The warehouse and mart were built using normalized identifiers and validated relationships. Unmatched complaints were preserved instead of assigned to arbitrary banks.

**Impact:** Financial analysis uses valid bank references, while complaint analysis retains unmatched records without introducing false bank attribution.

These checks establish integrity in the final mart; they do not establish that every raw file was originally free of orphaned identifiers.

### 1.7 Numeric Validation and Implausible Values

**Source layer:** Raw FDIC institutions dataset  
**Code reference:** `../src/profile_data.py`

The institution financial fields were inspected for missing, negative, zero, and extreme values.

| Check | Assets | Deposits |
|---|---:|---:|
| Missing values | 4,006 | 4,006 |
| Negative values | 0 | 0 |
| Zero values | 0 | 189 |
| Minimum | 1 | 0 |
| Maximum | 4,091,315,000 | 2,820,284,000 |

**Action taken:** Missing and zero values were preserved separately. Large balances were not automatically treated as invalid because institution size varies substantially.

**Impact:** Financial calculations retained the distinction between missing balances and reported zero balances.

The available institution profiling does not establish how many implausible financial ratios, such as ratios in the thousands, were present in the separate financial dataset. No unverified correction is claimed for those values.

### 1.8 Inconsistent Charter Classifications

**Source layers:** Raw FDIC institutions and historical failures/assistance data  
**Code references:** `../src/profile_data.py`, Part 1 data dictionary, and cleaning scripts

The institution dataset contained one blank charter classification for CERT 15656.

Additionally, the historical failures/assistance data included the charter code `MI`, which was not represented in the same way in the current institution classification list.

**Action taken:** The blank classification was retained as NULL. The historical `MI` classification was documented rather than forcibly converted to a modern charter category.

**Impact:** Historical classification information was preserved, avoiding potentially incorrect assumptions when comparing records across different periods.

### 1.9 Overall Impact and Limitations

The cleaning and validation process improved the consistency of institution identifiers, dates, numeric values, categorical fields, and warehouse relationships.

The resulting analytics mart supports financial and complaint reporting without requiring Power BI to repeat the raw-data cleaning process.

The confirmed findings above draw primarily from the institution profiling output and final warehouse/mart validations. A complete eight-file data-quality inventory would also require the profiling results for the remaining source files, particularly their original duplicate counts, orphaned-key counts, and implausible financial-ratio checks.

**Supporting code references:**
- `../src/profile_data.py`
- Part 1 institution-cleaning script
- `../sql/02_load_warehouse.sql`
- `../sql/04_create_mart.sql`



## Question 2: The Company Crosswalk

**Question:** What share of complaints can you attribute to an FDIC-insured bank, by what method, and what is the unmatched remainder made of? Which large complaint targets are not banks, and what does that mean for any claim that compares banks on complaints?

### 2.1 Overview

**Source layers:** Normalized warehouse and analytics mart  
**Code references:** Company crosswalk logic from Part 1, `../sql/02_load_warehouse.sql`, and `../sql/04_create_mart.sql`

The CFPB complaint dataset identifies companies by name, while FDIC institution records identify banks using a unique certificate number (`CERT`).

Because the two datasets use different identifiers, complaints cannot be directly joined to bank financial records without additional matching logic.

To address this, a company crosswalk was developed to associate CFPB companies with FDIC-insured institutions wherever a sufficiently reliable match could be established.

The crosswalk also preserves companies that could not be matched, allowing them to remain part of the overall complaints analysis.

### 2.2 Crosswalk Coverage

**Source layer:** Normalized warehouse  
**Code reference:** Company crosswalk processing from Part 1

The final dataset contains 1,077,624 complaints associated with 4,118 distinct companies.

The crosswalk produced the following results:

| Match category | Companies | Complaints | Share of complaints |
|---|---:|---:|---:|
| Direct FDIC CERT match | 45 | 209,983 | 19.49% |
| Holding-company match | 86 | 354,533 | 32.90% |
| Ambiguous or unmatched | 3,987 | 513,108 | 47.61% |
| **Total** | **4,118** | **1,077,624** | **100%** |

The ambiguous or unmatched group contains nine companies classified as ambiguous and 3,978 classified as unmatched.

These results show that approximately **52.39% of complaints have some form of FDIC institution or holding-company association**.

However, only **19.49% of complaints can be attributed directly to a specific FDIC charter using CERT**.

This distinction is important because a holding company can own multiple banks, each with a different FDIC certificate number.

### 2.3 Matching Methods

**Source layer:** Normalized warehouse  
**Code reference:** Part 1 company-crosswalk implementation

The crosswalk records a match status and match method for each company.

The matching process uses company and institution identifiers to establish relationships between CFPB complaint companies and FDIC institutions.

The results distinguish three important outcomes:

**Direct bank attribution**

A company is associated with a specific FDIC CERT. These complaints can be linked to the corresponding bank's financial records.

**Holding-company attribution**

A company is associated with a banking organization or parent company, but not necessarily with an individual FDIC charter.

These matches provide useful organizational context but are not automatically suitable for charter-level financial comparisons.

**Ambiguous or unmatched attribution**

A company cannot be associated with a single FDIC institution confidently enough to assign its complaints to a bank.

These complaints remain in the dataset with no direct bank attribution.

The crosswalk's `match_method` field preserves more detailed information about how each match was established. The exact breakdown by method should be taken from the stored crosswalk rather than inferred from these broad categories.

### 2.4 The Unmatched Remainder

**Source layer:** Normalized warehouse and analytics mart  
**Code reference:** `../sql/04_create_mart.sql`

A total of 867,641 complaints do not have a direct FDIC CERT attribution.

This includes:

- 354,533 complaints associated with holding companies.
- 513,108 complaints belonging to ambiguous or unmatched companies.

Therefore, **80.51% of complaints cannot be directly assigned to an individual FDIC charter**.

This does not mean that all these complaints concern nonbank companies.

The unmatched population can contain several different situations:

- Companies operating outside the FDIC-insured banking system.
- Companies whose names do not correspond directly to an FDIC institution.
- Companies associated with broader financial organizations rather than individual bank charters.
- Companies for which the available information is insufficient or ambiguous.

The unmatched population was preserved rather than discarded.

This allows the report to show the complete CFPB complaint population while restricting bank-specific comparisons to records with reliable bank identifiers.

### 2.5 Large Complaint Targets That Are Not Banks

**Source layer:** Analytics mart  
**Code reference:** Supporting query against `mart.fact_complaint` and `mart.dim_company`

The crosswalk highlights the importance of distinguishing FDIC-insured banks from other financial services companies.

A company receiving a large number of CFPB complaints is not necessarily an FDIC-insured bank. Complaint targets may include financial technology companies, debt collectors, credit reporting organizations, loan servicers, and other financial service providers.

However, the largest specific nonbank complaint targets cannot be identified reliably from the aggregate crosswalk counts alone.

To establish this finding, companies without direct CERT attribution must first be ranked by complaint count. Their actual business type and FDIC status must then be checked before identifying them as nonbanks.

**Company-level ranking:** To be added from the supporting SQL query.

This distinction prevents unmatched bank subsidiaries or holding-company records from being incorrectly classified as nonbank businesses.

### 2.6 Implications for Comparing Banks

**Source layers:** Normalized warehouse and analytics mart  
**Code references:** `../sql/04_create_mart.sql` and the complaint-rate calculation in Power BI

The crosswalk has several important implications for bank comparisons.

**1. Complaint volume is affected by institution size.**

Large banks generally serve more customers and therefore have more opportunities to receive complaints.

Comparing raw complaint counts alone may make larger banks appear worse simply because they operate at a larger scale.

To address this, the bank scorecard uses complaints per $1 billion in deposits as a size-adjusted metric.

**2. Holding-company matches cannot automatically be assigned to individual banks.**

A holding company may own multiple FDIC-insured institutions.

Assigning all complaints associated with that parent to one charter could substantially overstate the complaint volume of that institution.

For this reason, charter-level comparisons use complaints with direct CERT attribution.

**3. Unmatched complaints must remain visible.**

Removing unmatched complaints entirely would understate total CFPB complaint activity and exclude a substantial portion of the financial services market.

The analytics mart therefore preserves unmatched records for overall complaint reporting.

**4. Match coverage limits the conclusions that can be drawn.**

Only 19.49% of complaints are directly attributed to individual FDIC charters.

This means that bank-level complaint rankings reflect the subset of complaints successfully matched to banks, not the entire CFPB complaint population.

Differences in company naming and ownership structure may also affect which organizations are successfully matched.

Consequently, the report should not interpret a low matched complaint count as proof that a bank receives few complaints overall.

### 2.7 Conclusion

The company crosswalk successfully connected 209,983 complaints to individual FDIC-insured bank charters and associated another 354,533 complaints with holding companies.

Together, these represent approximately 52.39% of the complaint dataset, although only the direct CERT matches support individual bank-level financial comparisons.

The remaining complaints were preserved rather than forced into potentially incorrect matches.

This approach prioritizes reliable attribution over artificially high matching coverage and ensures that bank comparisons clearly communicate the limitations of the underlying data.

**Supporting code references:**
- Part 1 company-crosswalk implementation
- `../sql/02_load_warehouse.sql`
- `../sql/04_create_mart.sql`
- Power BI complaint-rate DAX measure


## Question 3: Bank Consolidation

**Question:** How did the number of reporting banks and industry asset concentration change between 2008 and 2026? Were bank closures caused by failures, mergers, or both?

**Source layer:** Analytics mart and raw FDIC failures data  
**Code references:** `../sql/04_create_mart.sql`, Power BI Industry Overview, and FDIC failures data.

### Bank Count and Asset Concentration

The number of reporting banks declined substantially between 2008 and 2026, from approximately 8,500 to 4,100.

Over the same period, the largest 10 banks increased their share of industry assets from approximately 44% to over 50%, indicating greater industry concentration.

| Metric | 2008 | 2026 |
|---|---|---|
| Reporting banks | ~8,500 | ~4,100 |
| Top 10 asset share | ~44% | Over 50% |
| Top 100 asset share | Pending SQL results | Pending SQL results |

These figures are preliminary observations from the Power BI chart. Exact values still need to be confirmed.

### Failures vs. Mergers

**Source layers:** Raw FDIC failures data and financial warehouse.

Bank failures can be identified using the FDIC failures dataset. A bank that stops reporting financials without appearing in the failure records may have merged, changed its charter, or exited for another reason.

Because the project does not include a merger dataset, non-failure exits cannot be definitively classified as mergers.

**Conclusion:** The decline in reporting banks reflects consolidation and documented failures, but the available data does not establish the exact contribution of mergers.

**Code references:** `../sql/04_create_mart.sql` and the FDIC failures dataset.
