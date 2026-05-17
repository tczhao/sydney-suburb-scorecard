"""Build dim_suburb in DuckDB from the ABS SAL boundary shapefile.

Reads the SHP via pyshp (no GDAL needed), computes a bounding-box centroid for
each Statistical Area Localities (SAL = suburb) record, filters to NSW and the
Greater Sydney bounding box, then writes dim_suburb to the project DuckDB file.

dim_suburb columns:
    suburb_id          TEXT  -- SAL code, e.g. '10002' (PK)
    suburb_name        TEXT  -- SAL name as published, e.g. 'Abbotsford (NSW)'
    suburb_name_norm   TEXT  -- normalised key for joins to BOCSAR / VG
    centroid_lat       DOUBLE
    centroid_lon       DOUBLE
    area_sqkm          DOUBLE
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import pandas as pd
import shapefile  # pyshp

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "sydney_scorecard.duckdb"

SAL_ZIP = RAW / "abs_boundaries" / "SAL_2021_AUST_GDA2020_SHP.zip"

# Greater Sydney bounding box.
# Greater Sydney GCCSA (1GSYD) spans from the Hawkesbury in the north to the
# Royal NP in the south, west into the Blue Mountains foothills, east to the
# coast. The box below is intentionally a small superset of the GCCSA so we
# don't lose suburbs at the edges. Tradeoff: a few non-GCCSA suburbs at the
# Hawkesbury / Blue Mountains rim may sneak in.
LAT_MIN, LAT_MAX = -34.20, -33.40
LON_MIN, LON_MAX = 150.50, 151.45


def normalise_name(s: str) -> str:
    return s.strip().lower().replace(" (nsw)", "").replace("  ", " ")


def load_sal_records() -> pd.DataFrame:
    with zipfile.ZipFile(SAL_ZIP) as z:
        shp_name = next(n for n in z.namelist() if n.lower().endswith(".shp"))
        base = shp_name[:-4]
        with (
            z.open(f"{base}.shp") as shp,
            z.open(f"{base}.dbf") as dbf,
            z.open(f"{base}.shx") as shx,
        ):
            r = shapefile.Reader(shp=shp, dbf=dbf, shx=shx)
            field_names = [f[0] for f in r.fields if f[0] != "DeletionFlag"]
            rows = []
            skipped = 0
            for rec in r.iterShapeRecords():
                bbox = getattr(rec.shape, "bbox", None)
                if bbox is None:
                    skipped += 1
                    continue
                lon_min, lat_min, lon_max, lat_max = bbox
                attrs = dict(zip(field_names, list(rec.record)))
                attrs["centroid_lon"] = (lon_min + lon_max) / 2
                attrs["centroid_lat"] = (lat_min + lat_max) / 2
                rows.append(attrs)
            if skipped:
                print(f"  skipped {skipped} records with null geometry (admin / migratory)")
    return pd.DataFrame(rows)


def build_dim_suburb(df_all: pd.DataFrame) -> pd.DataFrame:
    nsw = df_all[df_all["STE_CODE21"] == "1"]
    in_box = nsw[
        nsw["centroid_lat"].between(LAT_MIN, LAT_MAX)
        & nsw["centroid_lon"].between(LON_MIN, LON_MAX)
    ].copy()
    in_box["suburb_id"] = in_box["SAL_CODE21"].astype(str)
    in_box["suburb_name"] = in_box["SAL_NAME21"]
    in_box["suburb_name_norm"] = in_box["suburb_name"].map(normalise_name)
    return (
        in_box[
            [
                "suburb_id",
                "suburb_name",
                "suburb_name_norm",
                "centroid_lat",
                "centroid_lon",
                "AREASQKM21",
            ]
        ]
        .rename(columns={"AREASQKM21": "area_sqkm"})
        .sort_values("suburb_name")
        .reset_index(drop=True)
    )


def main() -> None:
    print(f"Reading SHP from {SAL_ZIP.name}")
    df = load_sal_records()
    print(f"  total SAL records (Australia): {len(df):,}")
    print(f"  NSW records: {(df['STE_CODE21'] == '1').sum():,}")

    dim_suburb = build_dim_suburb(df)
    print(f"  Greater Sydney suburbs after bbox filter: {len(dim_suburb):,}")

    print(f"\nWriting to DuckDB: {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))
    con.register("dim_suburb_df", dim_suburb)
    con.execute("CREATE OR REPLACE TABLE dim_suburb AS SELECT * FROM dim_suburb_df")
    con.unregister("dim_suburb_df")

    print("\nSample rows:")
    print(con.execute("SELECT * FROM dim_suburb LIMIT 5").df().to_string(index=False))
    total = con.execute("SELECT COUNT(*) FROM dim_suburb").fetchone()[0]
    print(f"\nRow count in DuckDB: {total:,}")
    spot_sql = (
        "SELECT suburb_id, suburb_name, ROUND(centroid_lat,4) AS lat, "
        "ROUND(centroid_lon,4) AS lon, ROUND(area_sqkm,2) AS km2 "
        "FROM dim_suburb WHERE suburb_name_norm LIKE '%bondi%'"
    )
    print("Spot check (suburbs containing 'bondi'):")
    print(con.execute(spot_sql).df().to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
