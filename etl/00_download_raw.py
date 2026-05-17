"""Download all raw source files for the Sydney suburb scorecard.

Idempotent: skips any file that already exists and is non-empty.
Run from the repo root: ``python etl/00_download_raw.py``
"""
from __future__ import annotations

from pathlib import Path
import sys
import time

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

MANIFEST = [
    {
        "name": "ABS SAL boundaries (shapefile, GDA2020)",
        "url": (
            "https://www.abs.gov.au/statistics/standards/"
            "australian-statistical-geography-standard-asgs-edition-3/"
            "jul2021-jun2026/access-and-downloads/digital-boundary-files/"
            "SAL_2021_AUST_GDA2020_SHP.zip"
        ),
        "path": "abs_boundaries/SAL_2021_AUST_GDA2020_SHP.zip",
    },
    {
        "name": "ABS SAL allocation file (SAL->SA2->GCCSA->LGA)",
        "url": (
            "https://www.abs.gov.au/statistics/standards/"
            "australian-statistical-geography-standard-asgs-edition-3/"
            "jul2021-jun2026/access-and-downloads/allocation-files/"
            "SAL_2021_AUST.xlsx"
        ),
        "path": "abs_allocation/SAL_2021_AUST.xlsx",
    },
    {
        "name": "ABS Census 2021 GCP DataPack (SAL, NSW)",
        "url": (
            "https://www.abs.gov.au/census/find-census-data/datapacks/"
            "download/2021_GCP_SAL_for_NSW_short-header.zip"
        ),
        "path": "abs_census/2021_GCP_SAL_for_NSW_short-header.zip",
    },
    {
        "name": "ABS Regional Population (SA2, 2024-25)",
        "url": (
            "https://www.abs.gov.au/statistics/people/population/"
            "regional-population/2024-25/32180DS0001_2024-25.xlsx"
        ),
        "path": "abs_regional_pop/32180DS0001_2024-25.xlsx",
    },
    {
        "name": "NSW Valuer General bulk sales (6yr archive)",
        "url": "https://nswpropertysalesdata.com/data/archive.zip",
        "path": "vg_sales/archive.zip",
    },
    {
        "name": "BOCSAR recorded crime by suburb",
        "url": "https://bocsarblob.blob.core.windows.net/bocsar-open-data/SuburbData.zip",
        "path": "bocsar/SuburbData.zip",
    },
]


def download(item: dict) -> None:
    target = RAW_DIR / item["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        size_mb = target.stat().st_size / 1e6
        print(f"[skip] {item['name']}  ({size_mb:.1f} MB cached)")
        return

    print(f"[get ] {item['name']}")
    started = time.time()
    headers = {"User-Agent": "sydney-suburb-scorecard/1.0 (+github.com/tczhao)"}
    with requests.get(item["url"], stream=True, timeout=120, headers=headers) as r:
        r.raise_for_status()
        with open(target, "wb") as f:
            for chunk in r.iter_content(chunk_size=256 * 1024):
                f.write(chunk)
    size_mb = target.stat().st_size / 1e6
    secs = time.time() - started
    print(f"       -> {target.relative_to(RAW_DIR.parent.parent)}  ({size_mb:.1f} MB in {secs:.1f}s)")


def main() -> int:
    print(f"Raw data dir: {RAW_DIR}\n")
    for item in MANIFEST:
        try:
            download(item)
        except requests.HTTPError as e:
            print(f"[FAIL] {item['name']}: {e}", file=sys.stderr)
            return 1
        except requests.RequestException as e:
            print(f"[FAIL] {item['name']}: network error: {e}", file=sys.stderr)
            return 1
    print("\nAll downloads complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
