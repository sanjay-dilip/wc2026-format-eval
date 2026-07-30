"""Source-to-warehouse row count reconciliation.

Compares each local source CSV's row count against its RAW.* table's row
count in Snowflake, and logs one VALIDATION.DATA_QUALITY_SUMMARY row per
file/table pair. A mismatch means the load silently dropped or duplicated
rows somewhere between disk and warehouse.
"""

import csv
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import GROUP_DRAW_SOURCE_PATH, MATCH_SOURCE_PATH, SHOOTOUT_SOURCE_PATH
from src.ingestion.connect import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# (local source file, RAW table it was loaded into)
SOURCE_TABLE_PAIRS = [
    (MATCH_SOURCE_PATH, "RAW.MATCH"),
    (SHOOTOUT_SOURCE_PATH, "RAW.SHOOTOUT"),
    (GROUP_DRAW_SOURCE_PATH, "RAW.GROUP_DRAW"),
]


def count_csv_rows(path: Path) -> int:
    """Return the number of data rows in a CSV file (header excluded)."""
    with path.open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def reconcile(cursor, source_path: Path, table_name: str) -> None:
    """Compare a source file's row count against its RAW table's row count."""
    source_count = count_csv_rows(source_path)

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    warehouse_count = cursor.fetchone()[0]

    mismatch = source_count != warehouse_count
    cursor.execute(
        "INSERT INTO VALIDATION.DATA_QUALITY_SUMMARY "
        "(check_name, table_name, rows_checked, rows_failed, passed, notes, checked_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            "source_to_warehouse_reconciliation",
            table_name,
            source_count,
            1 if mismatch else 0,
            not mismatch,
            f"source={source_path.name} source_rows={source_count} warehouse_rows={warehouse_count}",
            datetime.now(timezone.utc),
        ),
    )
    logger.info(
        "%s: source=%s warehouse=%s match=%s",
        table_name,
        source_count,
        warehouse_count,
        not mismatch,
    )


def main() -> None:
    """Reconcile every source file's row count against its RAW table."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for source_path, table_name in SOURCE_TABLE_PAIRS:
            reconcile(cursor, source_path, table_name)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
