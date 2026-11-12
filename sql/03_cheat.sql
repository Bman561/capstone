-- PURPOSE:
-- This script validates the accuracy and completeness of our warehouse
-- after loading. It compares record counts between staging and warehouse,
-- checks for duplicate or missing primary keys, and investigates missing
-- lookup references. It also documents expected differences, such as
-- financial records excluded because their institutions could not be
-- matched. These read-only checks help confirm that our ETL process
-- worked correctly before using the data for reporting and analysis.


-- Bank Health Capstone | Warehouse validation
-- Run after 01_create_schema.sql and 02_load_warehouse.sql.
-- These are read-only checks to verify data quality and warehouse loading.



-- PURPOSE:
-- This script validates the data loaded into our normalized warehouse.
-- We compare staging and warehouse record counts, check primary-key
-- uniqueness, and investigate missing lookup references.
-- These checks help confirm that our ETL process preserved data
-- integrity and that any excluded or missing records are understood.
-- The script only reads data; it does not modify warehouse tables.


-- 1. Compare record counts between staging and warehouse tables.
-- This helps identify records that were excluded during loading.
-- Financials should have 5,294 fewer rows because records without
-- a matching institution CERT were excluded during loading.

SELECT
    dataset,
    staging_rows,
    warehouse_rows,

    -- Subtract warehouse rows from staging rows.
    -- A positive difference means fewer records reached the warehouse.
    staging_rows - warehouse_rows AS difference

FROM (

    -- Each SELECT returns the same three columns:
    -- dataset name, staging row count, and warehouse row count.
    -- COUNT(*) counts every row, including rows containing NULL values.

    SELECT 'Institutions' AS dataset,
           (SELECT COUNT(*) FROM staging.stg_institutions) AS staging_rows,
           (SELECT COUNT(*) FROM warehouse.institution) AS warehouse_rows

    -- UNION ALL stacks the results vertically into one table.
    -- Unlike UNION, it does not attempt to remove duplicate rows.
    UNION ALL SELECT 'Financials',
           (SELECT COUNT(*) FROM staging.stg_financials),
           (SELECT COUNT(*) FROM warehouse.financial)

    UNION ALL SELECT 'Failures',
           (SELECT COUNT(*) FROM staging.stg_failures),
           (SELECT COUNT(*) FROM warehouse.failure)

    UNION ALL SELECT 'Complaints',
           (SELECT COUNT(*) FROM staging.stg_complaints),
           (SELECT COUNT(*) FROM warehouse.complaint)

    UNION ALL SELECT 'Company Crosswalk',
           (SELECT COUNT(*) FROM staging.stg_crosswalk),
           (SELECT COUNT(*) FROM warehouse.company_crosswalk)

    UNION ALL SELECT 'Macro',
           (SELECT COUNT(*) FROM staging.stg_macro),
           (SELECT COUNT(*) FROM warehouse.macro)

-- The parentheses create a derived table containing all count results.
-- AS counts gives that temporary result a name for the outer SELECT.
) AS counts;


-- 2. Validate primary-key uniqueness and completeness.
-- Primary keys uniquely identify individual records.
-- Expected: 1,077,624 complaints with zero duplicate IDs.

SELECT
    COUNT(*) AS complaint_rows,

    -- COUNT(DISTINCT ...) counts unique, non-NULL complaint IDs.
    -- Subtracting it from the total helps detect duplicates.
    -- The primary-key constraint should already prevent duplicate IDs.
    COUNT(*) - COUNT(DISTINCT complaint_id) AS duplicate_complaint_ids

FROM warehouse.complaint;


-- Validate the composite primary key in the financial table.
-- A composite key uses multiple columns to identify a unique record.
-- Here, one financial record represents one bank at one reporting date.
-- Expected: 517,842 financial rows with no missing or duplicate keys.

SELECT
    COUNT(*) AS financial_rows,

    -- FILTER allows us to count only rows meeting a condition.
    -- Check whether CERT or REPDTE is missing.
    -- Both values are required to identify a bank-quarter record.
    COUNT(*) FILTER (
        WHERE cert IS NULL OR repdte IS NULL
    ) AS null_financial_keys,

    -- COUNT(DISTINCT (cert, repdte)) counts unique combinations.
    -- A bank can appear in multiple quarters, but the same bank
    -- should not have two records for the same reporting date.
    -- Subtracting unique combinations from total rows detects duplicates.
    COUNT(*) - COUNT(DISTINCT (cert, repdte)) AS duplicate_financial_keys

FROM warehouse.financial;


-- 3. Check for missing complaint lookup references.
-- Our normalized complaint table stores IDs that reference
-- descriptive lookup tables rather than repeating text values.
--
-- NULL lookup values do not automatically mean a foreign-key violation.
-- They can result from missing source data or unsuccessful matches.
--
-- Previous results: issue=5, response=1, state=15,483; others=0.

SELECT

    -- Count complaints without a matching company ID.
    COUNT(*) FILTER (WHERE company_id IS NULL) AS missing_company,

    -- Count complaints without a matching product ID.
    COUNT(*) FILTER (WHERE product_id IS NULL) AS missing_product,

    -- Count complaints without a matching issue ID.
    COUNT(*) FILTER (WHERE issue_id IS NULL) AS missing_issue,

    -- Count complaints without a matching company response ID.
    COUNT(*) FILTER (WHERE response_id IS NULL) AS missing_response,

    -- Count complaints without a matching submission channel ID.
    COUNT(*) FILTER (WHERE channel_id IS NULL) AS missing_channel,

    -- Count complaints without a matching state code.
    COUNT(*) FILTER (WHERE state_code IS NULL) AS missing_state

FROM warehouse.complaint;


-- 4. Investigate why some complaints have no matching state.
-- This separates missing source values from lookup mismatches.
-- Expected: 14,751 originally missing + 732 unmatched = 15,483.

SELECT

    -- Count complaints where the original state was NULL or empty.
    -- TRIM removes surrounding spaces before checking for blanks.
    COUNT(*) FILTER (
        WHERE "State" IS NULL OR TRIM("State") = ''
    ) AS originally_missing,

    -- Count complaints that provided a state code,
    -- but that code was not found in the warehouse state lookup.
    COUNT(*) FILTER (
        WHERE "State" IS NOT NULL
          AND TRIM("State") <> ''

          -- NOT EXISTS returns TRUE when the subquery finds no rows.
          -- For each complaint, PostgreSQL checks whether its state
          -- appears in the warehouse.state lookup table.
          --
          -- SELECT 1 is used because EXISTS only checks whether
          -- a matching row exists, not which columns it contains.
          --
          -- These codes were intentionally excluded from the
          -- FDIC-derived state lookup rather than added automatically.
          AND NOT EXISTS (
              SELECT 1
              FROM warehouse.state s

              -- Compare the lookup state code to the cleaned source value.
              -- s is an alias for the warehouse.state table.
              WHERE s.state_code = TRIM("State")
          )
    ) AS unmatched_state_codes

FROM staging.stg_complaints;


-- 5. Verify that the warehouse load is reproducible.
-- Reproducibility means running the same pipeline again with
-- unchanged source data should produce the same results.
--
-- Execute 02_load_warehouse.sql again, then rerun these checks.
-- Record counts, primary-key uniqueness, and lookup relationships
-- should remain consistent after the second load.
--
-- This is especially important because our warehouse uses
-- a full-refresh approach rather than appending new rows.
