
-- 1. Create warehouse schema
CREATE SCHEMA IF NOT EXISTS warehouse;


-- 2. Create state lookup table
CREATE TABLE IF NOT EXISTS warehouse.state (
    state_code VARCHAR(2) PRIMARY KEY
);


-- 3. Create charter class lookup table
CREATE TABLE IF NOT EXISTS warehouse.charter_class (
    class_code VARCHAR(10) PRIMARY KEY
);


-- 4. Create institution table
CREATE TABLE IF NOT EXISTS warehouse.institution (
    cert INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    active BOOLEAN,
    established_date DATE,
    end_date DATE,

    state_code VARCHAR(2),
    class_code VARCHAR(10),

    city TEXT,
    zip VARCHAR(10),
    fed_rssd BIGINT,
    webaddr TEXT,
    namehcr TEXT,
    source_id TEXT,
    asset NUMERIC,
    dep NUMERIC,

    FOREIGN KEY (state_code)
        REFERENCES warehouse.state(state_code),

    FOREIGN KEY (class_code)
        REFERENCES warehouse.charter_class(class_code)
);


-- 5. Create quarterly financials table
CREATE TABLE IF NOT EXISTS warehouse.financial (
    cert INTEGER NOT NULL,
    repdte DATE NOT NULL,
    source_id TEXT,

    year INTEGER,
    quarter INTEGER,

    asset BIGINT,
    dep BIGINT,
    depdom BIGINT,
    depunins BIGINT,
    eq BIGINT,
    eqv DOUBLE PRECISION,
    rbct1j BIGINT,
    p3asset BIGINT,
    p9asset BIGINT,

    lnlsnet BIGINT,
    lnlsgr BIGINT,
    lnre BIGINT,
    lnatres BIGINT,
    nclnls BIGINT,
    nclnlsr DOUBLE PRECISION,
    nperfv DOUBLE PRECISION,
    elnatr BIGINT,

    intinc BIGINT,
    eintexp BIGINT,
    nonii BIGINT,
    nonix BIGINT,
    netinc BIGINT,

    intinc_q BIGINT,
    eintexp_q BIGINT,
    nonii_q BIGINT,
    nonix_q BIGINT,
    netinc_q BIGINT,
    elnatr_q BIGINT,

    nimy DOUBLE PRECISION,
    roa DOUBLE PRECISION,
    roe DOUBLE PRECISION,

    sc BIGINT,
    numemp BIGINT,
    offdom BIGINT,

    PRIMARY KEY (cert, repdte),

    FOREIGN KEY (cert)
        REFERENCES warehouse.institution(cert),

    CHECK (quarter BETWEEN 1 AND 4)
);

-- Unlike financials, a bank can appear multiple times in the failures dataset, and some failure records have no CERT.
-- So we can't use CERT as the primary key. Going to use Id as primary key here.


-- 6. Create failures table
CREATE TABLE IF NOT EXISTS warehouse.failure (
    id TEXT PRIMARY KEY,
    cert INTEGER,

    name TEXT,
    city TEXT,
    cityst TEXT,
    pstalp TEXT,
    failyr BIGINT,
    faildate DATE,
    resdate DATE,

    qbfasset DOUBLE PRECISION,
    qbfdep DOUBLE PRECISION,
    cost DOUBLE PRECISION,
    uninsdep DOUBLE PRECISION,
    fund BIGINT,

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

    FOREIGN KEY (cert)
        REFERENCES warehouse.institution(cert)
);


-- 7. Create CFPB company table
CREATE TABLE IF NOT EXISTS warehouse.company (
    company_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE
);


-- 8. Create product lookup table
CREATE TABLE IF NOT EXISTS warehouse.product (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name TEXT NOT NULL UNIQUE,
    product_harmonized TEXT
);


-- 9. Create issue lookup table
CREATE TABLE IF NOT EXISTS warehouse.issue (
    issue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    issue_name TEXT NOT NULL,
    sub_issue TEXT,

    UNIQUE NULLS NOT DISTINCT (issue_name, sub_issue)
);


-- 10. Create company response type lookup table
CREATE TABLE IF NOT EXISTS warehouse.response_type (
    response_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    response_name TEXT NOT NULL UNIQUE
);


-- 11. Create submission channel lookup table
CREATE TABLE IF NOT EXISTS warehouse.submission_channel (
    channel_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel_name TEXT NOT NULL UNIQUE
);



-- 12. Create complaints table
CREATE TABLE IF NOT EXISTS warehouse.complaint (
    complaint_id BIGINT PRIMARY KEY,
    date_received DATE,
    date_sent_to_company DATE,

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



-- 13. Create company crosswalk table
CREATE TABLE IF NOT EXISTS warehouse.company_crosswalk (
    company_id BIGINT PRIMARY KEY,
    cert INTEGER,

    namehcr TEXT,
    match_method TEXT,
    match_source TEXT,
    match_status TEXT,
    possible_certs TEXT,
    unmatched_category TEXT,
    complaint_count BIGINT,

    FOREIGN KEY (company_id)
        REFERENCES warehouse.company(company_id),

    FOREIGN KEY (cert)
        REFERENCES warehouse.institution(cert)
);


-- 14. Create quarterly macroeconomic indicators table
CREATE TABLE IF NOT EXISTS warehouse.macro (
    quarter_end DATE PRIMARY KEY,
    dgs10 DOUBLE PRECISION,
    fedfunds DOUBLE PRECISION,
    mortgage30us DOUBLE PRECISION,
    unrate DOUBLE PRECISION
);
