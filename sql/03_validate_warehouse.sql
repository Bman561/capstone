-- Bank Health Capstone | Warehouse validation
-- Run after 01_create_schema.sql and 02_load_warehouse.sql.
-- Read-only checks: expected results are documented below.

-- 1. Reconcile the six source datasets against warehouse tables.
-- Financial difference should be 5,294: staging financial rows without
-- a matching institution are deliberately retained only in staging.
SELECT dataset, staging_rows, warehouse_rows,
       staging_rows - warehouse_rows AS difference
FROM (
    SELECT 'Institutions' AS dataset,
           (SELECT COUNT(*) FROM staging.stg_institutions) AS staging_rows,
           (SELECT COUNT(*) FROM warehouse.institution) AS warehouse_rows
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
) AS counts;

-- 2. Primary-key uniqueness and completeness.
-- Expected: 1,077,624 complaints, 0 duplicate IDs;
-- 517,842 financial rows, 0 null/duplicate composite keys.
SELECT COUNT(*) AS complaint_rows,
       COUNT(*) - COUNT(DISTINCT complaint_id) AS duplicate_complaint_ids
FROM warehouse.complaint;

SELECT COUNT(*) AS financial_rows,
       COUNT(*) FILTER (WHERE cert IS NULL OR repdte IS NULL) AS null_financial_keys,
       COUNT(*) - COUNT(DISTINCT (cert, repdte)) AS duplicate_financial_keys
FROM warehouse.financial;



-- 3. Missing complaint lookup values (not the same as invalid foreign keys).
-- Previously: issue=5, response=1, state=15,483; others=0.
SELECT
    COUNT(*) FILTER (WHERE company_id IS NULL) AS missing_company,
    COUNT(*) FILTER (WHERE product_id IS NULL) AS missing_product,
    COUNT(*) FILTER (WHERE issue_id IS NULL) AS missing_issue,
    COUNT(*) FILTER (WHERE response_id IS NULL) AS missing_response,
    COUNT(*) FILTER (WHERE channel_id IS NULL) AS missing_channel,
    COUNT(*) FILTER (WHERE state_code IS NULL) AS missing_state
FROM warehouse.complaint;

-- 4. Explain missing state references using original staging data.
-- Expected: 14,751 originally missing + 732 unmatched = 15,483.
-- Unmatched values were intentionally not added to the FDIC-derived state lookup.
SELECT
    COUNT(*) FILTER (WHERE "State" IS NULL OR TRIM("State") = '') AS originally_missing,
    COUNT(*) FILTER (
        WHERE "State" IS NOT NULL AND TRIM("State") <> ''
          AND NOT EXISTS (
              SELECT 1 FROM warehouse.state s
              WHERE s.state_code = TRIM("State")
          )
    ) AS unmatched_state_codes
FROM staging.stg_complaints;


-- Reproducibility is tested operationally, not by a read-only query:
-- Run 02_load_warehouse.sql again (with BEGIN, TRUNCATE, reload, COMMIT),
-- then rerun this file to confirm counts and relationships are consistent.
