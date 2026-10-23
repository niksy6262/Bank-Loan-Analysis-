# DAX measures - Bank Loan Dashboard

Load `data/processed/loan_data_clean.csv` into Power BI as a table named `loans`.
Create a second table for dates (Modeling > New table):
```dax
Calendar =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2023, 1, 1 ), DATE ( 2024, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "MonthNum", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "YearMonth", FORMAT ( [Date], "YYYY-MM" )
)
```
Mark `Calendar` as a date table and relate `Calendar[Date]` (one) to `loans[application_date]` (many).
Create measures in a `_Measures` table.

## 1. Application and approval measures
```dax
Total Applications = COUNTROWS ( loans )
Approved Loans     = CALCULATE ( COUNTROWS ( loans ), loans[application_status] = "Approved" )
Approval Rate %    = DIVIDE ( [Approved Loans], [Total Applications] )
Total Disbursed    = SUM ( loans[disbursed_amount] )
Avg Loan Size      = DIVIDE ( [Total Disbursed], [Approved Loans] )
Avg Interest Rate  = CALCULATE ( AVERAGE ( loans[interest_rate] ), loans[application_status] = "Approved" )
Avg DTI %          = CALCULATE ( AVERAGE ( loans[dti_pct] ),       loans[application_status] = "Approved" )
```

## 2. Good loan / bad loan measures
```dax
Good Loans = CALCULATE ( COUNTROWS ( loans ), loans[loan_group] = "Good Loan" )
Bad Loans  = CALCULATE ( COUNTROWS ( loans ), loans[loan_group] = "Bad Loan" )
Good Loan % = DIVIDE ( [Good Loans], [Approved Loans] )
Default Rate % = DIVIDE ( [Bad Loans], [Approved Loans] )
Bad Loan Amount = CALCULATE ( SUM ( loans[disbursed_amount] ), loans[loan_group] = "Bad Loan" )
Amount at Risk % = DIVIDE ( [Bad Loan Amount], [Total Disbursed] )
```

## 3. Month-over-month
```dax
Disbursed Previous Month = CALCULATE ( [Total Disbursed], DATEADD ( 'Calendar'[Date], -1, MONTH ) )
Disbursed MoM % = DIVIDE ( [Total Disbursed] - [Disbursed Previous Month], [Disbursed Previous Month] )
```

## 4. High-risk segment
```dax
High Risk Loans =
CALCULATE (
    COUNTROWS ( loans ),
    loans[application_status] = "Approved",
    loans[credit_score] < 650,
    loans[dti_pct] >= 40
)
High Risk Share % = DIVIDE ( [High Risk Loans], [Approved Loans] )
```

## 5. Sort-order columns (so bands do not appear alphabetically)
Add these as calculated columns on `loans`, then Column tools > Sort by column:
```dax
Credit Band Sort =
SWITCH ( loans[credit_band], "Below 600", 1, "600-649", 2, "650-699", 3, "700-749", 4, "750-799", 5, "800+", 6 )

DTI Band Sort =
SWITCH ( loans[dti_band], "Below 30%", 1, "30-40%", 2, "40-50%", 3, "50%+", 4 )
```
Sort `credit_band` by `Credit Band Sort`, and `dti_band` by `DTI Band Sort`.

## 6. Checks - your cards must match these (no filters applied)
| Measure | Expected |
|---|---|
| Total Applications | 10,000 |
| Approved Loans | 6,794 |
| Approval Rate % | 67.94% |
| Total Disbursed | 7,490,935,000 |
| Good Loans / Bad Loans | 6,349 / 445 |
| Good Loan % / Default Rate % | 93.45% / 6.55% |
| Amount at Risk % | 5.82% |
| Avg Interest Rate / Avg DTI % | 10.55 / 42.17 |

The same values are in `outputs/kpis.json`, in the SQL result `outputs/sql_results/q01_kpi_summary.csv` and on the Excel `Summary` sheet.
