# Data dictionary

Eight files in `../raw`, exactly as published: no renamed columns, no type conversion, no date fixing, no deduplication, no blank filling. Everything below describes the files **as they are**, not as they should be. Where a definition and the data disagree, the data wins; note the disagreement in your report.

| File | Grain | Rows | Window |
|---|---|---|---|
| `fdic_institutions.json` | One row per FDIC-insured institution, ever | 27,835 | All history |
| `fdic_financials.csv` | One row per institution per quarter-end | 523,136 | 2006 Q1 to 2026 Q2 |
| `fdic_failures.csv` | One row per failure or assistance transaction | 4,117 | 1934 onward |
| `cfpb_complaints.csv` | One row per complaint | 1,077,624 | Received 2019-01-01 to 2026-06-30 |
| `fred_FEDFUNDS.csv` | One row per month | 867 | 1954 onward |
| `fred_UNRATE.csv` | One row per month | 945 | 1948 onward |
| `fred_MORTGAGE30US.csv` | One row per week | 2,898 | 1971 onward |
| `fred_DGS10.csv` | One row per trading day | 16,898 | 1962 onward |

Conventions that apply across the FDIC files:

- **Dollar amounts are in thousands of dollars.**
- **`CERT`** is the FDIC certificate number and the key that links institutions, financials and failures. It is a number in the JSON file and a text column in the CSVs.
- Income-statement fields in the financials are **year-to-date**, not for the quarter (see that file's notes).
- Ratios are percentages, already multiplied by 100 (`ROA` of `1.2` means 1.2 percent).

---

## `fdic_institutions.json`

The FDIC's directory of every institution it has ever insured. The file is a JSON array of records shaped `{"data": {...}, "score": 1}`; the fields below live inside `data`. A field that is null for an institution is absent from that record rather than present with a null value.

| Field | Type as it appears | Meaning |
|---|---|---|
| `CERT` | integer | FDIC certificate number, unique per institution |
| `NAME` | text | Legal name of the institution |
| `CITY` | text | City of the main office |
| `STALP` | text | Two-letter state or territory of the main office |
| `ZIP` | text | Five-digit ZIP of the main office |
| `ASSET` | integer | Total assets, thousands of dollars, as of the most recent report |
| `DEP` | integer | Total deposits, thousands of dollars, as of the most recent report |
| `ACTIVE` | integer | 1 = open and FDIC-insured, 0 = closed or no longer insured |
| `BKCLASS` | text | Charter class code; see the code table at the end |
| `NAMEHCR` | text | Name of the regulatory top holder: the holding company that owns or controls 25 percent or more of the institution. Written in the FDIC's holding-company convention, which differs from `NAME` |
| `FED_RSSD` | text | Federal Reserve RSSD identifier for the institution |
| `ESTYMD` | text, `MM/DD/YYYY` | Date the institution began operations |
| `ENDEFYMD` | text, `MM/DD/YYYY` | Date of the last structural event; for closed institutions, the day it became inactive. `12/31/9999` is the FDIC's value for an institution with no end date |
| `WEBADDR` | text | Primary web address from the most recent Call Report |
| `ID` | text | The API's own record identifier |

## `fdic_financials.csv`

Quarterly figures from the Call Reports that every insured institution files. One row per institution per quarter-end. Columns are in the order the API returned them, which is not the order below.

**Year-to-date, not quarterly.** `NETINC`, `INTINC`, `EINTEXP`, `NONII`, `NONIX` and `ELNATR` accumulate through the calendar year: the 30 September row holds January to September, and the 31 December row holds the full year. The balance-sheet fields (`ASSET`, `DEP`, `EQ`, loans, securities) and the counts are point-in-time at the quarter end. `ROA`, `ROE` and `NIMY` are annualized by the FDIC.

| Field | Type as it appears | Meaning |
|---|---|---|
| `CERT` | integer | FDIC certificate number |
| `REPDTE` | text, `YYYYMMDD` | Quarter-end report date |
| `ID` | text | API record identifier, `<CERT>_<REPDTE>` |
| `ASSET` | integer | Total assets, excluding off-balance-sheet items. Thousands |
| `DEP` | integer | Total deposits, domestic and foreign offices. Thousands |
| `DEPDOM` | integer | Deposits in domestic offices. Thousands |
| `DEPUNINS` | integer | Estimated uninsured deposits in domestic offices, as reported by the bank. Thousands |
| `NETINC` | integer | Net income, **year-to-date**. Thousands; can be negative |
| `ROA` | decimal | Return on assets: annualized net income as a percent of average assets |
| `ROE` | decimal | Return on equity: annualized net income as a percent of average equity |
| `EQ` | integer | Total equity capital. Thousands; can be negative |
| `EQV` | decimal | Equity capital as a percent of assets |
| `RBCT1J` | integer | Tier 1 risk-based capital, adjusted for the prompt corrective action rules. Thousands |
| `LNLSNET` | integer | Loans and leases, net of the allowance for losses. Thousands |
| `LNLSGR` | integer | Loans and leases, gross. Thousands |
| `LNRE` | integer | Loans secured by real estate. Thousands |
| `LNATRES` | integer | Allowance for loan and lease losses. Thousands |
| `NCLNLS` | integer | Noncurrent loans and leases: 90 or more days past due or in nonaccrual. Thousands |
| `NCLNLSR` | decimal | Noncurrent loans as a percent of gross loans |
| `NPERFV` | decimal | Nonperforming assets as a percent of total assets |
| `P3ASSET` | integer | Assets 30 to 89 days past due. Thousands |
| `P9ASSET` | integer | Assets 90 or more days past due. Thousands |
| `ELNATR` | integer | Provision for credit losses, **year-to-date**. Thousands; can be negative (a release of reserves) |
| `SC` | integer | Securities held. Thousands |
| `INTINC` | integer | Total interest income, **year-to-date**. Thousands |
| `EINTEXP` | integer | Total interest expense, **year-to-date**. Thousands |
| `NIMY` | decimal | Net interest margin: annualized net interest income as a percent of average earning assets |
| `NONII` | integer | Total noninterest income, **year-to-date**. Thousands |
| `NONIX` | integer | Total noninterest expense, **year-to-date**. Thousands |
| `NUMEMP` | integer | Number of full-time-equivalent employees |
| `OFFDOM` | integer | Number of domestic offices, including the head office |

## `fdic_failures.csv`

Every bank failure and FDIC assistance transaction since 1934, with every column the API returns. Many columns are legacy fields from the 1980s and 1990s crises. Several have no published definition; those are marked *undocumented* and described from the data.

| Field | Type as it appears | Meaning |
|---|---|---|
| `CERT` | text | FDIC certificate number of the failed institution |
| `NAME` | text | Legal name of the failed institution |
| `CITY` | text | City of the main office |
| `PSTALP` | text | Two-letter state |
| `CITYST` | text | City and state together, `"CITY, ST"` |
| `FAILDATE` | text, `M/D/YYYY` | Date the institution ceased to exist as a private going concern |
| `FAILYR` | text | Four-digit year of `FAILDATE` |
| `RESDATE` | text, `M/D/YYYY` | Date of resolution |
| `RESTYPE` | text | `FAILURE` or `ASSISTANCE` |
| `RESTYPE1` | text | Transaction type code. `PA` purchase and assumption of all deposits; `PI` purchase of insured deposits only; `P&A` purchase and assumption, deposit scope unknown; `PO` payout to insured depositors, no successor; `IDT` insured deposit transfer; `A/A` assistance, charter survives; `MGR`, `ABT`, `OBAM`, `DINB`, `REP` rarer assistance and bridge-bank forms |
| `CHCLASS1` | text | Charter class at failure; same codes as `BKCLASS` |
| `CHCLASS` | text | *Undocumented.* A charter class code |
| `QBFASSET` | text | Total assets at the last report before failure. Thousands |
| `QBFDEP` | text | Total deposits at the last report before failure. Thousands |
| `COST` | text | Estimated loss to the insurance fund. Thousands |
| `COSTMOSTRECENTASOF` | text, `YYYY-MM-DD` | *Undocumented.* Date the loss estimate was last updated |
| `UNINSDEP` | text | *Undocumented.* Uninsured deposits at failure |
| `SAVR` | text | Insurance fund that covered the failure: `FDIC`, `BIF`, `SAIF`, `DIF` (FDIC funds over time), `FSLIC`, `RTC` |
| `FUND` | text | Numeric code for the insurance fund |
| `BIDNAME` | text | Name of the acquiring institution |
| `BIDCITY` | text | City of the acquirer |
| `BIDSTATE` | text | State of the acquirer |
| `FIN` | text | Financial Institution Number assigned to the receivership |
| `BSTATUS` | text | *Undocumented.* Receivership status code |
| `CLOSCD` | text | *Undocumented.* Closing code |
| `TERMI` | text | *Undocumented.* Receivership termination flag |
| `FSL_PROG` | text | *Undocumented.* Program code for 1980s thrift resolutions |
| `PTRDATE` | text, `YYYY-MM-DD` | Date of pass-through receivership (RTC only) |
| `BRDATE` | text, `YYYY-MM-DD` | *Undocumented.* Bridge-bank date |
| `BANKNO` | text | *Undocumented.* A legacy bank number |
| `URL` | text | Link to the FDIC's press release or failed-bank page |
| `COMMENTS` | text | Free-text notes from the FDIC |
| `ID` | text | API record identifier |

## `cfpb_complaints.csv`

Complaints the CFPB received and sent to companies, from its public Consumer Complaint Database. Rows were kept where `Date received` falls between 2019-01-01 and 2026-06-30 and `Product` is one of the deposit, credit card, mortgage, vehicle loan or personal loan products. Every column the CFPB publishes is present. The CFPB no longer publishes the consumer's narrative text, so there is none.

| Field | Type as it appears | Meaning |
|---|---|---|
| `Complaint ID` | integer | Unique complaint identifier |
| `Date received` | text, `YYYY-MM-DD` | Date the CFPB received the complaint |
| `Date sent to company` | text, `YYYY-MM-DD` | Date the CFPB forwarded it to the company |
| `Product` | text | Product category the consumer chose. The CFPB renamed its product labels in August 2023, so a product may appear under two names across the window |
| `Sub-product` | text | Finer product category |
| `Issue` | text | Issue category the consumer chose; the set depends on `Product` |
| `Sub-issue` | text | Finer issue category |
| `Company` | text | Company the complaint is about, as the CFPB names it. There is no FDIC key |
| `Company public response` | text | Optional public response the company chose from a fixed list |
| `Company response to consumer` | text | How the company closed the complaint: `Closed with explanation`, `Closed with monetary relief`, `Closed with non-monetary relief`, `Untimely response`, `In progress` |
| `Timely response?` | text | `Yes` or `No`: whether the company responded within the CFPB's deadline |
| `State` | text | State of the consumer's mailing address, as a two-letter code |
| `ZIP code` | text | Consumer's mailing ZIP. The CFPB masks the last two digits (`304XX`) where the area is small |
| `Tags` | text | `Older American`, `Servicemember`, or both |
| `Submitted via` | text | Channel: `Web`, `Referral`, `Phone`, `Postal mail`, `Fax`, `Email` |

## `fred_*.csv`

Four economic series from the Federal Reserve Bank of St. Louis, two columns each: `observation_date` (`YYYY-MM-DD`) and the series value as a decimal in percent. Where FRED has no observation for a date, the value cell is empty.

| File | Series | Frequency | Dated |
|---|---|---|---|
| `fred_FEDFUNDS.csv` | `FEDFUNDS`, effective federal funds rate, monthly average | Monthly | First of the month |
| `fred_UNRATE.csv` | `UNRATE`, civilian unemployment rate, seasonally adjusted | Monthly | First of the month |
| `fred_MORTGAGE30US.csv` | `MORTGAGE30US`, average 30-year fixed mortgage rate | Weekly | Thursdays |
| `fred_DGS10.csv` | `DGS10`, 10-year Treasury constant-maturity yield | Daily | Trading days |

---

## Charter class codes (`BKCLASS`, `CHCLASS1`)

| Code | Meaning |
|---|---|
| `N` | Commercial bank, national charter, Federal Reserve member, supervised by the OCC |
| `NM` | Commercial bank, state charter, Federal Reserve non-member, supervised by the FDIC |
| `SM` | Commercial bank, state charter, Federal Reserve member, supervised by the Federal Reserve |
| `SB` | Federal savings bank, supervised by the OCC (the OTS before July 2011) |
| `SI` | State-chartered stock savings bank, supervised by the FDIC |
| `SL` | State-chartered stock savings and loan association, supervised by the FDIC (the OTS before July 2011) |
| `OI` | Insured US branch of a foreign-chartered institution |
| `NC` | Non-insured commercial bank or trust company |
| `NS` | Non-insured stock savings bank |
| `CU` | Credit union |
