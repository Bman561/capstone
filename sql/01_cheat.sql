
-- PURPOSE:
-- This script creates the normalized PostgreSQL warehouse structure
-- for our Bank Health Capstone. It defines the tables, columns, data
-- types, primary keys, and foreign keys needed to store our cleaned
-- datasets. By separating information into related tables, we reduce
-- redundancy and maintain data integrity. This script only creates
-- the database structure; it does not load any actual records.
-- It must run before the warehouse loading script.



-- 1. Create a dedicated schema to organize our normalized tables.
-- IF NOT EXISTS prevents an error if the schema already exists.
CREATE SCHEMA IF NOT EXISTS warehouse;


-- 2. State lookup table.
-- Each two-character state code is stored once.
-- Other tables reference this table to maintain consistent state values.
CREATE TABLE IF NOT EXISTS warehouse.state (
    state_code VARCHAR(2) PRIMARY KEY
);


-- 3. Charter class lookup table.
-- Stores unique FDIC charter classifications.
CREATE TABLE IF NOT EXISTS warehouse.charter_class (
    class_code VARCHAR(10) PRIMARY KEY
);


-- 4. Institution table.
-- One record per FDIC-insured institution, identified by CERT.
CREATE TABLE IF NOT EXISTS warehouse.institution (
    cert INTEGER PRIMARY KEY,

    -- NOT NULL ensures every institution has a name.
    name TEXT NOT NULL,

    active BOOLEAN,
    established_date DATE,
    end_date DATE,

    state_code VARCHAR(2),
    class_code VARCHAR(10),

    city TEXT,
    zip VARCHAR(10),

    -- BIGINT supports larger integer identifiers than INTEGER.
    fed_rssd BIGINT,

    webaddr TEXT,
    namehcr TEXT,
    source_id TEXT,

    -- NUMERIC stores financial values with exact decimal precision.
    asset NUMERIC,
    dep NUMERIC,

    -- Foreign keys require state and charter codes to exist
    -- in their respective lookup tables.
    FOREIGN KEY (state_code)
        REFERENCES warehouse.state(state_code),

    FOREIGN KEY (class_code)
        REFERENCES warehouse.charter_class(class_code)
);


-- 5. Quarterly financials table.
-- Each bank can have multiple financial records across quarters.
CREATE TABLE IF NOT EXISTS warehouse.financial (
    cert INTEGER NOT NULL,
    repdte DATE NOT NULL,
    source_id TEXT,

    year INTEGER,
    quarter INTEGER,

    -- Balance sheet measures: assets, deposits, and equity.
    asset BIGINT,
    dep BIGINT,
    depdom BIGINT,
    depunins BIGINT,
    eq BIGINT,

    -- DOUBLE PRECISION stores floating-point ratios.
    eqv DOUBLE PRECISION,

    rbct1j BIGINT,
    p3asset BIGINT,
    p9asset BIGINT,

    -- Loan balances, credit quality, and provisions.
    lnlsnet BIGINT,
    lnlsgr BIGINT,
    lnre BIGINT,
    lnatres BIGINT,
    nclnls BIGINT,
    nclnlsr DOUBLE PRECISION,
    nperfv DOUBLE PRECISION,
    elnatr BIGINT,

    -- Original year-to-date income and expense measures.
    intinc BIGINT,
    eintexp BIGINT,
    nonii BIGINT,
    nonix BIGINT,
    netinc BIGINT,

    -- Quarterly income and expense values calculated in Python.
    -- The _q suffix distinguishes them from the original YTD fields.
    intinc_q BIGINT,
    eintexp_q BIGINT,
    nonii_q BIGINT,
    nonix_q BIGINT,
    netinc_q BIGINT,
    elnatr_q BIGINT,

    -- Financial performance ratios.
    nimy DOUBLE PRECISION,
    roa DOUBLE PRECISION,
    roe DOUBLE PRECISION,

    sc BIGINT,
    numemp BIGINT,
    offdom BIGINT,

    -- Composite primary key: one record per bank per reporting date.
    -- CERT alone cannot be unique because banks report every quarter.
    PRIMARY KEY (cert, repdte),

    -- Prevent financial records from referencing nonexistent banks.
    FOREIGN KEY (cert)
        REFERENCES warehouse.institution(cert),

    -- Only quarters 1 through 4 are valid.
    CHECK (quarter BETWEEN 1 AND 4)
);


-- 6. Bank failures table.
-- CERT cannot be the primary key because some banks appear
-- multiple times and some failure records have no CERT.
-- We use the source record ID instead.
CREATE TABLE IF NOT EXISTS warehouse.failure (
    id TEXT PRIMARY KEY,

    -- Nullable because some historical failures lack a CERT.
    cert INTEGER,

    name TEXT,
    city TEXT,
    cityst TEXT,
    pstalp TEXT,
    failyr BIGINT,
    faildate DATE,
    resdate DATE,

    -- Financial information recorded around the bank failure.
    qbfasset DOUBLE PRECISION,
    qbfdep DOUBLE PRECISION,
    cost DOUBLE PRECISION,
    uninsdep DOUBLE PRECISION,
    fund BIGINT,

    -- Acquiring bank and resolution information.
    bankno TEXT,
    bidname TEXT,
    bidcity TEXT,
    bidstate TEXT,
    bstatus TEXT,

    chclass TEXT,
    chclass1 TEXT,
    closcd TEXT,
    restype TEXT,
    restype1 TEXT,
    termi TEXT,
    fin TEXT,
    savr TEXT,
    fsl_prog TEXT,

    costmostrecentasof DATE,
    ptrdate DATE,
    brdate DATE,

    comments TEXT,
    url TEXT,

    -- A non-null CERT must reference a known institution.
    -- NULL is allowed when the bank cannot be identified.
    FOREIGN KEY (cert)
        REFERENCES warehouse.institution(cert)
);


-- 7. CFPB company lookup table.
-- Each unique company name receives an automatically generated ID.
CREATE TABLE IF NOT EXISTS warehouse.company (
    -- GENERATED ALWAYS AS IDENTITY lets PostgreSQL assign IDs.
    company_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- UNIQUE prevents duplicate company names.
    company_name TEXT NOT NULL UNIQUE
);


-- 8. Product lookup table.
-- Stores original CFPB product names and their standardized categories.
CREATE TABLE IF NOT EXISTS warehouse.product (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name TEXT NOT NULL UNIQUE,
    product_harmonized TEXT
);


-- 9. Issue lookup table.
-- A complaint issue can have an associated sub-issue.
CREATE TABLE IF NOT EXISTS warehouse.issue (
    issue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    issue_name TEXT NOT NULL,
    sub_issue TEXT,

    -- Treat NULL sub-issues as equal for uniqueness.
    -- Prevents duplicate issue/sub-issue combinations,
    -- even when both records have NULL sub_issue values.
    UNIQUE NULLS NOT DISTINCT (issue_name, sub_issue)
);


-- 10. Response type lookup table.
-- Stores unique company response categories.
CREATE TABLE IF NOT EXISTS warehouse.response_type (
    response_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    response_name TEXT NOT NULL UNIQUE
);


-- 11. Submission channel lookup table.
-- Stores channels such as web, phone, and mail.
CREATE TABLE IF NOT EXISTS warehouse.submission_channel (
    channel_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel_name TEXT NOT NULL UNIQUE
);


-- 12. Complaints table.
-- Each complaint is uniquely identified by its CFPB complaint ID.
CREATE TABLE IF NOT EXISTS warehouse.complaint (
    complaint_id BIGINT PRIMARY KEY,

    date_received DATE,
    date_sent_to_company DATE,

    -- These IDs connect complaints to their lookup tables.
    -- Using IDs instead of repeating text reduces redundancy.
    company_id BIGINT,
    product_id BIGINT,
    issue_id BIGINT,
    response_id BIGINT,
    channel_id BIGINT,

    sub_product TEXT,
    company_public_response TEXT,
    state_code VARCHAR(2),
    zip_code TEXT,
    tags TEXT,
    timely_response BOOLEAN,

    -- Foreign keys enforce valid relationships.
    -- NULL values are allowed when source information is missing.
    FOREIGN KEY (company_id)
        REFERENCES warehouse.company(company_id),

    FOREIGN KEY (product_id)
        REFERENCES warehouse.product(product_id),

    FOREIGN KEY (issue_id)
        REFERENCES warehouse.issue(issue_id),

    FOREIGN KEY (response_id)
        REFERENCES warehouse.response_type(response_id),

    FOREIGN KEY (channel_id)
        REFERENCES warehouse.submission_channel(channel_id),

    FOREIGN KEY (state_code)
        REFERENCES warehouse.state(state_code)
);


-- 13. Company crosswalk table.
-- Connects CFPB company records to FDIC institutions when possible.
CREATE TABLE IF NOT EXISTS warehouse.company_crosswalk (
    -- One crosswalk record per CFPB company.
    company_id BIGINT PRIMARY KEY,

    -- Nullable because not every company is an FDIC-insured bank.
    cert INTEGER,

    namehcr TEXT,

    -- Document how the company was matched and its reliability.
    match_method TEXT,
    match_source TEXT,
    match_status TEXT,

    -- Preserve possible matches and reasons for unmatched records.
    possible_certs TEXT,
    unmatched_category TEXT,
    complaint_count BIGINT,

    -- Ensure every crosswalk company exists in the company table.
    FOREIGN KEY (company_id)
        REFERENCES warehouse.company(company_id),

    -- Only valid FDIC certificates can be assigned.
    FOREIGN KEY (cert)
        REFERENCES warehouse.institution(cert)
);


-- 14. Macroeconomic indicators table.
-- One record per quarter, containing four FRED indicators.
CREATE TABLE IF NOT EXISTS warehouse.macro (
    quarter_end DATE PRIMARY KEY,

    -- 10-year Treasury yield.
    dgs10 DOUBLE PRECISION,

    -- Federal funds rate.
    fedfunds DOUBLE PRECISION,

    -- 30-year mortgage rate.
    mortgage30us DOUBLE PRECISION,

    -- Unemployment rate.
    unrate DOUBLE PRECISION
);
