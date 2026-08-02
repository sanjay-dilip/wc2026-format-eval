"""Build 9 success criteria, verified against both live accounts, not
assumed: the consumer account runs BI-shaped queries against the share,
and a direct attempt to query RAW from the consumer account fails.

CREATE DATABASE ... FROM SHARE creates a new database object in the
consumer account, bound to WC2026_SHARE - deliberately named differently
from the pre-existing, empty WC2026_CONSUMER database already sitting in
the secondary account (confirmed empty - only INFORMATION_SCHEMA/PUBLIC -
then left untouched rather than dropped or repurposed; see
docs/decision_log.md, Build 9 entry, for why).
"""

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import snowflake.connector

from src.ingestion.connect import get_connection, get_secondary_connection
from src.sharing.setup_share import get_account_identifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SHARE_NAME = "WC2026_SHARE"
SHARED_DATABASE_NAME = "WC2026_FROM_SHARE"


def create_shared_database(cursor, provider_identifier: str) -> None:
    """Accept the share by creating a database from it on the consumer side."""
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS {SHARED_DATABASE_NAME} FROM SHARE {provider_identifier}.{SHARE_NAME}"
    )


def run_bi_shaped_query(cursor) -> list:
    """Run a real analytical query against the shared surface, not just SELECT 1."""
    cursor.execute(
        f"""
        SELECT tournament_year, avg_abs_goal_diff, blowout_rate_pct
        FROM {SHARED_DATABASE_NAME}.SHARED.COMPETITIVE_BALANCE
        ORDER BY tournament_year
        """
    )
    return cursor.fetchall()


def confirm_shared_schema_is_the_only_one_visible(cursor) -> list:
    """List every schema visible in the shared database - should be exactly SHARED (+ INFORMATION_SCHEMA)."""
    cursor.execute(f"SHOW SCHEMAS IN DATABASE {SHARED_DATABASE_NAME}")
    return [row[1] for row in cursor.fetchall()]


def confirm_raw_is_inaccessible(cursor) -> bool:
    """Actually attempt to query RAW from the consumer account - don't assume it's hidden."""
    try:
        cursor.execute(f"SELECT * FROM {SHARED_DATABASE_NAME}.RAW.MATCH")
        cursor.fetchall()
        return False
    except snowflake.connector.errors.ProgrammingError as error:
        logger.info("Direct RAW access correctly failed: %s", error)
        return True


def main() -> None:
    """Accept the share, run a BI-shaped query, and verify RAW is inaccessible."""
    primary_conn = get_connection()
    try:
        provider_identifier = get_account_identifier(primary_conn)
    finally:
        primary_conn.close()
    logger.info("Provider account identifier: %s", provider_identifier)

    conn = get_secondary_connection()
    try:
        cursor = conn.cursor()

        create_shared_database(cursor, provider_identifier)
        conn.commit()
        logger.info("%s created from %s.%s", SHARED_DATABASE_NAME, provider_identifier, SHARE_NAME)

        rows = run_bi_shaped_query(cursor)
        logger.info("BI-shaped query against the share (competitive balance): %s", rows)
        if not rows:
            raise RuntimeError("BI-shaped query against the share returned no rows.")

        visible_schemas = confirm_shared_schema_is_the_only_one_visible(cursor)
        logger.info("Schemas visible in %s: %s", SHARED_DATABASE_NAME, visible_schemas)
        unexpected_schemas = set(visible_schemas) - {"SHARED", "INFORMATION_SCHEMA"}
        if unexpected_schemas:
            raise RuntimeError(f"Unexpected schemas visible via the share: {unexpected_schemas}")

        if not confirm_raw_is_inaccessible(cursor):
            raise RuntimeError("RAW was accessible from the consumer account - this must fail.")
        logger.info("Confirmed: RAW is genuinely inaccessible from the consumer account.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
