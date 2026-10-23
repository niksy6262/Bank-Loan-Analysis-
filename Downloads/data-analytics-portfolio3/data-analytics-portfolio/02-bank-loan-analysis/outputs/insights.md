# Key insights

> Data is synthetic (see README). Insights describe patterns in this generated dataset.

## Portfolio overview
- **10,000** applications received; **67.9%** approved (6,794 loans, Rs 749.09 Cr disbursed, average loan Rs 11.03 L).
- **93.5%** of approved loans are good (Fully Paid or Current) and **6.5%** are in default; defaulted loans hold **5.8%** of the disbursed amount.
- Home loans are the largest book (Rs 355.60 Cr); Maharashtra is the top state (Rs 169.06 Cr).

## What drives approval and default
- Approval rate climbs from **38.8%** for scores below 600 to **88.7%** for 800+.
- Default rate falls from **16.5%** (score below 600) to **3.1%** (800+).
- Default rate rises with debt burden: **3.1%** when DTI is below 30% vs **11.9%** when DTI is 50% or more.
- Business loans default most (11.4%), Education loans least (3.3%).
- Freelancer borrowers default most (10.7%); Business Owner borrowers least (5.2%).

## High-risk segment
- Approved loans with credit score below 650 **and** DTI of 40% or more make up **9.2%** of approved loans but default at **18.2%** vs **5.4%** for everyone else.

## Recommendations
1. Add a stricter review (or a higher interest rate / lower limit) for applicants with credit score < 650 and DTI >= 40%.
2. Use DTI bands, not only credit score, in approval rules - the heatmap shows both matter together.
3. Monitor Business and Freelancer segments more closely with early-warning follow-ups.
4. Track good-loan % and default rate monthly on the dashboard so risk changes are visible early.
