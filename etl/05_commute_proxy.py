"""Compute a haversine straight-line commute proxy from each suburb centroid
to Sydney Town Hall, then write stg_commute to DuckDB.

commute_minutes_cbd = haversine_km(centroid, Town Hall) * MINUTES_PER_KM

MINUTES_PER_KM = 1.5 is a deliberately blunt heuristic that approximates the
combination of walk-to-station + scheduled train time + last-mile walk for a
typical Tuesday-morning peak-hour trip. It will over-rate suburbs separated
from the CBD by water with no rail crossing, and under-rate suburbs with a
long indirect rail route. Acceptable for ranking, not for prediction.
"""
from __future__ import annotations

import math
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "sydney_scorecard.duckdb"

TOWN_HALL_LAT = -33.8731
TOWN_HALL_LON = 151.2069
MINUTES_PER_KM = 1.5
EARTH_R_KM = 6371.0088


def main() -> None:
    print(f"Computing commute proxy to ({TOWN_HALL_LAT}, {TOWN_HALL_LON})")
    con = duckdb.connect(str(DB_PATH))

    # Use DuckDB's math functions; great-circle distance via haversine.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE stg_commute AS
        WITH base AS (
            SELECT
                suburb_id,
                suburb_name,
                centroid_lat,
                centroid_lon,
                radians(centroid_lat)              AS phi1,
                radians({TOWN_HALL_LAT})           AS phi2,
                radians(centroid_lat - ({TOWN_HALL_LAT})) AS dphi,
                radians(centroid_lon - ({TOWN_HALL_LON})) AS dlam
            FROM dim_suburb
        )
        SELECT
            suburb_id,
            suburb_name,
            centroid_lat,
            centroid_lon,
            {EARTH_R_KM} * 2 * asin(
                sqrt(
                    pow(sin(dphi / 2), 2)
                    + cos(phi1) * cos(phi2) * pow(sin(dlam / 2), 2)
                )
            ) AS distance_km,
            {EARTH_R_KM} * 2 * asin(
                sqrt(
                    pow(sin(dphi / 2), 2)
                    + cos(phi1) * cos(phi2) * pow(sin(dlam / 2), 2)
                )
            ) * {MINUTES_PER_KM} AS commute_minutes_cbd
        FROM base
        """
    )

    n = con.execute("SELECT COUNT(*) FROM stg_commute").fetchone()[0]
    print(f"  stg_commute rows: {n}")

    stats = con.execute(
        """
        SELECT
            ROUND(MIN(commute_minutes_cbd), 1)    AS min_min,
            ROUND(MEDIAN(commute_minutes_cbd), 1) AS median_min,
            ROUND(MAX(commute_minutes_cbd), 1)    AS max_min
        FROM stg_commute
        """
    ).df()
    print("\nCommute distribution (minutes):")
    print(stats.to_string(index=False))

    print("\nClosest 5 suburbs to CBD:")
    print(
        con.execute(
            """
            SELECT
                suburb_name,
                ROUND(distance_km, 2) AS km,
                ROUND(commute_minutes_cbd, 1) AS minutes
            FROM stg_commute
            ORDER BY distance_km ASC
            LIMIT 5
            """
        )
        .df()
        .to_string(index=False)
    )

    print("\nFarthest 5 suburbs from CBD:")
    print(
        con.execute(
            """
            SELECT
                suburb_name,
                ROUND(distance_km, 2) AS km,
                ROUND(commute_minutes_cbd, 1) AS minutes
            FROM stg_commute
            ORDER BY distance_km DESC
            LIMIT 5
            """
        )
        .df()
        .to_string(index=False)
    )

    # Sanity: Bondi should be ~7-8 km, Penrith ~50 km
    print("\nSpot check (Bondi, Penrith, Parramatta):")
    print(
        con.execute(
            """
            SELECT
                suburb_name,
                ROUND(distance_km, 2) AS km,
                ROUND(commute_minutes_cbd, 1) AS minutes
            FROM stg_commute
            WHERE suburb_name IN ('Bondi', 'Bondi Beach', 'Penrith', 'Parramatta')
            ORDER BY distance_km
            """
        )
        .df()
        .to_string(index=False)
    )

    con.close()


if __name__ == "__main__":
    main()
