"""Peek at headers + first rows of the big CSVs and find WFH-relevant Census tables."""
from pathlib import Path
import csv
import zipfile

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def peek_csv(path: Path, n: int = 3, max_cols: int = 30) -> None:
    print(f"\n=== {path.relative_to(RAW.parent.parent)} ({path.stat().st_size / 1e6:.1f} MB) ===")
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"  columns ({len(header)}): {header[:max_cols]}")
        if len(header) > max_cols:
            print(f"    ...+{len(header) - max_cols} more")
        for i, row in enumerate(reader):
            if i >= n:
                break
            print(f"  row {i+1}: {row[:max_cols]}")


def peek_csv_in_zip(zip_path: Path, csv_name: str, n: int = 3, max_cols: int = 20) -> None:
    print(f"\n=== {csv_name} (in {zip_path.name}) ===")
    with zipfile.ZipFile(zip_path) as z:
        with z.open(csv_name) as raw:
            text = (line.decode("utf-8", errors="replace") for line in raw)
            reader = csv.reader(text)
            header = next(reader)
            print(f"  columns ({len(header)}): {header[:max_cols]}")
            if len(header) > max_cols:
                print(f"    ...+{len(header) - max_cols} more")
            for i, row in enumerate(reader):
                if i >= n:
                    break
                print(f"  row {i+1}: {row[:max_cols]}")


def main() -> None:
    # VG sales (extract CSV from ZIP)
    vg_zip = RAW / "vg_sales" / "archive.zip"
    with zipfile.ZipFile(vg_zip) as z:
        vg_csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
        print(f"VG csv inside zip: {vg_csv_name}")
        peek_csv_in_zip(vg_zip, vg_csv_name, n=3, max_cols=30)

    # BOCSAR (extract CSV from ZIP)
    bocsar_zip = RAW / "bocsar" / "SuburbData.zip"
    with zipfile.ZipFile(bocsar_zip) as z:
        bocsar_csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
        print(f"\nBOCSAR csv inside zip: {bocsar_csv_name}")
        peek_csv_in_zip(bocsar_zip, bocsar_csv_name, n=3, max_cols=20)

    # Census: find tables relevant to WFH
    census_zip = RAW / "abs_census" / "2021_GCP_SAL_for_NSW_short-header.zip"
    print(f"\n=== Census ZIP {census_zip.name}: SAL-level tables ===")
    with zipfile.ZipFile(census_zip) as z:
        sal_csvs = sorted(n for n in z.namelist() if "_NSW_SAL.csv" in n)
        print(f"  total SAL-level CSVs: {len(sal_csvs)}")
        # Look for tables containing travel-to-work / WFH
        for name in sal_csvs:
            short = Path(name).name
            if any(g in short for g in ("G01", "G02", "G33", "G46", "G59", "G60", "G61")):
                print(f"\n  --- {short} ---")
                peek_csv_in_zip(census_zip, name, n=1, max_cols=12)


if __name__ == "__main__":
    main()
