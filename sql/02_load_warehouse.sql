
-- Rebuild warehouse from the latest staging data
BEGIN;

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

-- 1. Load state lookup
INSERT INTO warehouse.state (state_code)
SELECT DISTINCT "STALP"
FROM staging.stg_institutions
WHERE "STALP" IS NOT NULL
  AND TRIM("STALP") <> ''
ON CONFLICT (state_code) DO NOTHING;


-- 2. Load charter class lookup
INSERT INTO warehouse.charter_class (class_code)
SELECT DISTINCT "BKCLASS"
FROM staging.stg_institutions
WHERE "BKCLASS" IS NOT NULL
  AND TRIM("BKCLASS") <> ''
ON CONFLICT (class_code) DO NOTHING;


-- 3. Load institutions
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
    NULLIF(TRIM("BKCLASS"), ''),
    "CITY",
    "ZIP",
    NULLIF(TRIM("FED_RSSD"), '')::BIGINT,
    "WEBADDR",
    "NAMEHCR",
    "ID",
    "ASSET",
    "DEP"
FROM staging.stg_institutions
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



-- 4. Load quarterly financial records
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
INNER JOIN warehouse.institution i
    ON f."CERT" = i.cert
ON CONFLICT (cert, repdte) DO NOTHING;





-- 5. Load failure records
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
ON CONFLICT (id) DO NOTHING;




-- 6. Load CFPB companies
INSERT INTO warehouse.company (company_name)
SELECT DISTINCT TRIM("Company")
FROM staging.stg_crosswalk
WHERE "Company" IS NOT NULL
  AND TRIM("Company") <> ''
ON CONFLICT (company_name) DO NOTHING;




-- 7. Load company crosswalk
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
INNER JOIN warehouse.company c
    ON TRIM(cw."Company") = c.company_name
ON CONFLICT (company_id) DO UPDATE SET
    cert = EXCLUDED.cert,
    namehcr = EXCLUDED.namehcr,
    match_method = EXCLUDED.match_method,
    match_source = EXCLUDED.match_source,
    match_status = EXCLUDED.match_status,
    possible_certs = EXCLUDED.possible_certs,
    unmatched_category = EXCLUDED.unmatched_category,
    complaint_count = EXCLUDED.complaint_count;




-- 8. Load product lookup table
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
ON CONFLICT (product_name) DO UPDATE SET
    product_harmonized = EXCLUDED.product_harmonized;



-- 9. Load issue lookup table
INSERT INTO warehouse.issue (
    issue_name,
    sub_issue
)
SELECT DISTINCT
    "Issue",
    "Sub-issue"
FROM staging.stg_complaints
WHERE "Issue" IS NOT NULL
ON CONFLICT (issue_name, sub_issue) DO NOTHING;



-- 10. Load response type lookup table
INSERT INTO warehouse.response_type (response_name)
SELECT DISTINCT TRIM("Company response to consumer")
FROM staging.stg_complaints
WHERE "Company response to consumer" IS NOT NULL
  AND TRIM("Company response to consumer") <> ''
ON CONFLICT (response_name) DO NOTHING;



-- 11. Load submission channel lookup table
INSERT INTO warehouse.submission_channel (channel_name)
SELECT DISTINCT TRIM("Submitted via")
FROM staging.stg_complaints
WHERE "Submitted via" IS NOT NULL
  AND TRIM("Submitted via") <> ''
ON CONFLICT (channel_name) DO NOTHING;



-- 12. Load complaint records
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

LEFT JOIN warehouse.company co
    ON TRIM(c."Company") = co.company_name

LEFT JOIN warehouse.product p
    ON TRIM(c."Product") = p.product_name

LEFT JOIN warehouse.issue i
    ON c."Issue" = i.issue_name
    AND c."Sub-issue" IS NOT DISTINCT FROM i.sub_issue

LEFT JOIN warehouse.response_type r
    ON TRIM(c."Company response to consumer") = r.response_name

LEFT JOIN warehouse.submission_channel sc
    ON TRIM(c."Submitted via") = sc.channel_name

LEFT JOIN warehouse.state s
    ON TRIM(c."State") = s.state_code

ON CONFLICT (complaint_id) DO NOTHING;



-- 13. Load macroeconomic data
INSERT INTO warehouse.macro (
    quarter_end,
    dgs10,
    fedfunds,
    mortgage30us,
    unrate
)
SELECT
    quarter_end::DATE,
    "DGS10",
    "FEDFUNDS",
    "MORTGAGE30US",
    "UNRATE"
FROM staging.stg_macro
ON CONFLICT (quarter_end) DO UPDATE SET
    dgs10 = EXCLUDED.dgs10,
    fedfunds = EXCLUDED.fedfunds,
    mortgage30us = EXCLUDED.mortgage30us,
    unrate = EXCLUDED.unrate;


COMMIT;