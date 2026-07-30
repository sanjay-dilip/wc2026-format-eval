"""Load the 2026 match subset, the full shootout history, the group draw
crosswalk, the confederation crosswalk, and the venue coordinates into
RAW, and record one AUDIT.LOAD_LOG row per file loaded.

Each load truncates its target table first: COPY INTO ... FORCE = TRUE is
not idempotent on its own (it re-appends the same rows on every re-run,
since FORCE bypasses Snowflake's already-loaded-file dedup) - truncating
first makes re-running this script safe.

credits_used is left NULL at insert time: Snowflake's
ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY view has up to ~3 hours of latency,
so a real per-load credit figure isn't available synchronously. It gets
backfilled by a separate reconciliation query once that view catches up.
"""

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import (
    CONFEDERATION_SOURCE_PATH,
    GROUP_DRAW_SOURCE_PATH,
    MATCH_SOURCE_PATH,
    SHOOTOUT_SOURCE_PATH,
    VENUE_COORDINATES_SOURCE_PATH,
    load_snowflake_config,
)
from src.ingestion.connect import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STAGE_NAME = "RAW.WC2026_STAGE"
FILE_FORMAT_NAME = "RAW.CSV_STANDARD"


def load_file(cursor, source_path: Path, target_table: str, warehouse_name: str) -> None:
    """PUT a local CSV to the internal stage, COPY INTO target_table, and
    write one AUDIT.LOAD_LOG row for the run."""
    started_at = datetime.now(timezone.utc)
    start = time.perf_counter()

    stage_path = f"@{STAGE_NAME}/{source_path.name}"
    cursor.execute(f"TRUNCATE TABLE {target_table}")
    cursor.execute(f"PUT file://{source_path} @{STAGE_NAME} OVERWRITE = TRUE AUTO_COMPRESS = TRUE")
    cursor.execute(
        f"COPY INTO {target_table} FROM {stage_path} "
        f"FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT_NAME}') "
        f"FORCE = TRUE"
    )
    copy_results = cursor.fetchall()
    rows_loaded = sum(row[3] for row in copy_results)

    duration_seconds = round(time.perf_counter() - start, 3)
    ended_at = datetime.now(timezone.utc)

    cursor.execute(
        "INSERT INTO AUDIT.LOAD_LOG "
        "(target_table, source_file, rows_loaded, warehouse_name, "
        "load_started_at, load_ended_at, duration_seconds, credits_used) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)",
        (
            target_table,
            source_path.name,
            rows_loaded,
            warehouse_name,
            started_at,
            ended_at,
            duration_seconds,
        ),
    )
    logger.info("Loaded %s rows into %s from %s", rows_loaded, target_table, source_path.name)


def main() -> None:
    """Load both RAW source files and log each run to AUDIT.LOAD_LOG."""
    cfg = load_snowflake_config()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        load_file(cursor, MATCH_SOURCE_PATH, "RAW.MATCH", cfg.warehouse)
        load_file(cursor, SHOOTOUT_SOURCE_PATH, "RAW.SHOOTOUT", cfg.warehouse)
        load_file(cursor, GROUP_DRAW_SOURCE_PATH, "RAW.GROUP_DRAW", cfg.warehouse)
        load_file(cursor, CONFEDERATION_SOURCE_PATH, "RAW.TEAM_CONFEDERATION", cfg.warehouse)
        load_file(cursor, VENUE_COORDINATES_SOURCE_PATH, "RAW.VENUE_COORDINATES", cfg.warehouse)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
