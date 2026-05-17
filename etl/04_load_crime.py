"""Load BOCSAR suburb-level crime data, compute crime_per_1000 using Census
G01 total population as the denominator, write stg_crime to DuckDB.

BOCSAR file structure (372 monthly columns from Jan 1995 to Dec 2025):
    Suburb, Offence category, Subcategory, Jan 1995, Feb 1995, ... Dec 2025

We sum the last 12 monthly columns (latest year) per suburb across all offence
types, then divide by Census 2021 total population to get crime_per_1000.

Suppression: suburbs with total_pop < 500 get NULL crime_per_1000 -- the rate
is too noisy when the denominator is small.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "sydney_scorecard.duckdb"
BOCSAR_ZIP = RAW / "bocsar" / "SuburbData.zip"

POP_SUPPRESSION_THRESHOLD = 500


def main() -> None:
    print(f"Inspecting BOCSAR header in {BOCSAR_ZIP.name} ...")
    with zipfile.ZipFile(BOCSAR_ZIP) as z:
        csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(csv_name) as f:
            header_df = pd.read_csv(f, nrows=0)
    all_cols = list(header_df.columns)
    cat_cols = all_cols[:3]  # Suburb, Offence category, Subcategory
    month_cols = all_cols[3:]
    last_12 = month_cols[-12:]
    print(f"  total cols: {len(all_cols)}  monthly: {len(month_cols)}")
    print(f"  last 12 months window: {last_12[0]} .. {last_12[-1]}")

    print("Reading suburb + last-12-month columns only ...")
    with zipfile.ZipFile(BOCSAR_ZIP) as z:
        with z.open(csv_name) as f:
            df = pd.read_csv(f, usecols=["Suburb"] + last_12)
    print(f"  raw rows (suburb x offence subcategory): {len(df):,}")

    # Sum across the 12 month columns and across all offence subcategories per suburb
    df["offences_12mo"] = df[last_12].sum(axis=1, numeric_only=True)
    suburb_crime = (
        df.groupby("Suburb", as_index=False)["offences_12mo"]
        .sum()
        .rename(columns={"Suburb": "suburb_name_bocsar"})
    )
    suburb_crime["suburb_name_norm"] = (
        suburb_crime["suburb_name_bocsar"].astype("string").str.strip().str.lower()
    )
    print(f"  unique suburbs in BOCSAR: {len(suburb_crime):,}")

    print(f"\nWriting to DuckDB: {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))
    con.register("crime_df", suburb_crime)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE stg_crime AS
        SELECT
            ds.suburb_id,
            ds.suburb_name,
            c.offences_12mo,
            g.total_pop,
            CASE
                WHEN g.total_pop IS NULL OR g.total_pop < {POP_SUPPRESSION_THRESHOLD}
                    THEN NULL
                ELSE c.offences_12mo::DOUBLE / g.total_pop * 1000.0
            END AS crime_per_1000
        FROM dim_suburb ds
        LEFT JOIN crime_df c ON c.suburb_name_norm = ds.suburb_name_norm
        LEFT JOIN stg_census_g01 g ON g.suburb_id = ds.suburb_id
        """
    )
    con.unregister("crime_df")

    n_rows = con.execute("SELECT COUNT(*) FROM stg_crime").fetchone()[0]
    n_matched = con.execute(
        "SELECT COUNT(*) FROM stg_crime WHERE offences_12mo IS NOT NULL"
    ).fetchone()[0]
    n_rated = con.execute(
        "SELECT COUNT(*) FROM stg_crime WHERE crime_per_1000 IS NOT NULL"
    ).fetchone()[0]
    print(f"  stg_crime rows: {n_rows}")
    print(f"  matched to BOCSAR: {n_matched}")
    print(f"  with computed crime_per_1000 (pop >= {POP_SUPPRESSION_THRESHOLD}): {n_rated}")
    print(f"  suppressed (small pop or no match): {n_rows - n_rated}")

    print("\nLowest crime suburbs (pop>=1000, top 5 safest):")
    safe = con.execute(
        """
        SELECT
            suburb_name,
            total_pop,
            offences_12mo,
            ROUND(crime_per_1000, 1) AS crime_per_1000
        FROM stg_crime
        WHERE crime_per_1000 IS NOT NULL AND total_pop >= 1000
        ORDER BY crime_per_1000 ASC
        LIMIT 5
        """
    ).df()
    print(safe.to_string(index=False))

    print("\nHighest crime suburbs (pop>=1000, top 5):")
    hot = con.execute(
        """
        SELECT
            suburb_name,
            total_pop,
            offences_12mo,
            ROUND(crime_per_1000, 1) AS crime_per_1000
        FROM stg_crime
        WHERE crime_per_1000 IS NOT NULL AND total_pop >= 1000
        ORDER BY crime_per_1000 DESC
        LIMIT 5
        """
    ).df()
    print(hot.to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()
