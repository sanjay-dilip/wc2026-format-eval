"""Build 8: prove incremental load equals full rebuild.

Simulates a new-match arrival, a correction, and an idempotent no-op
rerun against RAW.MATCH -> RAW.MATCH_STREAM -> CORE.SP_APPLY_MATCH_STREAM()
(sql/core/10_create_apply_match_stream_procedure.sql), and after each
change compares the incrementally-updated CORE.FACT_MATCH against a full
rebuild (src.core.build_core.main()) via a content hash.

The hash is computed over natural-key/business columns (team names,
match date, tournament year, scores, ...), not raw match_id - a full
rebuild after inserting a new 2026 match renumbers the trailing historical
block (see docs/decision_log.md, Build 8 entry), so match_id is not a
valid basis for this comparison even though the actual match data is
identical.

Cleans up back to the original 220-row baseline afterward - same
fixture-and-cleanup discipline as tests/test_validation_checks.py's
bad-row fixture. Safe to re-run: raises before making any changes if it
finds a dirty starting state (pending stream data, or a leftover
synthetic row from a previous crashed run).
"""

import hashlib
import logging
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.build_core import main as full_rebuild
from src.ingestion.connect import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Synthetic fixture match: same real date/venue/stage as the actual 2026
# Final (the tournament's last date), with a home_team name that sorts
# alphabetically after every team that already plays on that date - see
# sql/core/10_create_apply_match_stream_procedure.sql's comment on why
# that ordering is what makes the incremental match_id assignment agree
# with a full rebuild's ROW_NUMBER() for this one row.
SYNTHETIC_MATCH_DATE = "2026-07-19"
SYNTHETIC_HOME_TEAM = "Switzerland"
SYNTHETIC_AWAY_TEAM = "Sweden"
SYNTHETIC_STAGE = "Third Place Playoff"
SYNTHETIC_VENUE_CITY = "East Rutherford"
SYNTHETIC_VENUE_COUNTRY = "United States"
SYNTHETIC_HOME_SCORE = 2
SYNTHETIC_AWAY_SCORE = 1

TASK_POLL_INTERVAL_SECONDS = 3
TASK_POLL_MAX_ATTEMPTS = 10

FACT_MATCH_NATURAL_VIEW_QUERY = """
    SELECT
        t.tournament_year, dd.full_date, ht.team_name, at.team_name,
        f.home_score, f.away_score, f.went_to_et, f.went_to_so,
        sowin.team_name, ds.stage_name, dv.venue_name, f.neutral_site
    FROM CORE.FACT_MATCH f
    JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = f.tournament_id
    JOIN CORE.DIM_DATE dd ON dd.date_id = f.date_id
    JOIN CORE.DIM_TEAM ht ON ht.team_id = f.home_team_id
    JOIN CORE.DIM_TEAM at ON at.team_id = f.away_team_id
    LEFT JOIN CORE.DIM_STAGE ds ON ds.stage_id = f.stage_id
    LEFT JOIN CORE.DIM_VENUE dv ON dv.venue_id = f.venue_id
    LEFT JOIN CORE.DIM_TEAM sowin ON sowin.team_id = f.so_winner_id
    ORDER BY t.tournament_year, dd.full_date, ht.team_name, at.team_name
"""


def fact_match_content_hash(cursor) -> str:
    """Hash CORE.FACT_MATCH by natural-key/business columns, not match_id."""
    cursor.execute(FACT_MATCH_NATURAL_VIEW_QUERY)
    rows = cursor.fetchall()
    return hashlib.sha256(repr(rows).encode("utf-8")).hexdigest()


def assert_clean_starting_state(cursor) -> None:
    """Refuse to run against a dirty state left by a previous crashed run."""
    cursor.execute("SELECT SYSTEM$STREAM_HAS_DATA('RAW.MATCH_STREAM')")
    if cursor.fetchone()[0]:
        raise RuntimeError(
            "RAW.MATCH_STREAM already has pending data - a previous run may have "
            "crashed mid-way. Inspect RAW.MATCH for a leftover synthetic row before "
            "re-running."
        )
    cursor.execute(
        "SELECT COUNT(*) FROM RAW.MATCH WHERE home_team = %s AND away_team = %s",
        (SYNTHETIC_HOME_TEAM, SYNTHETIC_AWAY_TEAM),
    )
    if cursor.fetchone()[0]:
        raise RuntimeError(
            f"A leftover synthetic fixture row ({SYNTHETIC_HOME_TEAM} vs "
            f"{SYNTHETIC_AWAY_TEAM}) already exists in RAW.MATCH - clean it up before "
            "re-running."
        )


def insert_synthetic_match(cursor) -> None:
    """Simulate a new match arriving in RAW.MATCH."""
    cursor.execute(
        """
        INSERT INTO RAW.MATCH (match_date, home_team, away_team, home_score, away_score,
                                stage, venue_city, venue_country, is_knockout)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """,
        (
            SYNTHETIC_MATCH_DATE,
            SYNTHETIC_HOME_TEAM,
            SYNTHETIC_AWAY_TEAM,
            SYNTHETIC_HOME_SCORE,
            SYNTHETIC_AWAY_SCORE,
            SYNTHETIC_STAGE,
            SYNTHETIC_VENUE_CITY,
            SYNTHETIC_VENUE_COUNTRY,
        ),
    )


def pick_correction_target(cursor) -> tuple[str, str, str, int, int]:
    """Pick a real, non-shootout 2026 match to simulate a score correction on."""
    cursor.execute(
        """
        SELECT m.match_date, m.home_team, m.away_team, m.home_score, m.away_score
        FROM RAW.MATCH m
        LEFT JOIN RAW.SHOOTOUT sh
            ON sh.match_date = m.match_date AND sh.home_team = m.home_team
           AND sh.away_team = m.away_team
        WHERE sh.match_date IS NULL
        ORDER BY m.match_date, m.home_team
        LIMIT 1
        """
    )
    match_date, home_team, away_team, home_score, away_score = cursor.fetchone()
    return str(match_date), home_team, away_team, home_score, away_score


def apply_correction(cursor, match_date: str, home_team: str, away_team: str, new_home_score: int) -> None:
    """Simulate a score correction on an existing RAW.MATCH row."""
    cursor.execute(
        "UPDATE RAW.MATCH SET home_score = %s WHERE match_date = %s AND home_team = %s AND away_team = %s",
        (new_home_score, match_date, home_team, away_team),
    )


def call_apply_stream_procedure(cursor) -> str:
    """Consume RAW.MATCH_STREAM into CORE.FACT_MATCH incrementally."""
    cursor.execute("CALL CORE.SP_APPLY_MATCH_STREAM()")
    return cursor.fetchone()[0]


def run_full_rebuild_and_rehash(cursor) -> str:
    """Run a from-scratch full CORE rebuild and return CORE.FACT_MATCH's content hash."""
    full_rebuild()
    return fact_match_content_hash(cursor)


def execute_task_and_wait(cursor) -> None:
    """Trigger CORE.INCREMENTAL_FACT_MATCH_TASK once and poll until it succeeds.

    Secondary confirmation that the Task object itself works end-to-end -
    the main comparison above calls the procedure directly for
    deterministic, synchronous timing; this proves the scheduled-task path
    (never actually scheduled - see sql/core/11_create_incremental_fact_match_task.sql)
    also runs correctly at least once.
    """
    cursor.execute("EXECUTE TASK CORE.INCREMENTAL_FACT_MATCH_TASK")
    for _ in range(TASK_POLL_MAX_ATTEMPTS):
        cursor.execute(
            "SELECT state FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY("
            "TASK_NAME => 'INCREMENTAL_FACT_MATCH_TASK')) ORDER BY scheduled_time DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row and row[0] == "SUCCEEDED":
            logger.info("CORE.INCREMENTAL_FACT_MATCH_TASK ran successfully via EXECUTE TASK.")
            return
        if row and row[0] == "FAILED":
            raise RuntimeError("CORE.INCREMENTAL_FACT_MATCH_TASK run failed - check TASK_HISTORY.")
        time.sleep(TASK_POLL_INTERVAL_SECONDS)
    logger.warning(
        "CORE.INCREMENTAL_FACT_MATCH_TASK did not report SUCCEEDED within %s attempts - "
        "not treated as a hard failure, since the main comparison above already verified "
        "correctness via a direct procedure call.",
        TASK_POLL_MAX_ATTEMPTS,
    )


def main() -> None:
    """Run all 3 scenarios, compare incremental vs. full rebuild, then clean up."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        assert_clean_starting_state(cursor)

        baseline_hash = fact_match_content_hash(cursor)
        logger.info("Baseline CORE.FACT_MATCH content hash: %s", baseline_hash)

        # Scenario A: new match arrival.
        insert_synthetic_match(cursor)
        conn.commit()
        result = call_apply_stream_procedure(cursor)
        conn.commit()
        logger.info("Scenario A (new match arrival) procedure result: %s", result)
        incremental_hash_a = fact_match_content_hash(cursor)
        full_hash_a = run_full_rebuild_and_rehash(cursor)
        if incremental_hash_a != full_hash_a:
            raise RuntimeError(
                f"Scenario A mismatch: incremental={incremental_hash_a} full={full_hash_a}"
            )
        logger.info("Scenario A: incremental result matches full rebuild.")

        # Scenario B: correction.
        match_date, home_team, away_team, original_home_score, _ = pick_correction_target(cursor)
        corrected_home_score = original_home_score + 1
        apply_correction(cursor, match_date, home_team, away_team, corrected_home_score)
        conn.commit()
        result = call_apply_stream_procedure(cursor)
        conn.commit()
        logger.info(
            "Scenario B (correction: %s vs %s, home_score %s -> %s) procedure result: %s",
            home_team, away_team, original_home_score, corrected_home_score, result,
        )
        incremental_hash_b = fact_match_content_hash(cursor)
        full_hash_b = run_full_rebuild_and_rehash(cursor)
        if incremental_hash_b != full_hash_b:
            raise RuntimeError(
                f"Scenario B mismatch: incremental={incremental_hash_b} full={full_hash_b}"
            )
        logger.info("Scenario B: incremental result matches full rebuild.")

        # Scenario C: idempotent rerun, no pending changes.
        result = call_apply_stream_procedure(cursor)
        conn.commit()
        logger.info("Scenario C (idempotent rerun) procedure result: %s", result)
        idempotent_hash = fact_match_content_hash(cursor)
        if idempotent_hash != full_hash_b:
            raise RuntimeError(
                f"Scenario C mismatch: expected no change, got {idempotent_hash} != {full_hash_b}"
            )
        logger.info("Scenario C: no-op rerun left CORE.FACT_MATCH unchanged.")

        # Task demonstration: prove the Task object itself works, on an
        # empty stream (best-effort, not part of the correctness proof).
        execute_task_and_wait(cursor)

        # Cleanup: restore RAW.MATCH to its original state, then rebuild.
        cursor.execute(
            "DELETE FROM RAW.MATCH WHERE home_team = %s AND away_team = %s",
            (SYNTHETIC_HOME_TEAM, SYNTHETIC_AWAY_TEAM),
        )
        apply_correction(cursor, match_date, home_team, away_team, original_home_score)
        conn.commit()
        call_apply_stream_procedure(cursor)
        conn.commit()
        final_hash = run_full_rebuild_and_rehash(cursor)
        if final_hash != baseline_hash:
            raise RuntimeError(
                f"Cleanup did not restore the original baseline: {final_hash} != {baseline_hash}"
            )
        logger.info("Cleanup verified: CORE.FACT_MATCH content hash matches the original baseline.")

        cursor.execute("SELECT COUNT(*) FROM CORE.FACT_MATCH")
        logger.info("Final CORE.FACT_MATCH row count (should be 220): %s", cursor.fetchone()[0])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
