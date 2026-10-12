"""
Download BTS On-Time Performance data (optional helper)
=======================================================

Usage (from the project folder):

    python src/download_data.py --year 2024 --months 1 2 3

This downloads the pre-packaged monthly ZIP files that BTS publishes, unzips
the CSV into data/raw/, and deletes the ZIP.

If it fails (no internet, BTS website changed, firewall...), do not worry:
follow the MANUAL steps in data/README.md instead. The analysis works with
any BTS CSV you place inside the data/ folder.
"""

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# BTS publishes one ZIP per month at this address pattern.
URL = ("https://transtats.bts.gov/PREZIP/"
       "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip")


def download_month(year: int, month: int) -> None:
    url = URL.format(year=year, month=month)
    zip_path = RAW_DIR / f"bts_{year}_{month:02d}.zip"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {year}-{month:02d} from {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (student project)"})
    with urllib.request.urlopen(request, timeout=120) as response, open(zip_path, "wb") as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".csv"):
                zf.extract(name, RAW_DIR)
                print(f"  extracted {name}")
    zip_path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download BTS On-Time Performance monthly files.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="+", required=True, help="e.g. 1 2 3")
    args = parser.parse_args()
    for month in args.months:
        try:
            download_month(args.year, month)
        except Exception as error:  # network problems, file not published yet, etc.
            print(f"\nCould not download {args.year}-{month:02d}: {error}")
            print("Use the manual download steps in data/README.md instead.")
            sys.exit(1)
    print("\nDone. Now run:  python src/data_analysis.py   (or open the notebook)")


if __name__ == "__main__":
    main()
