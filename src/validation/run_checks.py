"""Run every Build 3 data-quality check against the live warehouse.

Most checks are row-level: a SQL SELECT under sql/validation/checks/ that
returns the failing rows (match_date, home_team, away_team, detail). This
script runs each one, inserts the failing rows into
VALIDATION.REJECTED_RECORDS, and logs one VALIDATION.DATA_QUALITY_SUMMARY
row per check.

Two checks don't fit that row-level shape and are handled separately:
- stage_counts: an aggregate comparison against the validated 72/16/8/4/2/1/1
  split, not a per-row failure.
- missing_venue_coordinates: no coordinate column exists anywhere in RAW yet
  (open blocker #3 - no verified source found). This checks that no such
  column has been added without going through Build 7's re-verification
  gate, rather than checking data that doesn't exist.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingestion.connect import get_connection
from src.validation.checks import EXPECTED_STAGE_COUNTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHECKS_DIR = REPO_ROOT / "sql" / "validation" / "checks"

# (sql file, check name, source table to count rows_checked against)
ROW_LEVEL_CHECKS = [
    ("duplicate_join_keys_match.sql", "duplicate_join_keys", "RAW.MATCH"),
    ("duplicate_join_keys_shootout.sql", "duplicate_join_keys", "RAW.SHOOTOUT"),
    ("group_mismatches.sql", "group_mismatches", "RAW.MATCH"),
    ("missing_teams.sql", "missing_teams", "RAW.MATCH"),
    ("invalid_scores.sql", "invalid_scores", "RAW.MATCH"),
    ("impossible_dates.sql", "impossible_dates", "RAW.MATCH"),
]

VENUE_COORDINATE_COLUMNS = ("LATITUDE", "LONGITUDE", "VENUE_LATITUDE", "VENUE_LONGITUDE")


def log_summary(cursor, check_name: str, table_name: str, rows_checked: int, rows_failed: int, notes: str) -> None:
    """Insert one VALIDATION.DATA_QUALITY_SUMMARY row for a completed check."""
    cursor.execute(
        "INSERT INTO VALIDATION.DATA_QUALITY_SUMMARY "
        "(check_name, table_name, rows_checked, rows_failed, passed, notes, checked_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            check_name,
            table_name,
            rows_checked,
            rows_failed,
            rows_failed == 0,
            notes,
            datetime.now(timezone.utc),
        ),
    )
    logger.info(
        "%s on %s: %s/%s failed", check_name, table_name, rows_failed, rows_checked
    )


def run_row_level_check(cursor, sql_file: str, check_name: str, table_name: str) -> None:
    """Run one row-level detection query and log its failures."""
    query = (CHECKS_DIR / sql_file).read_text(encoding="utf-8")
    cursor.execute(query)
    failing_rows = cursor.fetchall()

    for match_date, home_team, away_team, detail in failing_rows:
        cursor.execute(
            "INSERT INTO VALIDATION.REJECTED_RECORDS "
            "(check_name, table_name, match_date, home_team, away_team, detail, rejected_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (check_name, table_name, str(match_date), home_team, away_team, detail, datetime.now(timezone.utc)),
        )

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    rows_checked = cursor.fetchone()[0]
    log_summary(cursor, check_name, table_name, rows_checked, len(failing_rows), notes=None)


def run_stage_counts_check(cursor) -> None:
    """Compare RAW.MATCH's stage split against the validated 72/16/8/4/2/1/1 split."""
    cursor.execute("SELECT stage, COUNT(*) FROM RAW.MATCH GROUP BY stage")
    actual_counts = dict(cursor.fetchall())

    mismatches = {
        stage: (expected, actual_counts.get(stage, 0))
        for stage, expected in EXPECTED_STAGE_COUNTS.items()
        if actual_counts.get(stage, 0) != expected
    }
    for stage, (expected, actual) in mismatches.items():
        cursor.execute(
            "INSERT INTO VALIDATION.REJECTED_RECORDS "
            "(check_name, table_name, match_date, home_team, away_team, detail, rejected_at) "
            "VALUES (%s, %s, NULL, NULL, NULL, %s, %s)",
            (
                "stage_counts",
                "RAW.MATCH",
                f"stage={stage} expected={expected} actual={actual}",
                datetime.now(timezone.utc),
            ),
        )

    rows_checked = sum(actual_counts.values())
    log_summary(cursor, "stage_counts", "RAW.MATCH", rows_checked, len(mismatches), notes=None)


def run_missing_venue_coordinates_check(cursor) -> None:
    """Confirm no venue coordinate column has been added to RAW.MATCH without
    going through Build 7's independent re-verification (open blocker #3)."""
    placeholders = ", ".join(f"'{c}'" for c in VENUE_COORDINATE_COLUMNS)
    cursor.execute(
        "SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE table_schema = 'RAW' AND table_name = 'MATCH' AND column_name IN ({placeholders})"
    )
    found_columns = [row[0] for row in cursor.fetchall()]
    log_summary(
        cursor,
        "missing_venue_coordinates",
        "RAW.MATCH",
        rows_checked=1,
        rows_failed=len(found_columns),
        notes=(
            "Documents open blocker #3: no venue coordinate source has been found, "
            "so none should exist in RAW yet. Fails only if an unverified column "
            f"appears: {found_columns}" if found_columns else
            "Documents open blocker #3: confirmed no venue coordinate column exists "
            "in RAW.MATCH yet, consistent with the still-open sourcing gap."
        ),
    )


def main() -> None:
    """Run every Build 3 check against the live warehouse."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for sql_file, check_name, table_name in ROW_LEVEL_CHECKS:
            run_row_level_check(cursor, sql_file, check_name, table_name)
        run_stage_counts_check(cursor)
        run_missing_venue_coordinates_check(cursor)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
