"""
Run every query in sql/queries.sql against the cleaned data using SQLite
(no installation needed - SQLite ships with Python).

Run:     python src/run_sql.py        (run src/analysis.py first)
Output:  prints each result and saves it to outputs/sql_results/<query_name>.csv
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_FILE = ROOT / "data" / "processed" / "loan_data_clean.csv"
SQL_FILE = ROOT / "sql" / "queries.sql"
OUT_DIR = ROOT / "outputs" / "sql_results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_queries(path: Path) -> dict:
    """Split the .sql file on the '-- name: xxx' markers."""
    parts = re.split(r"^-- name:\s*(\w+)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def main():
    con = sqlite3.connect(":memory:")
    pd.read_csv(CLEAN_FILE).to_sql("loans", con, index=False)

    for name, sql in load_queries(SQL_FILE).items():
        result = pd.read_sql_query(sql, con)
        result.to_csv(OUT_DIR / f"{name}.csv", index=False)
        print(f"\n=== {name} ({len(result)} rows) ===")
        print(result.head(12).to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
