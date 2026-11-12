
-- PURPOSE:
-- This script transforms our normalized warehouse into a reporting mart
-- designed for Power BI and analytical queries. It uses a star-schema
-- structure with dimension tables describing banks, companies, products,
-- and dates, alongside fact tables containing complaints, financial
-- measurements, and economic indicators. This makes the data easier to
-- filter, aggregate, and compare across different datasets. The mart
-- uses a full-refresh approach and prepares the data for dashboards
-- without requiring complex joins against the original warehouse.


--DESIGN THOUGHT PROCESS

--For Part 3, I decided to build a **star schema** because I wanted to separate how the data is stored from how it's actually analyzed.
--
--In Part 2, I created a normalized warehouse to maintain data integrity and reduce redundancy. But for reporting, I wanted something simpler that would work well with Power BI.
--
--So I created **dimension tables** for descriptive information, like banks, companies, products, and dates, and **fact tables** for the actual financial measurements, complaints, and macroeconomic data.
--
--One important decision I made was keeping financials and complaints in separate fact tables because they represent different levels of detail. Financials are recorded quarterly for each bank, while complaints are individual events.
 --I also standardized complaints to quarter-end dates so I could compare complaint trends with financial performance and economic conditions over the same periods.
--
--Ultimately, my goal was to create a reporting layer that was easier to query, avoided unnecessary duplication, and supported the kinds of comparisons I wanted to make in Power BI.

-- Part 3: Reporting Mart
-- Build a star schema from the normalized warehouse for reporting.

-- Run all changes in one transaction.
BEGIN;

-- Create a separate schema for analytical tables.
CREATE SCHEMA IF NOT EXISTS mart;



-- SECTION 1: CREATE ALL MART TABLES


-- DIMENSIONS describe the entities used to filter and group data.
-- FACT TABLES contain measurable events or financial values.


-- 1. Date dimension
-- One row per calendar date, with attributes for time-based analysis.
CREATE TABLE IF NOT EXISTS mart.dim_date (
    date_key DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    quarter_end DATE NOT NULL
);


-- 2. Bank dimension
-- Stores descriptive information about each FDIC institution.
CREATE TABLE IF NOT EXISTS mart.dim_bank (
    cert INTEGER PRIMARY KEY,
    bank_name TEXT NOT NULL,
    holding_company TEXT,
    state_code VARCHAR(2),
    city TEXT,
    charter_class VARCHAR(10),
    active BOOLEAN
);


-- 3. Company dimension
-- Includes CFPB companies and their FDIC matching information.
-- CERT may be NULL when a company has no confirmed bank match.
CREATE TABLE IF NOT EXISTS mart.dim_company (
    company_id BIGINT PRIMARY KEY,
    company_name TEXT NOT NULL,
    cert INTEGER,
    match_status TEXT,
    match_method TEXT,
    holding_company TEXT
);


-- 4. Product dimension
-- Keeps both original and harmonized CFPB product categories.
CREATE TABLE IF NOT EXISTS mart.dim_product (
    product_id BIGINT PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_harmonized TEXT
);


-- 5. Response dimension
-- Describes how companies responded to complaints.
CREATE TABLE IF NOT EXISTS mart.dim_response (
    response_id BIGINT PRIMARY KEY,
    response_name TEXT NOT NULL
);


-- 6. Submission channel dimension
-- Describes how consumers submitted complaints.
CREATE TABLE IF NOT EXISTS mart.dim_channel (
    channel_id BIGINT PRIMARY KEY,
    channel_name TEXT NOT NULL
);


-- 7. State dimension
-- Stores the state codes used for geographic reporting.
CREATE TABLE IF NOT EXISTS mart.dim_state (
    state_code VARCHAR(2) PRIMARY KEY
);


-- 8. Complaint fact table
-- One row per consumer complaint.
-- Contains dimension IDs and fields used to measure complaint activity.
CREATE TABLE IF NOT EXISTS mart.fact_complaint (
    complaint_id BIGINT PRIMARY KEY,
    date_received DATE,
    quarter_end DATE,
    company_id BIGINT,
    cert INTEGER,
    product_id BIGINT,
    response_id BIGINT,
    channel_id BIGINT,
    state_code VARCHAR(2),
    timely_response BOOLEAN
);


-- 9. Financial fact table
-- One row per bank per reporting quarter.
-- Stores financial balances, quarterly income, and performance ratios.
CREATE TABLE IF NOT EXISTS mart.fact_financial (
    cert INTEGER NOT NULL,
    quarter_end DATE NOT NULL,
    asset BIGINT,
    dep BIGINT,
    eq BIGINT,
    lnlsnet BIGINT,
    netinc_q BIGINT,
    intinc_q BIGINT,
    eintexp_q BIGINT,
    nonii_q BIGINT,
    nonix_q BIGINT,
    elnatr_q BIGINT,
    roa DOUBLE PRECISION,
    roe DOUBLE PRECISION,

    -- Composite key prevents duplicate bank-quarter records.
    PRIMARY KEY (cert, quarter_end)
);


-- 10. Macroeconomic fact table
-- One row per quarter containing economic indicators.
CREATE TABLE IF NOT EXISTS mart.fact_macro (
    quarter_end DATE PRIMARY KEY,
    dgs10 DOUBLE PRECISION,
    fedfunds DOUBLE PRECISION,
    mortgage30us DOUBLE PRECISION,
    unrate DOUBLE PRECISION
);



-- SECTION 2: CLEAR EXISTING MART DATA


-- Remove previous records before rebuilding the mart.
-- This is a full refresh rather than an incremental update.
TRUNCATE TABLE
    mart.fact_complaint,
    mart.fact_financial,
    mart.fact_macro,
    mart.dim_company,
    mart.dim_product,
    mart.dim_response,
    mart.dim_channel,
    mart.dim_state,
    mart.dim_bank,
    mart.dim_date;



-- SECTION 3: POPULATE MART TABLES


-- 11. Populate date dimension.
-- Generate a continuous calendar from 2006 through the latest
-- financial reporting date, including dates without transactions.
INSERT INTO mart.dim_date (
    date_key,
    year,
    quarter,
    month,
    day,
    quarter_end
)
SELECT
    d::DATE,

    -- EXTRACT retrieves individual parts of each generated date.
    EXTRACT(YEAR FROM d)::INTEGER,
    EXTRACT(QUARTER FROM d)::INTEGER,
    EXTRACT(MONTH FROM d)::INTEGER,
    EXTRACT(DAY FROM d)::INTEGER,

    -- Find the final day of the quarter containing this date.
    -- DATE_TRUNC finds the quarter's start.
    -- Add 3 months to reach the next quarter, then subtract 1 day.
    (
        DATE_TRUNC('quarter', d)
        + INTERVAL '3 months'
        - INTERVAL '1 day'
    )::DATE

-- generate_series creates one date per day between these boundaries.
FROM generate_series(
    '2006-01-01'::DATE,
    (
        SELECT MAX(repdte)
        FROM warehouse.financial
    ),
    INTERVAL '1 day'
) AS d

ON CONFLICT (date_key) DO NOTHING;


-- 12. Populate bank dimension.
-- Copy descriptive institution fields into reporting-friendly columns.
INSERT INTO mart.dim_bank (
    cert,
    bank_name,
    holding_company,
    state_code,
    city,
    charter_class,
    active
)
SELECT
    cert,
    name,
    namehcr,
    state_code,
    city,
    class_code,
    active
FROM warehouse.institution

-- EXCLUDED refers to the incoming row when a key conflict occurs.
ON CONFLICT (cert) DO UPDATE SET
    bank_name = EXCLUDED.bank_name,
    holding_company = EXCLUDED.holding_company,
    state_code = EXCLUDED.state_code,
    city = EXCLUDED.city,
    charter_class = EXCLUDED.charter_class,
    active = EXCLUDED.active;


-- 13. Populate company dimension.
-- Combine company names with their crosswalk matching details.
INSERT INTO mart.dim_company (
    company_id,
    company_name,
    cert,
    match_status,
    match_method,
    holding_company
)
SELECT
    c.company_id,
    c.company_name,
    cw.cert,
    cw.match_status,
    cw.match_method,
    cw.namehcr
FROM warehouse.company c

-- LEFT JOIN preserves companies even when no FDIC match exists.
LEFT JOIN warehouse.company_crosswalk cw
    ON c.company_id = cw.company_id

ON CONFLICT (company_id) DO UPDATE SET
    company_name = EXCLUDED.company_name,
    cert = EXCLUDED.cert,
    match_status = EXCLUDED.match_status,
    match_method = EXCLUDED.match_method,
    holding_company = EXCLUDED.holding_company;


-- 14. Populate product dimension.
INSERT INTO mart.dim_product (
    product_id,
    product_name,
    product_harmonized
)
SELECT
    product_id,
    product_name,
    product_harmonized
FROM warehouse.product
ON CONFLICT (product_id) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    product_harmonized = EXCLUDED.product_harmonized;


-- 15. Populate response dimension.
INSERT INTO mart.dim_response (
    response_id,
    response_name
)
SELECT
    response_id,
    response_name
FROM warehouse.response_type
ON CONFLICT (response_id) DO UPDATE SET
    response_name = EXCLUDED.response_name;


-- 16. Populate submission channel dimension.
INSERT INTO mart.dim_channel (
    channel_id,
    channel_name
)
SELECT
    channel_id,
    channel_name
FROM warehouse.submission_channel
ON CONFLICT (channel_id) DO UPDATE SET
    channel_name = EXCLUDED.channel_name;


-- 17. Populate state dimension.
INSERT INTO mart.dim_state (
    state_code
)
SELECT
    state_code
FROM warehouse.state
ON CONFLICT (state_code) DO NOTHING;


-- 18. Populate complaint fact table.
-- Convert individual complaints into reporting-ready records.
INSERT INTO mart.fact_complaint (
    complaint_id,
    date_received,
    quarter_end,
    company_id,
    cert,
    product_id,
    response_id,
    channel_id,
    state_code,
    timely_response
)
SELECT
    c.complaint_id,
    c.date_received,

    -- Assign each complaint to the final day of its calendar quarter.
    -- This allows complaints and quarterly financials to be compared.
    (
        DATE_TRUNC('quarter', c.date_received)
        + INTERVAL '3 months'
        - INTERVAL '1 day'
    )::DATE,

    c.company_id,

    -- Use the crosswalk to associate complaints with FDIC banks.
    -- Unmatched companies will have NULL CERT values.
    cw.cert,

    c.product_id,
    c.response_id,
    c.channel_id,
    c.state_code,
    c.timely_response

FROM warehouse.complaint c

-- Keep all complaints, including those without a bank match.
LEFT JOIN warehouse.company_crosswalk cw
    ON c.company_id = cw.company_id

-- Update existing complaint records if their values change.
ON CONFLICT (complaint_id) DO UPDATE SET
    date_received = EXCLUDED.date_received,
    quarter_end = EXCLUDED.quarter_end,
    company_id = EXCLUDED.company_id,
    cert = EXCLUDED.cert,
    product_id = EXCLUDED.product_id,
    response_id = EXCLUDED.response_id,
    channel_id = EXCLUDED.channel_id,
    state_code = EXCLUDED.state_code,
    timely_response = EXCLUDED.timely_response;


-- 19. Populate financial fact table.
-- Keep the measures needed for quarterly bank health analysis.
INSERT INTO mart.fact_financial (
    cert,
    quarter_end,
    asset,
    dep,
    eq,
    lnlsnet,
    netinc_q,
    intinc_q,
    eintexp_q,
    nonii_q,
    nonix_q,
    elnatr_q,
    roa,
    roe
)
SELECT
    cert,

    -- REPDTE becomes the reporting quarter-end date.
    repdte,

    asset,
    dep,
    eq,
    lnlsnet,
    netinc_q,
    intinc_q,
    eintexp_q,
    nonii_q,
    nonix_q,
    elnatr_q,
    roa,
    roe

FROM warehouse.financial

-- One record per bank-quarter; refresh measures on conflicts.
ON CONFLICT (cert, quarter_end) DO UPDATE SET
    asset = EXCLUDED.asset,
    dep = EXCLUDED.dep,
    eq = EXCLUDED.eq,
    lnlsnet = EXCLUDED.lnlsnet,
    netinc_q = EXCLUDED.netinc_q,
    intinc_q = EXCLUDED.intinc_q,
    eintexp_q = EXCLUDED.eintexp_q,
    nonii_q = EXCLUDED.nonii_q,
    nonix_q = EXCLUDED.nonix_q,
    elnatr_q = EXCLUDED.elnatr_q,
    roa = EXCLUDED.roa,
    roe = EXCLUDED.roe;


-- 20. Populate macroeconomic fact table.
-- These indicators can be compared with financial and complaint trends
-- using their shared quarter-end dates.
INSERT INTO mart.fact_macro (
    quarter_end,
    dgs10,
    fedfunds,
    mortgage30us,
    unrate
)
SELECT
    quarter_end,
    dgs10,
    fedfunds,
    mortgage30us,
    unrate
FROM warehouse.macro

ON CONFLICT (quarter_end) DO UPDATE SET
    dgs10 = EXCLUDED.dgs10,
    fedfunds = EXCLUDED.fedfunds,
    mortgage30us = EXCLUDED.mortgage30us,
    unrate = EXCLUDED.unrate;



-- Commit the completed mart rebuild.
COMMIT;
