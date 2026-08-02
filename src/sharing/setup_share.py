"""Build 9: add the secondary trial account as a consumer of WC2026_SHARE.

sql/shared/*.sql (schema, secure views, share creation + grants) already
ran as part of src.ingestion.setup_snowflake - this script does the one
step that can't be a static committed SQL file: ALTER SHARE ... ADD
ACCOUNTS needs the consumer account's org-qualified identifier
(org_name.account_name), which is deployment-specific and looked up live
here rather than hardcoded or duplicated into .env, the same reasoning
config.py already established for credentials.
"""

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingestion.connect import get_connection, get_secondary_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SHARE_NAME = "WC2026_SHARE"


def get_account_identifier(conn) -> str:
    """Return an account's org-qualified identifier (org_name.account_name)."""
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME()")
    org_name, account_name = cursor.fetchone()
    return f"{org_name}.{account_name}"


def main() -> None:
    """Add the secondary account as a consumer of the primary account's share."""
    secondary_conn = get_secondary_connection()
    try:
        consumer_identifier = get_account_identifier(secondary_conn)
    finally:
        secondary_conn.close()
    logger.info("Consumer account identifier: %s", consumer_identifier)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"ALTER SHARE {SHARE_NAME} SET ACCOUNTS = {consumer_identifier}")
        conn.commit()
        logger.info("%s now shared with %s", SHARE_NAME, consumer_identifier)

        cursor.execute(f"SHOW GRANTS TO SHARE {SHARE_NAME}")
        for row in cursor.fetchall():
            logger.info("Grant on share: %s", row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
