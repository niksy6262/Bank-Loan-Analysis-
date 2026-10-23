# Power BI build guide - Bank Loan Dashboard

Needs Power BI Desktop (free, Windows). Plan 2-3 hours.
Result: `powerbi/bank_loan_dashboard.pbix` and screenshots in `powerbi/screenshots/`.

## Step 1 - Load and prepare
1. Get data > Text/CSV > `data/processed/loan_data_clean.csv`. Name the table `loans`.
2. Transform data: `application_date` = Date, `annual_income` and `interest_rate` = Decimal number, money columns = Whole number or Fixed decimal. Close & Apply.
3. Create the `Calendar` table and relationship described at the top of `DAX_measures.md`.

## Step 2 - Measures and sort columns
Add every measure and both sort columns from `DAX_measures.md`, then check the numbers in section 6.

## Step 3 - Page 1: Summary
- **KPI cards:** Total Applications, Approved Loans, Approval Rate %, Total Disbursed, Avg Interest Rate, Avg DTI %.
- **Good vs bad:** two cards (Good Loan %, Default Rate %) and a **donut chart** with `loan_group` (filter the visual to Approved loans only) and Count of loans.
- **Line + column chart:** X = `Calendar[YearMonth]`, columns = Total Disbursed, line = Approval Rate %.
- **Bar chart:** Total Disbursed by `loan_purpose`.
- **Slicers:** Year, State, Employment type, Loan purpose.

## Step 4 - Page 2: Risk analysis
- **Column chart:** Default Rate % by `credit_band` (sorted with the sort column).
- **Column chart:** Default Rate % by `dti_band`.
- **Matrix heatmap:** rows = `credit_band`, columns = `dti_band`, values = Default Rate %; apply Conditional formatting > Background colour (white to red).
- **Bar chart:** Default Rate % by `loan_purpose` and by `employment_type`.
- **Card:** High Risk Share % with a text box: "Credit score < 650 and DTI >= 40%".

## Step 5 - Polish and publish to GitHub
- Colour rule: blue = volume, green = good loans, red = risk/default.
- Sync slicers across pages; align visuals; add a title to every visual.
- Save `powerbi/bank_loan_dashboard.pbix`; save screenshots in `powerbi/screenshots/` and link them in `README.md`.
