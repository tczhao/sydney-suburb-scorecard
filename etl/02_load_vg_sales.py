"""Load NSW Valuer General bulk sales, filter to Greater Sydney residential
sales in the last 5 years, write stg_vg_sales to the project DuckDB.

Source CSV is ~297 MB inside data/raw/vg_sales/archive.zip with columns:
    Property ID, Sale counter, Download date / time, Property name,
    Property unit number, Property house number, Property street name,
    Property locality, Property post code, Area, Area type,
    Contract date, Settlement date, Purchase price, Zoning,
    Nature of property, Primary purpose, Strata lot number,
    Dealing number, Property legal description

Nature of property:  R = Residence, V = Vacant land, 3 = other (rare)
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "sydney_scorecard.duckdb"
VG_ZIP = RAW / "vg_sales" / "archive.zip"


def load_vg_sales() -> pd.DataFrame:
    cols = [
        "Property locality",
        "Property post code",
        "Contract date",
        "Purchase price",
        "Nature of property",
        "Primary purpose",
        "Area",
        "Area type",
    ]
    with zipfile.ZipFile(VG_ZIP) as z:
        csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(csv_name) as f:
            df = pd.read_csv(f, usecols=cols, low_memory=False)

    df = df.rename(
        columns={
            "Property locality": "locality",
            "Property post code": "postcode_raw",
            "Contract date": "contract_date",
            "Purchase price": "price",
            "Nature of property": "nature",
            "Primary purpose": "purpose",
            "Area": "area",
            "Area type": "area_type",
        }
    )
    df["contract_date"] = pd.to_datetime(df["contract_date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["postcode"] = (
        df["postcode_raw"].astype("string").str.replace(r"\.0$", "", regex=True)
    )
    df["suburb_name_norm"] = (
        df["locality"].fillna("").astype("string").str.strip().str.lower()
    )
    return df


def main() -> None:
    print(f"Reading VG sales CSV from {VG_ZIP.name} ...")
    df = load_vg_sales()
    print(f"  raw rows: {len(df):,}")

    df = df[df["nature"] == "R"]
    df = df[df["price"].notna() & (df["price"] > 1000)]
    df = df[df["contract_date"].notna()]
    print(f"  residential, priced, dated: {len(df):,}")
    print(
        f"  date range: {df['contract_date'].min().date()} "
        f"to {df['contract_date'].max().date()}"
    )

    print(f"\nWriting to DuckDB: {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))
    con.register("vg_df", df)
    con.execute(
        """
        CREATE OR REPLACE TABLE stg_vg_sales AS
        SELECT
            ds.suburb_id,
            ds.suburb_name,
            vg.locality          AS vg_locality,
            vg.postcode          AS postcode,
            vg.contract_date     AS contract_date,
            CAST(vg.price AS BIGINT) AS price,
            vg.purpose           AS purpose
        FROM vg_df vg
        INNER JOIN dim_suburb ds
            ON ds.suburb_name_norm = vg.suburb_name_norm
        WHERE vg.contract_date >= CURRENT_DATE - INTERVAL 5 YEAR
        """
    )
    con.unregister("vg_df")

    n_sales = con.execute("SELECT COUNT(*) FROM stg_vg_sales").fetchone()[0]
    n_suburbs = con.execute(
        "SELECT COUNT(DISTINCT suburb_id) FROM stg_vg_sales"
    ).fetchone()[0]
    print(f"  Greater Sydney residential sales (last 5yr): {n_sales:,}")
    print(f"  suburbs with at least one sale:            {n_suburbs:,}")

    print("\nTop-10 suburbs by sales count (last 12mo):")
    top10 = con.execute(
        """
        SELECT
            suburb_name,
            COUNT(*)                       AS n_sales,
            MEDIAN(price)::BIGINT          AS median_12m,
            MAX(contract_date)::DATE       AS latest_sale
        FROM stg_vg_sales
        WHERE contract_date >= CURRENT_DATE - INTERVAL 1 YEAR
        GROUP BY 1
        HAVING n_sales >= 5
        ORDER BY n_sales DESC
        LIMIT 10
        """
    ).df()
    print(top10.to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()
