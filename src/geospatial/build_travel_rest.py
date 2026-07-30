"""Populate ANALYTICS.TEAM_TRAVEL_REST: one row per team per match, with
distance traveled and rest days since that team's previous match.

Truncates before populating, so re-running is safe (same pattern as
src/core/build_core.py). Depends on CORE.DIM_VENUE already having its
Build 7 coordinate backfill applied - run src/core/build_core.py first.
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

POPULATE_QUERY_PATH = REPO_ROOT / "sql" / "analytics" / "populate" / "01_team_travel_rest.sql"


def main() -> None:
    """Truncate and repopulate ANALYTICS.TEAM_TRAVEL_REST."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE ANALYTICS.TEAM_TRAVEL_REST")
        cursor.execute(POPULATE_QUERY_PATH.read_text(encoding="utf-8"))
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM ANALYTICS.TEAM_TRAVEL_REST")
        logger.info("Populated ANALYTICS.TEAM_TRAVEL_REST: %s rows", cursor.fetchone()[0])

        cursor.execute(
            "SELECT COUNT(*) FROM ANALYTICS.TEAM_TRAVEL_REST WHERE previous_match_id IS NULL"
        )
        logger.info("Rows with no previous match (team's first match): %s", cursor.fetchone()[0])

        cursor.execute(
            "SELECT COUNT(*) FROM ANALYTICS.TEAM_TRAVEL_REST "
            "WHERE previous_match_id IS NOT NULL AND (distance_km IS NULL OR rest_days IS NULL)"
        )
        unexpected_nulls = cursor.fetchone()[0]
        logger.info("Rows with a previous match but a NULL distance/rest (should be 0): %s", unexpected_nulls)
        if unexpected_nulls:
            raise RuntimeError(
                f"{unexpected_nulls} rows have a previous match but missing distance_km/rest_days"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
