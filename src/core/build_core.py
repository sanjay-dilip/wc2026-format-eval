"""Populate CORE from validated RAW data: 6 dimensions, then fact_match.

Each table is truncated before its populate/*.sql query runs, so re-running
this script is safe (same truncate-first pattern as src/ingestion/load_raw.py
- see docs/decision_log.md's idempotency note from Build 3).

No zero-copy clone of CORE before this load: docs/decision_log.md
(2026-07-30 entry) documents why - CORE is empty going into Build 4, so
there is no prior state worth protecting, and Time Travel already covers
this session's risk.

After the dimension/fact populate loop, backfills dim_venue.venue_name
and lat/long from RAW.VENUE_COORDINATES (Build 7 research) - an UPDATE,
not a truncate+insert, but idempotent on its own terms since it always
sets the same values from the same source rows.
"""

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingestion.connect import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

POPULATE_DIR = REPO_ROOT / "sql" / "core" / "populate"

# (populate SQL file, table it fills) - dependency order matters: dims
# before fact_match, and dim_team depends on dim_group + dim_confederation
# already being populated.
POPULATE_ORDER = [
    ("01_dim_date.sql", "CORE.DIM_DATE"),
    ("02_dim_group.sql", "CORE.DIM_GROUP"),
    ("03_dim_confederation.sql", "CORE.DIM_CONFEDERATION"),
    ("04_dim_stage.sql", "CORE.DIM_STAGE"),
    ("05_dim_venue.sql", "CORE.DIM_VENUE"),
    ("06_dim_team.sql", "CORE.DIM_TEAM"),
    ("07_fact_match.sql", "CORE.FACT_MATCH"),
]

# fact_match FK column -> the dimension table it must resolve against.
# so_winner_id is excluded: it's legitimately NULL for non-shootout matches.
FACT_MATCH_FK_CHECKS = [
    ("date_id", "CORE.DIM_DATE", "date_id"),
    ("stage_id", "CORE.DIM_STAGE", "stage_id"),
    ("venue_id", "CORE.DIM_VENUE", "venue_id"),
    ("home_team_id", "CORE.DIM_TEAM", "team_id"),
    ("away_team_id", "CORE.DIM_TEAM", "team_id"),
]


def populate_table(cursor, sql_file: str, table_name: str) -> None:
    """Truncate a CORE table and repopulate it from its populate query."""
    cursor.execute(f"TRUNCATE TABLE {table_name}")
    query = (POPULATE_DIR / sql_file).read_text(encoding="utf-8")
    cursor.execute(query)
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    logger.info("Populated %s: %s rows", table_name, row_count)


def backfill_dim_venue_coordinates(cursor) -> None:
    """Run the RAW.VENUE_COORDINATES -> CORE.DIM_VENUE UPDATE."""
    query = (POPULATE_DIR / "08_backfill_dim_venue_coordinates.sql").read_text(encoding="utf-8")
    cursor.execute(query)
    cursor.execute("SELECT COUNT(*) FROM CORE.DIM_VENUE WHERE latitude IS NULL")
    missing = cursor.fetchone()[0]
    logger.info("dim_venue coordinate backfill: %s rows still missing lat/long", missing)


def check_orphaned_foreign_keys(cursor) -> dict[str, int]:
    """Return the count of CORE.FACT_MATCH rows whose FK doesn't resolve
    against its dimension table, for every FK except the nullable
    so_winner_id."""
    orphan_counts = {}
    for fk_column, dim_table, dim_key in FACT_MATCH_FK_CHECKS:
        cursor.execute(
            f"SELECT COUNT(*) FROM CORE.FACT_MATCH f "
            f"LEFT JOIN {dim_table} d ON d.{dim_key} = f.{fk_column} "
            f"WHERE d.{dim_key} IS NULL"
        )
        orphan_counts[fk_column] = cursor.fetchone()[0]
    return orphan_counts


def main() -> None:
    """Populate every CORE table and verify fact_match has no orphaned FKs."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for sql_file, table_name in POPULATE_ORDER:
            populate_table(cursor, sql_file, table_name)
        backfill_dim_venue_coordinates(cursor)
        conn.commit()

        orphan_counts = check_orphaned_foreign_keys(cursor)
        for fk_column, count in orphan_counts.items():
            logger.info("Orphaned %s: %s", fk_column, count)
        if any(orphan_counts.values()):
            raise RuntimeError(f"Orphaned foreign keys found: {orphan_counts}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
