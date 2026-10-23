"""
Generate a synthetic bank loan-application dataset (10,000 applications).

Patterns built in (so the analysis has real signals to find):
  * approval depends on credit score and debt-to-income (DTI) ratio
  * defaults are more likely with low credit score, high DTI, high interest rate,
    unsecured purposes (Personal / Business) and less stable income
  * older loans with short tenures show as 'Fully Paid', the rest as 'Current'
The raw file also contains typical errors (missing income, duplicate rows,
inconsistent state names) to be fixed in analysis.py.

Run:     python src/generate_data.py
Output:  data/raw/loan_data_raw.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
N = 10000
SNAPSHOT = pd.Timestamp("2025-01-31")          # date the data was "extracted"

rng = np.random.default_rng(SEED)
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

sigmoid = lambda x: 1 / (1 + np.exp(-x))

# ---------------------------------------------------------------- applicants
STATES = ["Maharashtra", "Karnataka", "Delhi", "Tamil Nadu",
          "Gujarat", "Telangana", "Uttar Pradesh", "West Bengal"]
STATE_W = np.array([.22, .14, .12, .12, .11, .10, .10, .09])
EMP = ["Salaried", "Self-Employed", "Business Owner", "Freelancer"]
EMP_W = [.55, .20, .15, .10]
EMP_MEDIAN_INCOME = {"Salaried": 600_000, "Self-Employed": 750_000,
                     "Business Owner": 1_200_000, "Freelancer": 500_000}

state = rng.choice(STATES, size=N, p=STATE_W / STATE_W.sum())
employment = rng.choice(EMP, size=N, p=EMP_W)
age = np.clip(rng.normal(36, 9, N), 21, 65).round().astype(int)

income = np.array([EMP_MEDIAN_INCOME[e] for e in employment]) * np.exp(rng.normal(0, 0.45, N))
income = (np.clip(income, 240_000, 6_000_000) / 1000).round() * 1000          # annual, INR

z_income = (np.log(income) - np.log(650_000)) / 0.5
credit = np.clip(690 + 45 * z_income + rng.normal(0, 65, N), 300, 900).round().astype(int)

dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
app_date = np.sort(rng.choice(dates.values, size=N))
app_date = pd.to_datetime(app_date)

# --------------------------------------------------------------------- loans
PURPOSES = ["Personal", "Home", "Auto", "Education", "Business"]
PURPOSE_W = [.30, .20, .18, .12, .20]
purpose = rng.choice(PURPOSES, size=N, p=PURPOSE_W)

INCOME_MULT = {"Personal": (0.3, 0.9), "Home": (2.0, 5.0), "Auto": (0.6, 1.2),
               "Education": (0.4, 1.0), "Business": (0.8, 2.5)}
TENURES = {"Personal": [12, 24, 36, 48, 60], "Home": [120, 180, 240],
           "Auto": [36, 48, 60, 84], "Education": [36, 60, 84, 120],
           "Business": [24, 36, 60, 84]}
BASE_RATE = {"Personal": 13.0, "Home": 8.5, "Auto": 9.5, "Education": 9.5, "Business": 12.0}

amount = np.zeros(N)
tenure = np.zeros(N, dtype=int)
rate = np.zeros(N)
for p in PURPOSES:
    idx = np.where(purpose == p)[0]
    lo, hi = INCOME_MULT[p]
    amount[idx] = income[idx] * rng.uniform(lo, hi, len(idx))
    tenure[idx] = rng.choice(TENURES[p], size=len(idx))
    rate[idx] = BASE_RATE[p]
amount = np.clip((amount / 5000).round() * 5000, 50_000, 15_000_000)           # INR
rate = np.clip(rate + (690 - credit) * 0.012 + rng.normal(0, 0.6, N), 7.0, 24.0).round(2)

r = rate / 1200
emi = amount * r * (1 + r) ** tenure / ((1 + r) ** tenure - 1)
monthly_income = income / 12
existing_debt = monthly_income * rng.beta(1.5, 5, N) * 0.6
dti = np.clip((existing_debt + emi) / monthly_income * 100, 5, 120).round(1)

# ----------------------------------------------------------- decision + outcome
p_approve = sigmoid(1.9 + 0.012 * (credit - 690) - 0.06 * (dti - 35))
approved = rng.random(N) < p_approve

PURPOSE_RISK = {"Personal": .25, "Home": -.40, "Auto": -.10, "Education": .10, "Business": .30}
EMP_RISK = {"Salaried": -.20, "Self-Employed": .10, "Business Owner": .10, "Freelancer": .30}
logit_default = (-3.1 - 0.010 * (credit - 700) + 0.035 * (dti - 35) + 0.08 * (rate - 12)
                 + np.array([PURPOSE_RISK[p] for p in purpose])
                 + np.array([EMP_RISK[e] for e in employment]))
defaulted = rng.random(N) < sigmoid(logit_default)

months_old = (SNAPSHOT - app_date).days / 30.4
# a loan is Fully Paid if its tenure is over, or the customer closed it early (prepayment)
fully_paid = (tenure <= months_old - 1) | ((months_old >= 12) & (rng.random(N) < 0.30))
repay_status = np.where(~approved, "Not Disbursed",
                np.where(defaulted, "Default",
                np.where(fully_paid, "Fully Paid", "Current")))

df = pd.DataFrame({
    "loan_id": [f"LN{i:06d}" for i in range(1, N + 1)],
    "application_date": app_date.strftime("%Y-%m-%d"),
    "state": state,
    "customer_age": age,
    "employment_type": employment,
    "annual_income": income,
    "credit_score": credit,
    "loan_purpose": purpose,
    "loan_amount": amount.astype(int),
    "tenure_months": tenure,
    "interest_rate": rate,
    "emi": emi.round(0).astype(int),
    "dti_pct": dti,
    "application_status": np.where(approved, "Approved", "Rejected"),
    "repayment_status": repay_status,
    "disbursed_amount": np.where(approved, amount, 0).astype(int),
})

# ---------------------------------------------------------- inject data errors
idx = rng.choice(df.index, size=int(0.015 * N), replace=False)           # missing income
df.loc[idx, "annual_income"] = np.nan
idx = rng.choice(df.index, size=int(0.03 * N), replace=False)            # messy state names
df.loc[idx, "state"] = df.loc[idx, "state"].map(lambda s: [s.upper(), s.lower(), f" {s} "][rng.integers(0, 3)])
dupes = df.sample(n=int(0.005 * N), random_state=SEED)                    # duplicate rows
df = pd.concat([df, dupes]).sample(frac=1, random_state=SEED).reset_index(drop=True)

df.to_csv(OUT_DIR / "loan_data_raw.csv", index=False)
print(f"Saved {len(df):,} rows -> {OUT_DIR / 'loan_data_raw.csv'}")
print("Approval rate: %.1f%%" % (approved.mean() * 100))
print("Default rate among approved: %.1f%%" % ((repay_status == 'Default').sum() / approved.sum() * 100))
print(pd.Series(repay_status).value_counts().to_dict())
