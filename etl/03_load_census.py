"""Load 2021 Census GCP tables G01 (population) and G02 (medians) at SAL level
for Greater Sydney, write stg_census_g01 and stg_census_g02 to DuckDB.

G33 (Total Household Income by Composition) and G46 (Industry of Employment)
were originally scoped but G33 column dictionary does NOT include the tenure
columns we wanted (owner-occupier %) -- it's actually a household-income table.
The lifestyle pillar uses crime + Census-G02 median household income instead.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "sydney_scorecard.duckdb"
CENSUS_ZIP = RAW / "abs_census" / "2021_GCP_SAL_for_NSW_short-header.zip"


def load_census_table(table_id: str, cols: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(CENSUS_ZIP) as z:
        member = next(n for n in z.namelist() if f"_{table_id}_NSW_SAL.csv" in n)
        with z.open(member) as f:
            df = pd.read_csv(f, usecols=cols)
    df["suburb_id"] = (
        df["SAL_CODE_2021"].astype(str).str.replace("SAL", "", regex=False)
    )
    return df


def main() -> None:
    print("Loading Census G01 (population) ...")
    g01 = load_census_table("G01", ["SAL_CODE_2021", "Tot_P_P"])
    g01 = g01.rename(columns={"Tot_P_P": "total_pop"})
    print(f"  G01 rows (NSW): {len(g01):,}")

    print("Loading Census G02 (medians) ...")
    g02 = load_census_table(
        "G02",
        [
            "SAL_CODE_2021",
            "Median_tot_hhd_inc_weekly",
            "Median_rent_weekly",
            "Median_age_persons",
        ],
    )
    g02 = g02.rename(
        columns={
            "Median_tot_hhd_inc_weekly": "median_hhd_inc_weekly",
            "Median_rent_weekly": "median_rent_weekly",
            "Median_age_persons": "median_age",
        }
    )
    print(f"  G02 rows (NSW): {len(g02):,}")

    print(f"\nWriting to DuckDB: {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))
    con.register("g01_df", g01)
    con.register("g02_df", g02)

    con.execute(
        """
        CREATE OR REPLACE TABLE stg_census_g01 AS
        SELECT ds.suburb_id, ds.suburb_name, g.total_pop
        FROM g01_df g
        INNER JOIN dim_suburb ds ON ds.suburb_id = g.suburb_id
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE stg_census_g02 AS
        SELECT
            ds.suburb_id,
            ds.suburb_name,
            g.median_hhd_inc_weekly,
            g.median_rent_weekly,
            g.median_age
        FROM g02_df g
        INNER JOIN dim_suburb ds ON ds.suburb_id = g.suburb_id
        """
    )
    con.unregister("g01_df")
    con.unregister("g02_df")

    g01_n = con.execute("SELECT COUNT(*) FROM stg_census_g01").fetchone()[0]
    g02_n = con.execute("SELECT COUNT(*) FROM stg_census_g02").fetchone()[0]
    print(f"  stg_census_g01 rows: {g01_n}")
    print(f"  stg_census_g02 rows: {g02_n}")

    print("\nTop 5 Greater Sydney suburbs by median household income (pop > 1000):")
    sanity = con.execute(
        """
        SELECT
            ds.suburb_name,
            g1.total_pop,
            g2.median_hhd_inc_weekly AS hhd_inc_wk,
            g2.median_rent_weekly    AS rent_wk,
            g2.median_age
        FROM dim_suburb ds
        LEFT JOIN stg_census_g01 g1 ON g1.suburb_id = ds.suburb_id
        LEFT JOIN stg_census_g02 g2 ON g2.suburb_id = ds.suburb_id
        WHERE g1.total_pop > 1000
        ORDER BY g2.median_hhd_inc_weekly DESC NULLS LAST
        LIMIT 5
        """
    ).df()
    print(sanity.to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()
