
-- PURPOSE:
-- This script transfers our cleaned data from staging into the
-- normalized warehouse tables. It loads lookup tables first, followed
-- by institutions, financial records, complaints, and other datasets
-- while respecting their relationships. It uses a full-refresh approach,
-- clearing existing warehouse data before rebuilding it. The script
-- also handles duplicate keys and excludes financial records without
-- matching institutions to preserve referential integrity. All changes
-- run inside a transaction to keep the warehouse rebuild consistent.

-- A data warehouse is a centralized database that stores data from different sources in a structured and consistent way,
-- primarily for reporting and analysis.
--In our capstone, we took data from the FDIC, CFPB, and FRED, cleaned it using Python, and loaded it into our PostgreSQL warehouse.
--In this project, we took data from the FDIC, CFPB, and FRED, cleaned it using Python, and loaded it into our PostgreSQL warehouse.

-- Lookup tables are loaded before dependent tables so their IDs
-- are available when creating relationships.
-- The script uses a full-refresh approach and runs in a transaction
-- to keep the warehouse consistent if something goes wrong.

--DIFFERENCE BETWEEN INNER JOIN AND LEFT JOIN
--INNER JOIN returns only matching rows from both tables, while
--LEFT JOIN returns all rows from the left table and matched rows from the right table, filling unmatched right-side columns with NULL.




-- BEGIN starts a transaction so all changes can be committed together.
BEGIN;


-- Clear existing warehouse data before reloading.
-- RESTART IDENTITY resets automatically generated IDs to their starting values.
-- Multiple related tables are truncated together because of foreign key relationships.
-- This makes the warehouse rebuild repeatable without accumulating old records.
TRUNCATE TABLE
    warehouse.complaint,
    warehouse.company_crosswalk,
    warehouse.financial,
    warehouse.failure,
    warehouse.macro,
    warehouse.company,
    warehouse.product,
    warehouse.issue,
    warehouse.response_type,
    warehouse.submission_channel,
    warehouse.institution,
    warehouse.state,
    warehouse.charter_class
RESTART IDENTITY;


-- 1. Load unique state codes from the institutions staging table.
-- Lookup tables store distinct values rather than repeating them in every record.
INSERT INTO warehouse.state (state_code)

-- SELECT DISTINCT removes duplicate state codes.
SELECT DISTINCT "STALP"
FROM staging.stg_institutions

-- Exclude NULL and empty state codes.
-- TRIM removes leading and trailing whitespace.
WHERE "STALP" IS NOT NULL
  AND TRIM("STALP") <> ''

-- If the state code already exists, skip inserting it.
-- This avoids violating the unique constraint.
ON CONFLICT (state_code) DO NOTHING;


-- 2. Load unique FDIC charter classifications.
-- Each classification can later be referenced by institution records.
INSERT INTO warehouse.charter_class (class_code)
SELECT DISTINCT "BKCLASS"
FROM staging.stg_institutions
WHERE "BKCLASS" IS NOT NULL
  AND TRIM("BKCLASS") <> ''
ON CONFLICT (class_code) DO NOTHING;


-- 3. Load institution records into the warehouse.
-- CERT is the primary key identifying each FDIC institution.
-- Explicit column lists ensure staging fields map to the correct warehouse columns.
INSERT INTO warehouse.institution (
    cert,
    name,
    active,
    established_date,
    end_date,
    state_code,
    class_code,
    city,
    zip,
    fed_rssd,
    webaddr,
    namehcr,
    source_id,
    asset,
    dep
)
SELECT
    "CERT",
    "NAME",
    "ACTIVE",
    "ESTYMD",
    "ENDEFYMD",
    "STALP",

    -- TRIM removes whitespace, and NULLIF converts an empty string to NULL.
    -- This prevents blank charter classifications from being stored as valid codes.
    NULLIF(TRIM("BKCLASS"), ''),

    "CITY",
    "ZIP",

    -- Clean the identifier before converting it to a BIGINT.
    -- ::BIGINT is PostgreSQL's shorthand for CAST(... AS BIGINT).
    NULLIF(TRIM("FED_RSSD"), '')::BIGINT,

    "WEBADDR",
    "NAMEHCR",
    "ID",
    "ASSET",
    "DEP"
FROM staging.stg_institutions

-- An UPSERT inserts new rows or updates existing rows.
-- ON CONFLICT checks whether the incoming CERT already exists.
-- EXCLUDED refers to the new row that PostgreSQL attempted to insert.
ON CONFLICT (cert) DO UPDATE SET
    name = EXCLUDED.name,
    active = EXCLUDED.active,
    established_date = EXCLUDED.established_date,
    end_date = EXCLUDED.end_date,
    state_code = EXCLUDED.state_code,
    class_code = EXCLUDED.class_code,
    city = EXCLUDED.city,
    zip = EXCLUDED.zip,
    fed_rssd = EXCLUDED.fed_rssd,
    webaddr = EXCLUDED.webaddr,
    namehcr = EXCLUDED.namehcr,
    source_id = EXCLUDED.source_id,
    asset = EXCLUDED.asset,
    dep = EXCLUDED.dep;


-- 4. Load quarterly financial records.
-- The grain is one financial record per bank CERT and reporting date.
-- Together, CERT and REPDTE form the composite primary key.
INSERT INTO warehouse.financial (
    cert, repdte, source_id, year, quarter,
    asset, dep, depdom, depunins, eq, eqv, rbct1j,
    p3asset, p9asset, lnlsnet, lnlsgr, lnre,
    lnatres, nclnls, nclnlsr, nperfv, elnatr,
    intinc, eintexp, nonii, nonix, netinc,
    intinc_q, eintexp_q, nonii_q, nonix_q,
    netinc_q, elnatr_q, nimy, roa, roe,
    sc, numemp, offdom
)
SELECT
    f."CERT", f."REPDTE", f."ID", f."YEAR", f."QUARTER",
    f."ASSET", f."DEP", f."DEPDOM", f."DEPUNINS",
    f."EQ", f."EQV", f."RBCT1J", f."P3ASSET", f."P9ASSET",
    f."LNLSNET", f."LNLSGR", f."LNRE", f."LNATRES",
    f."NCLNLS", f."NCLNLSR", f."NPERFV", f."ELNATR",
    f."INTINC", f."EINTEXP", f."NONII", f."NONIX",
    f."NETINC", f."INTINC_Q", f."EINTEXP_Q",
    f."NONII_Q", f."NONIX_Q", f."NETINC_Q",
    f."ELNATR_Q", f."NIMY", f."ROA", f."ROE",
    f."SC", f."NUMEMP", f."OFFDOM"
FROM staging.stg_financials f

-- INNER JOIN only keeps financial records with a matching institution.
-- This protects referential integrity because financial.CERT
-- must reference an institution that exists in the warehouse.
-- The alias f represents staging financials, while i represents institutions.
INNER JOIN warehouse.institution i
    ON f."CERT" = i.cert

-- Skip duplicate bank/reporting-date combinations.
-- Unlike DO UPDATE, DO NOTHING leaves the existing row unchanged.
ON CONFLICT (cert, repdte) DO NOTHING;


-- 5. Load bank failure records.
-- Failures use their source ID as the primary key rather than CERT.
-- CERT is not used as the unique identifier because the failure
-- dataset represents failure events, not the institution master list.
INSERT INTO warehouse.failure (
    id, cert, name, city, cityst, pstalp,
    failyr, faildate, resdate,
    qbfasset, qbfdep, cost, uninsdep, fund,
    bankno, bidname, bidcity, bidstate, bstatus,
    chclass, chclass1, closcd, restype, restype1,
    termi, fin, savr, fsl_prog,
    costmostrecentasof, ptrdate, brdate,
    comments, url
)
SELECT
    f."ID", f."CERT", f."NAME", f."CITY",
    f."CITYST", f."PSTALP", f."FAILYR",
    f."FAILDATE", f."RESDATE",
    f."QBFASSET", f."QBFDEP", f."COST",
    f."UNINSDEP", f."FUND",
    f."BANKNO", f."BIDNAME", f."BIDCITY",
    f."BIDSTATE", f."BSTATUS",
    f."CHCLASS", f."CHCLASS1", f."CLOSCD",
    f."RESTYPE", f."RESTYPE1",
    f."TERMI", f."FIN", f."SAVR", f."FSL_PROG",
    f."COSTMOSTRECENTASOF", f."PTRDATE", f."BRDATE",
    f."COMMENTS", f."URL"
FROM staging.stg_failures f

-- Ignore records with duplicate failure IDs.
ON CONFLICT (id) DO NOTHING;


-- 6. Load unique CFPB company names from the crosswalk.
-- Each company receives a generated company_id in the warehouse.
-- Other tables can reference this ID instead of repeating the company name.
INSERT INTO warehouse.company (company_name)
SELECT DISTINCT TRIM("Company")
FROM staging.stg_crosswalk
WHERE "Company" IS NOT NULL
  AND TRIM("Company") <> ''
ON CONFLICT (company_name) DO NOTHING;


-- 7. Load the company crosswalk.
-- The crosswalk connects CFPB company names to FDIC institutions.
-- Some companies have a specific CERT, while others only match
-- a holding company or remain unmatched.
INSERT INTO warehouse.company_crosswalk (
    company_id,
    cert,
    namehcr,
    match_method,
    match_source,
    match_status,
    possible_certs,
    unmatched_category,
    complaint_count
)
SELECT
    c.company_id,
    cw."CERT",
    cw."NAMEHCR",
    cw."match_method",
    cw."match_source",
    cw."match_status",
    cw."possible_certs",
    cw."unmatched_category",
    cw."complaint_count"
FROM staging.stg_crosswalk cw

-- Match each company name to its generated warehouse company ID.
-- INNER JOIN ensures we only load crosswalk records
-- associated with a company in the company lookup table.
INNER JOIN warehouse.company c
    ON TRIM(cw."Company") = c.company_name

-- Update existing crosswalk records if matching information changes.
-- This preserves the latest matching results for each company.
ON CONFLICT (company_id) DO UPDATE SET
    cert = EXCLUDED.cert,
    namehcr = EXCLUDED.namehcr,
    match_method = EXCLUDED.match_method,
    match_source = EXCLUDED.match_source,
    match_status = EXCLUDED.match_status,
    possible_certs = EXCLUDED.possible_certs,
    unmatched_category = EXCLUDED.unmatched_category,
    complaint_count = EXCLUDED.complaint_count;


-- 8. Load the product lookup table.
-- Store original CFPB product names alongside harmonized categories.
-- This preserves the source labels while supporting standardized reporting.
INSERT INTO warehouse.product (
    product_name,
    product_harmonized
)
SELECT DISTINCT
    TRIM("Product"),
    "PRODUCT_HARMONIZED"
FROM staging.stg_complaints
WHERE "Product" IS NOT NULL
  AND TRIM("Product") <> ''

-- If the original product name exists, refresh its harmonized category.
ON CONFLICT (product_name) DO UPDATE SET
    product_harmonized = EXCLUDED.product_harmonized;


-- 9. Load unique issue and sub-issue combinations.
-- The combination matters because one issue can have multiple sub-issues.
INSERT INTO warehouse.issue (
    issue_name,
    sub_issue
)
SELECT DISTINCT
    "Issue",
    "Sub-issue"
FROM staging.stg_complaints
WHERE "Issue" IS NOT NULL

-- Avoid duplicate issue/sub-issue combinations.
ON CONFLICT (issue_name, sub_issue) DO NOTHING;


-- 10. Load unique company response types.
-- A lookup table prevents the same response text from being
-- repeated across every complaint record.
INSERT INTO warehouse.response_type (response_name)
SELECT DISTINCT TRIM("Company response to consumer")
FROM staging.stg_complaints
WHERE "Company response to consumer" IS NOT NULL
  AND TRIM("Company response to consumer") <> ''
ON CONFLICT (response_name) DO NOTHING;


-- 11. Load unique complaint submission channels.
-- Examples include different methods consumers use to submit complaints.
INSERT INTO warehouse.submission_channel (channel_name)
SELECT DISTINCT TRIM("Submitted via")
FROM staging.stg_complaints
WHERE "Submitted via" IS NOT NULL
  AND TRIM("Submitted via") <> ''
ON CONFLICT (channel_name) DO NOTHING;


-- 12. Load individual CFPB complaints.
-- The grain is one row per complaint ID.
-- Instead of storing repeated descriptive values, we use foreign keys
-- pointing to company, product, issue, response, and channel lookups.
INSERT INTO warehouse.complaint (
    complaint_id,
    date_received,
    date_sent_to_company,
    company_id,
    product_id,
    issue_id,
    response_id,
    channel_id,
    sub_product,
    company_public_response,
    zip_code,
    tags,
    state_code,
    timely_response
)
SELECT
    c."Complaint ID",
    c."Date received",
    c."Date sent to company",
    co.company_id,
    p.product_id,
    i.issue_id,
    r.response_id,
    sc.channel_id,
    c."Sub-product",
    c."Company public response",
    c."ZIP code",
    c."Tags",
    s.state_code,
    c."Timely response?"
FROM staging.stg_complaints c

-- LEFT JOIN preserves every staging complaint even when a lookup
-- value cannot be found. The unmatched lookup ID becomes NULL.
-- An INNER JOIN would exclude complaints without matching lookup rows.
LEFT JOIN warehouse.company co
    ON TRIM(c."Company") = co.company_name

LEFT JOIN warehouse.product p
    ON TRIM(c."Product") = p.product_name

LEFT JOIN warehouse.issue i
    ON c."Issue" = i.issue_name

    -- Normally, NULL = NULL does not evaluate to TRUE in SQL.
    -- IS NOT DISTINCT FROM treats two NULLs as equal.
    -- This allows issues with missing sub-issues to match correctly.
    AND c."Sub-issue" IS NOT DISTINCT FROM i.sub_issue

LEFT JOIN warehouse.response_type r
    ON TRIM(c."Company response to consumer") = r.response_name

LEFT JOIN warehouse.submission_channel sc
    ON TRIM(c."Submitted via") = sc.channel_name

LEFT JOIN warehouse.state s
    ON TRIM(c."State") = s.state_code

-- The complaint ID is unique, so duplicates are skipped.
ON CONFLICT (complaint_id) DO NOTHING;


-- 13. Load quarterly macroeconomic indicators.
-- The grain is one row per quarter-end date.
-- These indicators can later be compared with quarterly bank financials.
INSERT INTO warehouse.macro (
    quarter_end,
    dgs10,
    fedfunds,
    mortgage30us,
    unrate
)
SELECT
    -- ::DATE converts the staging value to a PostgreSQL date.
    quarter_end::DATE,
    "DGS10",
    "FEDFUNDS",
    "MORTGAGE30US",
    "UNRATE"
FROM staging.stg_macro

-- Update indicator values if the quarter already exists.
-- This keeps the latest macroeconomic observations in the warehouse.
ON CONFLICT (quarter_end) DO UPDATE SET
    dgs10 = EXCLUDED.dgs10,
    fedfunds = EXCLUDED.fedfunds,
    mortgage30us = EXCLUDED.mortgage30us,
    unrate = EXCLUDED.unrate;


-- COMMIT saves all warehouse changes together.
-- If an unhandled SQL error occurs, the transaction cannot be
-- committed and must be rolled back.
-- This prevents a partially completed warehouse refresh.
COMMIT;