"""Build fact_suburb_metrics in DuckDB and export the denormalised CSV that
Tableau Public will consume.

Aggregates the stg_* tables into a single row per suburb, computes the four
pillar raw subscores, clips outliers at the 1st / 99th percentile, and
min-max normalises each to a 0-100 score. The composite score itself is left
to Tableau (the weight sliders compute it live).

Outputs:
  - DuckDB table: fact_suburb_metrics
  - File:         tableau/suburb_scores.csv  (Tableau Public Edition input)
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "sydney_scorecard.duckdb"
TABLEAU_CSV = ROOT / "tableau" / "suburb_scores.csv"

PERSONA_BUDGET = 1_200_000  # Sam & Priya target buy price


def normalise_with_clip(series: pd.Series) -> pd.Series:
    """Clip to 1st/99th percentile, then min-max scale to 0-100. NaN stays NaN."""
    s = series.copy()
    if s.dropna().empty:
        return s
    p1, p99 = s.quantile(0.01), s.quantile(0.99)
    s = s.clip(lower=p1, upper=p99)
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series([50.0] * len(s), index=s.index)
    return 100.0 * (s - lo) / (hi - lo)


def zscore(series: pd.Series) -> pd.Series:
    mean = series.mean()
    std = series.std(ddof=0)
    if not std or pd.isna(std):
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mean) / std


def main() -> None:
    print(f"Connecting to {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))

    print("Building sales aggregates (12mo median + 5yr CAGR) ...")
    con.execute(
        """
        CREATE OR REPLACE TABLE stg_sales_agg AS
        WITH win_now AS (
            SELECT suburb_id, MEDIAN(price) AS p_now, COUNT(*) AS n_now
            FROM stg_vg_sales
            WHERE contract_date >= CURRENT_DATE - INTERVAL 1 YEAR
            GROUP BY suburb_id
        ),
        win_5yr AS (
            SELECT suburb_id, MEDIAN(price) AS p_5yr, COUNT(*) AS n_5yr
            FROM stg_vg_sales
            WHERE contract_date BETWEEN CURRENT_DATE - INTERVAL 5 YEAR
                                    AND CURRENT_DATE - INTERVAL 4 YEAR
            GROUP BY suburb_id
        )
        SELECT
            n.suburb_id,
            n.p_now      AS median_sale_price_12m,
            n.n_now      AS n_sales_12m,
            o.n_5yr      AS n_sales_5yr_ago,
            CASE
                WHEN o.p_5yr IS NULL OR o.p_5yr <= 0
                  OR n.p_now IS NULL OR n.p_now <= 0
                  OR n.n_now < 3 OR o.n_5yr < 3
                THEN NULL
                ELSE POWER(n.p_now::DOUBLE / o.p_5yr, 1.0 / 5.0) - 1.0
            END AS price_5yr_cagr
        FROM win_now n
        LEFT JOIN win_5yr o ON o.suburb_id = n.suburb_id
        """
    )

    print("Pulling combined fact rows into pandas ...")
    fact = con.execute(
        """
        SELECT
            ds.suburb_id,
            ds.suburb_name,
            ds.centroid_lat,
            ds.centroid_lon,
            ds.area_sqkm,
            g1.total_pop,
            g2.median_hhd_inc_weekly,
            g2.median_rent_weekly,
            g2.median_age,
            s.median_sale_price_12m,
            s.n_sales_12m,
            s.price_5yr_cagr,
            c.offences_12mo,
            c.crime_per_1000,
            cm.distance_km,
            cm.commute_minutes_cbd
        FROM dim_suburb ds
        LEFT JOIN stg_census_g01 g1 ON g1.suburb_id = ds.suburb_id
        LEFT JOIN stg_census_g02 g2 ON g2.suburb_id = ds.suburb_id
        LEFT JOIN stg_sales_agg  s  ON  s.suburb_id = ds.suburb_id
        LEFT JOIN stg_crime      c  ON  c.suburb_id = ds.suburb_id
        LEFT JOIN stg_commute    cm ON cm.suburb_id = ds.suburb_id
        """
    ).df()
    print(f"  rows: {len(fact)}")

    print("Computing raw subscores ...")
    fact["affordability_raw"] = (
        (PERSONA_BUDGET - fact["median_sale_price_12m"])
        / fact["median_sale_price_12m"]
    )
    fact["commute_raw"] = -fact["commute_minutes_cbd"]
    fact["growth_raw"] = fact["price_5yr_cagr"]

    # Lifestyle = average of z(low_crime) + z(income); skipna so we use either
    low_crime_z = zscore(-fact["crime_per_1000"])
    income_z = zscore(fact["median_hhd_inc_weekly"])
    fact["lifestyle_raw"] = pd.concat(
        [low_crime_z, income_z], axis=1
    ).mean(axis=1, skipna=True)

    print("Normalising to 0-100 (clip 1st/99th, min-max) ...")
    fact["affordability_norm"] = normalise_with_clip(fact["affordability_raw"])
    fact["commute_norm"] = normalise_with_clip(fact["commute_raw"])
    fact["lifestyle_norm"] = normalise_with_clip(fact["lifestyle_raw"])
    fact["growth_norm"] = normalise_with_clip(fact["growth_raw"])

    # Drop suburbs with no sales data at all -- they can't be ranked.
    before = len(fact)
    fact = fact[fact["median_sale_price_12m"].notna()].reset_index(drop=True)
    print(f"  dropped {before - len(fact)} suburbs with no recent sales")
    print(f"  final fact_suburb_metrics rows: {len(fact)}")

    print(f"\nWriting fact_suburb_metrics to DuckDB ...")
    con.register("fact_df", fact)
    con.execute("CREATE OR REPLACE TABLE fact_suburb_metrics AS SELECT * FROM fact_df")
    con.unregister("fact_df")

    print(f"Exporting Tableau CSV -> {TABLEAU_CSV.relative_to(ROOT)}")
    TABLEAU_CSV.parent.mkdir(parents=True, exist_ok=True)
    fact.to_csv(TABLEAU_CSV, index=False)

    print("\n=== Coverage check (non-NULL count per column) ===")
    coverage = fact.notna().sum().sort_values(ascending=False)
    print(coverage.to_string())

    print("\n=== Persona top-10 preview (weights 0.35/0.20/0.25/0.20) ===")
    preview = fact.assign(
        composite=(
            0.35 * fact["affordability_norm"].fillna(0)
            + 0.20 * fact["commute_norm"].fillna(0)
            + 0.25 * fact["lifestyle_norm"].fillna(0)
            + 0.20 * fact["growth_norm"].fillna(0)
        )
    )
    cols = [
        "suburb_name",
        "median_sale_price_12m",
        "commute_minutes_cbd",
        "crime_per_1000",
        "price_5yr_cagr",
        "composite",
    ]
    top10 = (
        preview[preview["median_sale_price_12m"] <= PERSONA_BUDGET]
        .sort_values("composite", ascending=False)
        .head(10)[cols]
    )
    print(top10.to_string(index=False))

    con.close()
    print("\nDone. fact_suburb_metrics ready for Tableau.")


if __name__ == "__main__":
    main()
