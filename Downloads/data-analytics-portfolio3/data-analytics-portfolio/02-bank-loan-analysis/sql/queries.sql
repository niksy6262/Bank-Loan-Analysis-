-- ============================================================================
-- Bank Loan Analysis - SQL queries
-- Table: loans  (loaded from data/processed/loan_data_clean.csv by src/run_sql.py)
-- Columns: loan_id, application_date, state, customer_age, employment_type,
--   annual_income, credit_score, loan_purpose, loan_amount, tenure_months,
--   interest_rate, emi, dti_pct, application_status ('Approved'/'Rejected'),
--   repayment_status ('Fully Paid'/'Current'/'Default'/'Not Disbursed'),
--   disbursed_amount, application_month (YYYY-MM), application_year,
--   credit_band, dti_band, age_band,
--   loan_group ('Good Loan' / 'Bad Loan' / 'Rejected')
-- Definitions: good loan = approved and not in default; bad loan = default;
--              default rate = bad loans / approved loans.
-- Written in SQLite; works in PostgreSQL / MySQL with minor date-function changes.
-- ============================================================================

-- name: q01_kpi_summary
-- Headline KPIs (the cards on the Power BI dashboard)
SELECT
    COUNT(*)                                                                    AS total_applications,
    SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END)            AS approved_loans,
    ROUND(100.0 * SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) AS approval_rate_pct,
    SUM(disbursed_amount)                                                       AS total_disbursed,
    ROUND(AVG(CASE WHEN application_status = 'Approved' THEN disbursed_amount END), 0) AS avg_loan_size,
    ROUND(AVG(CASE WHEN application_status = 'Approved' THEN interest_rate END), 2)    AS avg_interest_rate_pct,
    ROUND(AVG(CASE WHEN application_status = 'Approved' THEN dti_pct END), 2)          AS avg_dti_pct,
    SUM(CASE WHEN loan_group = 'Good Loan' THEN 1 ELSE 0 END)                   AS good_loans,
    SUM(CASE WHEN loan_group = 'Bad Loan'  THEN 1 ELSE 0 END)                   AS bad_loans,
    ROUND(100.0 * SUM(CASE WHEN loan_group = 'Good Loan' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 2) AS good_loan_pct,
    ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 2) AS default_rate_pct
FROM loans;

-- name: q02_good_vs_bad_loan_summary
-- Count, amount and average rate for good vs bad loans
SELECT loan_group,
       COUNT(*)                          AS loans,
       SUM(disbursed_amount)             AS disbursed_amount,
       ROUND(100.0 * SUM(disbursed_amount) / SUM(SUM(disbursed_amount)) OVER (), 2) AS amount_share_pct,
       ROUND(AVG(interest_rate), 2)      AS avg_interest_rate,
       ROUND(AVG(dti_pct), 1)            AS avg_dti
FROM loans
WHERE application_status = 'Approved'
GROUP BY loan_group;

-- name: q03_approval_and_default_by_credit_band
-- How credit score drives approval and default
SELECT credit_band,
       COUNT(*)                                                                     AS applications,
       ROUND(100.0 * SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 1) AS approval_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 0), 1)      AS default_rate_pct
FROM loans
GROUP BY credit_band
ORDER BY MIN(credit_score);

-- name: q04_default_rate_by_dti_band
SELECT dti_band,
       SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END) AS approved_loans,
       ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 1) AS default_rate_pct
FROM loans
GROUP BY dti_band
ORDER BY MIN(dti_pct);

-- name: q05_purpose_portfolio
-- Disbursed amount, average rate and default rate per loan purpose
SELECT loan_purpose,
       SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END) AS approved_loans,
       SUM(disbursed_amount)                                            AS disbursed_amount,
       ROUND(AVG(CASE WHEN application_status = 'Approved' THEN interest_rate END), 2) AS avg_interest_rate,
       ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 1)    AS default_rate_pct
FROM loans
GROUP BY loan_purpose
ORDER BY disbursed_amount DESC;

-- name: q06_monthly_disbursement_running_total
-- Monthly disbursement with a running (cumulative) total - window function
WITH monthly AS (
    SELECT application_month, SUM(disbursed_amount) AS disbursed
    FROM loans
    GROUP BY application_month
)
SELECT application_month,
       disbursed,
       SUM(disbursed) OVER (ORDER BY application_month) AS cumulative_disbursed
FROM monthly
ORDER BY application_month;

-- name: q07_state_ranking
-- State ranking by disbursement with default rate
SELECT state,
       SUM(disbursed_amount) AS disbursed_amount,
       RANK() OVER (ORDER BY SUM(disbursed_amount) DESC) AS disbursement_rank,
       ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 1) AS default_rate_pct
FROM loans
GROUP BY state
ORDER BY disbursement_rank;

-- name: q08_risk_matrix_credit_x_dti
-- Default rate for every credit-band x DTI-band combination
SELECT credit_band, dti_band,
       SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END) AS approved_loans,
       ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 1) AS default_rate_pct
FROM loans
GROUP BY credit_band, dti_band
HAVING approved_loans >= 30
ORDER BY default_rate_pct DESC
LIMIT 10;

-- name: q09_high_risk_segment
-- Compare the high-risk segment (score < 650 and DTI >= 40) with everyone else
SELECT CASE WHEN credit_score < 650 AND dti_pct >= 40 THEN 'High risk' ELSE 'Other' END AS segment,
       COUNT(*)                          AS approved_loans,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_of_portfolio_pct,
       ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END) / COUNT(*), 1) AS default_rate_pct
FROM loans
WHERE application_status = 'Approved'
GROUP BY segment;

-- name: q10_employment_type_summary
SELECT employment_type,
       COUNT(*)                                                          AS applications,
       ROUND(100.0 * SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 1) AS approval_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN loan_group = 'Bad Loan' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN application_status = 'Approved' THEN 1 ELSE 0 END), 1)                  AS default_rate_pct,
       ROUND(AVG(annual_income), 0)                                       AS avg_annual_income
FROM loans
GROUP BY employment_type
ORDER BY default_rate_pct DESC;
