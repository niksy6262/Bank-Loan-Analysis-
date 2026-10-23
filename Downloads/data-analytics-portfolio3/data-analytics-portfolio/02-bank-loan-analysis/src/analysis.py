"""
Bank Loan Analysis
==================
Pipeline: load raw -> clean (logged) -> feature engineering -> KPIs -> charts -> insights

Key definitions (same as used in the SQL file and the Power BI measures):
  * Approval rate   = approved applications / all applications
  * Good loan       = approved loan that is 'Fully Paid' or 'Current'
  * Bad loan        = approved loan that is in 'Default'
  * Default rate    = bad loans / approved loans

Run:     python src/analysis.py        (run src/generate_data.py first)
Outputs: data/processed/loan_data_clean.csv, outputs/cleaning_log.md,
         outputs/kpis.json, outputs/insights.md, outputs/charts/*.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "loan_data_raw.csv"
CLEAN_FILE = ROOT / "data" / "processed" / "loan_data_clean.csv"
OUT_DIR = ROOT / "outputs"
CHART_DIR = OUT_DIR / "charts"
for folder in (CLEAN_FILE.parent, CHART_DIR):
    folder.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="notebook")
BLUE, ORANGE, GREEN, RED, GREY = "#2F5D8C", "#E07A2F", "#3E8E5A", "#C0392B", "#8A94A0"


def gapply(frame, col, func):
    """Apply func to every group of `col` and return a Series (works on old and new pandas)."""
    return pd.Series({key: func(group) for key, group in frame.groupby(col)})

CREDIT_LABELS = ["Below 600", "600-649", "650-699", "700-749", "750-799", "800+"]
DTI_LABELS = ["Below 30%", "30-40%", "40-50%", "50%+"]


def inr(x: float) -> str:
    if x >= 1e7:
        return f"Rs {x / 1e7:.2f} Cr"
    if x >= 1e5:
        return f"Rs {x / 1e5:.2f} L"
    return f"Rs {x:,.0f}"


# --------------------------------------------------------------------------- #
# CLEANING + FEATURES
# --------------------------------------------------------------------------- #
def clean(raw: pd.DataFrame):
    log = [("Rows in raw file", len(raw))]
    df = raw.copy()

    before = len(df)
    df = df.drop_duplicates()
    log.append(("Exact duplicate rows removed", before - len(df)))
    assert df["loan_id"].is_unique, "loan_id must be unique after de-duplication"

    df["state"] = df["state"].str.strip().str.title()

    # Missing income: fill with the median income of the same employment type
    n_missing = int(df["annual_income"].isna().sum())
    df["annual_income"] = df["annual_income"].fillna(
        df.groupby("employment_type")["annual_income"].transform("median"))
    log.append(("Missing annual_income filled with median of employment type", n_missing))

    df["application_date"] = pd.to_datetime(df["application_date"])
    df["application_month"] = df["application_date"].dt.strftime("%Y-%m")
    df["application_year"] = df["application_date"].dt.year

    # Business-rule check: rejected applications must have nothing disbursed
    assert (df.loc[df.application_status == "Rejected", "disbursed_amount"] == 0).all()

    df["credit_band"] = pd.cut(df["credit_score"], bins=[299, 599, 649, 699, 749, 799, 900],
                               labels=CREDIT_LABELS).astype(str)
    df["dti_band"] = pd.cut(df["dti_pct"], bins=[-np.inf, 30, 40, 50, np.inf], right=False,
                            labels=DTI_LABELS).astype(str)
    df["age_band"] = pd.cut(df["customer_age"], bins=[20, 30, 40, 50, 100],
                            labels=["21-30", "31-40", "41-50", "51+"]).astype(str)
    df["loan_group"] = np.select(
        [df["application_status"] == "Rejected", df["repayment_status"] == "Default"],
        ["Rejected", "Bad Loan"], default="Good Loan")

    log.append(("Rows in clean file", len(df)))
    return df.sort_values("application_date").reset_index(drop=True), log


# --------------------------------------------------------------------------- #
# KPIs
# --------------------------------------------------------------------------- #
def compute_kpis(df):
    approved = df[df["application_status"] == "Approved"]
    good = approved[approved["loan_group"] == "Good Loan"]
    bad = approved[approved["loan_group"] == "Bad Loan"]
    return {
        "total_applications": int(len(df)),
        "approved_loans": int(len(approved)),
        "approval_rate_pct": round(len(approved) / len(df) * 100, 2),
        "total_disbursed": int(approved["disbursed_amount"].sum()),
        "avg_loan_size": round(float(approved["disbursed_amount"].mean()), 0),
        "avg_interest_rate_pct": round(float(approved["interest_rate"].mean()), 2),
        "avg_dti_pct": round(float(approved["dti_pct"].mean()), 2),
        "good_loans": int(len(good)),
        "bad_loans": int(len(bad)),
        "good_loan_pct": round(len(good) / len(approved) * 100, 2),
        "default_rate_pct": round(len(bad) / len(approved) * 100, 2),
        "amount_at_risk_pct": round(bad["disbursed_amount"].sum() / approved["disbursed_amount"].sum() * 100, 2),
    }


def approval_rate(g):
    return (g["application_status"] == "Approved").mean() * 100


def default_rate(g):
    a = g[g["application_status"] == "Approved"]
    return (a["loan_group"] == "Bad Loan").mean() * 100 if len(a) else np.nan


# --------------------------------------------------------------------------- #
# CHARTS
# --------------------------------------------------------------------------- #
def save(fig, name):
    fig.tight_layout()
    fig.savefig(CHART_DIR / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


def bar_labels(ax, fmt="{:.1f}%"):
    for c in ax.containers:
        ax.bar_label(c, labels=[fmt.format(v) for v in c.datavalues], fontsize=9, padding=2)


def make_charts(df, kpis):
    approved = df[df["application_status"] == "Approved"]

    # 1. Good vs bad loans (donut)
    counts = approved["loan_group"].value_counts().reindex(["Good Loan", "Bad Loan"])
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.pie(counts, labels=[f"{k}\n{v:,}" for k, v in counts.items()], colors=[GREEN, RED],
           startangle=90, wedgeprops=dict(width=0.38, edgecolor="white"), autopct="%1.1f%%",
           pctdistance=0.81, textprops={"fontsize": 10})
    ax.set_title("Approved loans: good vs bad", fontweight="bold")
    save(fig, "01_good_vs_bad_loans.png")

    # 2. Approval and default rate by credit band
    by_credit = pd.DataFrame({
        "Approval rate": gapply(df, "credit_band", approval_rate),
        "Default rate": gapply(df, "credit_band", default_rate),
    }).loc[CREDIT_LABELS]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
    axes[0].bar(by_credit.index, by_credit["Approval rate"], color=BLUE)
    axes[0].set_title("Approval rate by credit score band (%)", fontweight="bold")
    axes[1].bar(by_credit.index, by_credit["Default rate"], color=RED)
    axes[1].set_title("Default rate by credit score band (%)", fontweight="bold")
    for ax in axes:
        bar_labels(ax)
    save(fig, "02_credit_band_approval_and_default.png")

    # 3. Default rate by DTI band
    by_dti = gapply(approved, "dti_band", default_rate).loc[DTI_LABELS]
    fig, ax = plt.subplots(figsize=(7, 4.3))
    ax.bar(by_dti.index, by_dti.values, color=ORANGE)
    bar_labels(ax)
    ax.set_title("Default rate by debt-to-income (DTI) band (%)", fontweight="bold")
    save(fig, "03_default_rate_by_dti.png")

    # 4. Loan purpose: amount disbursed + default rate
    purpose = approved.groupby("loan_purpose").agg(disbursed=("disbursed_amount", "sum")).join(
        gapply(approved, "loan_purpose", default_rate).rename("default_rate"))
    purpose = purpose.sort_values("disbursed", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
    axes[0].bar(purpose.index, purpose["disbursed"] / 1e7, color=BLUE)
    axes[0].set_title("Amount disbursed by purpose (Rs crore)", fontweight="bold")
    axes[1].bar(purpose.index, purpose["default_rate"], color=RED)
    axes[1].set_title("Default rate by purpose (%)", fontweight="bold")
    bar_labels(axes[0], "{:.1f}")
    bar_labels(axes[1])
    save(fig, "04_loan_purpose_analysis.png")

    # 5. Monthly applications vs approvals
    monthly = df.groupby("application_month").agg(
        applications=("loan_id", "count"),
        approved=("application_status", lambda s: (s == "Approved").sum()))
    fig, ax = plt.subplots(figsize=(11, 4.3))
    ax.plot(monthly.index, monthly["applications"], marker="o", color=BLUE, label="Applications")
    ax.plot(monthly.index, monthly["approved"], marker="o", color=GREEN, label="Approved")
    ax.set_xticks(range(0, len(monthly), 2))
    ax.set_xticklabels(monthly.index[::2], rotation=45, ha="right")
    ax.set_title("Monthly applications vs approved loans", fontweight="bold")
    ax.legend()
    save(fig, "05_monthly_applications.png")

    # 6. Employment type: approval vs default
    emp = pd.DataFrame({
        "Approval rate": gapply(df, "employment_type", approval_rate),
        "Default rate": gapply(df, "employment_type", default_rate),
    }).sort_values("Default rate", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    emp.plot(kind="bar", ax=ax, color=[BLUE, RED], rot=15)
    bar_labels(ax)
    ax.set_xlabel("")
    ax.set_title("Approval and default rate by employment type (%)", fontweight="bold")
    save(fig, "06_employment_type.png")

    # 7. State-wise disbursement
    state = approved.groupby("state")["disbursed_amount"].sum().sort_values(ascending=False) / 1e7
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(state.index, state.values, color=BLUE)
    ax.invert_yaxis()
    ax.bar_label(bars, labels=[f" Rs {v:.1f} Cr" for v in state.values], fontsize=9)
    ax.set_xlim(0, state.max() * 1.2)
    ax.set_title("Amount disbursed by state (Rs crore)", fontweight="bold")
    ax.grid(axis="y", visible=False)
    save(fig, "07_disbursed_by_state.png")

    # 8. Risk heatmap: credit band x DTI band
    heat = approved.pivot_table(index="credit_band", columns="dti_band", values="loan_group",
                                aggfunc=lambda s: (s == "Bad Loan").mean() * 100)
    heat = heat.reindex(index=CREDIT_LABELS, columns=DTI_LABELS)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    sns.heatmap(heat, annot=True, fmt=".1f", cmap="Reds", cbar_kws={"label": "Default rate (%)"}, ax=ax)
    ax.set_title("Default rate (%) - credit score band vs DTI band", fontweight="bold")
    ax.set_xlabel("Debt-to-income band")
    ax.set_ylabel("Credit score band")
    ax.tick_params(axis="y", rotation=0)
    save(fig, "08_risk_heatmap.png")


# --------------------------------------------------------------------------- #
# INSIGHTS
# --------------------------------------------------------------------------- #
def write_insights(df, k):
    approved = df[df["application_status"] == "Approved"]
    by_credit_appr = gapply(df, "credit_band", approval_rate)
    by_credit_def = gapply(approved, "credit_band", default_rate)
    by_dti_def = gapply(approved, "dti_band", default_rate)
    by_purpose_def = gapply(approved, "loan_purpose", default_rate).sort_values()
    by_emp_def = gapply(approved, "employment_type", default_rate).sort_values()
    purpose_amt = approved.groupby("loan_purpose")["disbursed_amount"].sum().sort_values(ascending=False)
    state_amt = approved.groupby("state")["disbursed_amount"].sum().sort_values(ascending=False)

    risky = approved[(approved["credit_score"] < 650) & (approved["dti_pct"] >= 40)]
    rest = approved.drop(risky.index)
    risky_def = (risky["loan_group"] == "Bad Loan").mean() * 100
    rest_def = (rest["loan_group"] == "Bad Loan").mean() * 100

    lines = [
        "# Key insights",
        "",
        "> Data is synthetic (see README). Insights describe patterns in this generated dataset.",
        "",
        "## Portfolio overview",
        f"- **{k['total_applications']:,}** applications received; **{k['approval_rate_pct']:.1f}%** approved "
        f"({k['approved_loans']:,} loans, {inr(k['total_disbursed'])} disbursed, average loan {inr(k['avg_loan_size'])}).",
        f"- **{k['good_loan_pct']:.1f}%** of approved loans are good (Fully Paid or Current) and "
        f"**{k['default_rate_pct']:.1f}%** are in default; defaulted loans hold "
        f"**{k['amount_at_risk_pct']:.1f}%** of the disbursed amount.",
        f"- {purpose_amt.index[0]} loans are the largest book ({inr(purpose_amt.iloc[0])}); "
        f"{state_amt.index[0]} is the top state ({inr(state_amt.iloc[0])}).",
        "",
        "## What drives approval and default",
        f"- Approval rate climbs from **{by_credit_appr['Below 600']:.1f}%** for scores below 600 to "
        f"**{by_credit_appr['800+']:.1f}%** for 800+.",
        f"- Default rate falls from **{by_credit_def['Below 600']:.1f}%** (score below 600) to "
        f"**{by_credit_def['800+']:.1f}%** (800+).",
        f"- Default rate rises with debt burden: **{by_dti_def['Below 30%']:.1f}%** when DTI is below 30% vs "
        f"**{by_dti_def['50%+']:.1f}%** when DTI is 50% or more.",
        f"- {by_purpose_def.index[-1]} loans default most ({by_purpose_def.iloc[-1]:.1f}%), "
        f"{by_purpose_def.index[0]} loans least ({by_purpose_def.iloc[0]:.1f}%).",
        f"- {by_emp_def.index[-1]} borrowers default most ({by_emp_def.iloc[-1]:.1f}%); "
        f"{by_emp_def.index[0]} borrowers least ({by_emp_def.iloc[0]:.1f}%).",
        "",
        "## High-risk segment",
        f"- Approved loans with credit score below 650 **and** DTI of 40% or more make up "
        f"**{len(risky) / len(approved) * 100:.1f}%** of approved loans but default at "
        f"**{risky_def:.1f}%** vs **{rest_def:.1f}%** for everyone else.",
        "",
        "## Recommendations",
        "1. Add a stricter review (or a higher interest rate / lower limit) for applicants with credit score < 650 and DTI >= 40%.",
        "2. Use DTI bands, not only credit score, in approval rules - the heatmap shows both matter together.",
        f"3. Monitor {by_purpose_def.index[-1]} and {by_emp_def.index[-1]} segments more closely with early-warning follow-ups.",
        "4. Track good-loan % and default rate monthly on the dashboard so risk changes are visible early.",
    ]
    (OUT_DIR / "insights.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    raw = pd.read_csv(RAW_FILE)
    df, log = clean(raw)
    df.to_csv(CLEAN_FILE, index=False)

    (OUT_DIR / "cleaning_log.md").write_text(
        "# Data cleaning log\n\n| Step | Rows |\n|---|---:|\n"
        + "\n".join(f"| {s} | {n:,} |" for s, n in log) + "\n", encoding="utf-8")

    kpis = compute_kpis(df)
    (OUT_DIR / "kpis.json").write_text(json.dumps(kpis, indent=2), encoding="utf-8")

    make_charts(df, kpis)
    write_insights(df, kpis)

    print("Cleaning log:")
    for s, n in log:
        print(f"  {s:<62}{n:>8,}")
    print("\nKPIs:", json.dumps(kpis, indent=2))
    print(f"\nCharts saved in {CHART_DIR}")


if __name__ == "__main__":
    main()
