"""Create schemas, the RAW/AUDIT objects, warehouse config, file format, and
stage by running the SQL DDL files under sql/ in dependency order.

Every statement uses CREATE ... IF NOT EXISTS or ALTER ... SET, so this is
safe to re-run.
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

SQL_ROOT = REPO_ROOT / "sql"

# Schema-creation files must run before any file that creates objects
# inside that schema (e.g. AUDIT before AUDIT.LOAD_LOG). "shared" runs
# after "analytics" - its secure views (sql/shared/01_create_secure_views.sql)
# wrap ANALYTICS objects, which must already exist.
SCHEMA_DIR_ORDER = ["raw", "validation", "core", "analytics", "shared", "audit"]


def iter_sql_files() -> list[Path]:
    """Return every .sql file under sql/, in dependency-safe order."""
    files = []
    for schema_dir in SCHEMA_DIR_ORDER:
        files.extend(sorted((SQL_ROOT / schema_dir).glob("*.sql")))
    return files


def run_sql_file(conn, path: Path) -> None:
    """Execute every statement in a single .sql file.

    Uses execute_string(), not a naive split on ";" - Build 8's stored
    procedure file (sql/core/10_create_apply_match_stream_procedure.sql)
    is one CREATE PROCEDURE statement whose $$-quoted body itself contains
    semicolons; execute_string() parses statement boundaries the same way
    Snowflake does, respecting dollar-quoting, instead of breaking on
    every ";" regardless of context.
    """
    conn.execute_string(path.read_text(encoding="utf-8"))


def main() -> None:
    """Run every DDL file under sql/ against the configured account."""
    conn = get_connection()
    try:
        for path in iter_sql_files():
            logger.info("Running %s", path.relative_to(REPO_ROOT))
            run_sql_file(conn, path)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
