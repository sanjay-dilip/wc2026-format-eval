"""Fetch the full historical martj42/international_results dataset.

data/raw/international_results_full.csv is gitignored (3.6+ MiB, not
2026-specific, easily re-fetched - see .gitignore) but until this script
existed, nothing actually fetched it: a fresh clone had no way to
regenerate the file src/transform/build_stage_mapping.py and this
project's own historical-comparison transform both depend on. This script
closes that gap.

Safe to re-run: always overwrites the local file with the latest pull.
"""

import csv
import io
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import requests

from config import INTERNATIONAL_RESULTS_SOURCE_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
EXPECTED_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "tournament",
    "city",
    "country",
    "neutral",
]
# 49,520 data rows confirmed at Build 0 (docs/data_dictionary.md); the
# dataset only grows as new matches are played, so treat that as a floor,
# not an exact count.
MIN_EXPECTED_ROWS = 49_520


def fetch(url: str = SOURCE_URL, timeout_seconds: int = 30) -> str:
    """Download the CSV body as text, raising on a non-2xx response."""
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.text


def validate(csv_text: str) -> int:
    """Check the header matches what this project expects and the row
    count is at least the floor confirmed at Build 0. Returns the row
    count. Raises ValueError on any mismatch."""
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)
    if header != EXPECTED_COLUMNS:
        raise ValueError(f"Unexpected column layout: {header}")
    row_count = sum(1 for _ in reader)
    if row_count < MIN_EXPECTED_ROWS:
        raise ValueError(
            f"Row count {row_count} is below the Build 0 floor of {MIN_EXPECTED_ROWS} "
            "- source may have changed shape or truncated mid-download."
        )
    return row_count


def main() -> None:
    """Fetch, validate, and write the historical results CSV to data/raw/."""
    logger.info("Fetching %s", SOURCE_URL)
    csv_text = fetch()
    row_count = validate(csv_text)
    INTERNATIONAL_RESULTS_SOURCE_PATH.write_text(csv_text, encoding="utf-8")
    logger.info(
        "Wrote %s data rows to %s", row_count, INTERNATIONAL_RESULTS_SOURCE_PATH
    )


if __name__ == "__main__":
    main()
