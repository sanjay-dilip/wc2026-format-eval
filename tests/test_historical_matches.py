"""Tests for src/transform/build_historical_matches.py.

Verifies the transform script reproduces, from raw inputs, the already
committed data/processed/wc_historical_matches.csv rather than producing
merely plausible-looking output - same pattern as test_stage_mapping.py.
"""

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "transform"))

from build_historical_matches import (  # noqa: E402
    COMPARISON_YEARS,
    INTERNATIONAL_RESULTS_PATH,
    OUTPUT_PATH,
    build_historical_match_rows,
    load_historical_world_cup_matches,
)

# 64 matches for the 32-team format (2022), 52 for the 24-team format
# (1994) - the standard match counts for those formats, confirmed directly
# against the source data, not assumed from format alone.
EXPECTED_MATCH_COUNTS = {"2022": 64, "1994": 52}


def _generated_rows():
    matches = load_historical_world_cup_matches(INTERNATIONAL_RESULTS_PATH, COMPARISON_YEARS)
    return build_historical_match_rows(matches)


def test_match_counts_by_tournament_year():
    rows = _generated_rows()
    counts = {"2022": 0, "1994": 0}
    for row in rows:
        counts[row.tournament_year] += 1
    assert counts == EXPECTED_MATCH_COUNTS


def test_no_other_tournament_years_present():
    rows = _generated_rows()
    years = {row.tournament_year for row in rows}
    assert years == set(EXPECTED_MATCH_COUNTS)


def test_join_key_is_unique():
    rows = _generated_rows()
    keys = [(row.tournament_year, row.match_date, row.home_team, row.away_team) for row in rows]
    assert len(keys) == len(set(keys))


def test_generated_output_matches_committed_csv():
    generated_rows = _generated_rows()
    generated = [vars(row) for row in generated_rows]
    generated_sorted = sorted(
        generated, key=lambda r: (r["tournament_year"], r["match_date"], r["home_team"])
    )

    with OUTPUT_PATH.open(newline="", encoding="utf-8") as f:
        committed = list(csv.DictReader(f))

    assert generated_sorted == committed
