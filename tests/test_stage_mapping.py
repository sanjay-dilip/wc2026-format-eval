"""Tests for src/transform/build_stage_mapping.py.

Verifies the transform script reproduces, from raw inputs, the already
validated data/processed/wc2026_stage_mapping.csv rather than producing
merely plausible-looking output.
"""

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "transform"))

from build_stage_mapping import (  # noqa: E402
    GROUP_DRAW_PATH,
    INTERNATIONAL_RESULTS_PATH,
    OUTPUT_PATH,
    build_stage_mapping_rows,
    load_group_draw,
    load_world_cup_2026_matches,
)

EXPECTED_STAGE_COUNTS = {
    "Group Stage": 72,
    "Round of 32": 16,
    "Round of 16": 8,
    "Quarterfinals": 4,
    "Semifinals": 2,
    "Third Place Playoff": 1,
    "Final": 1,
}
EXPECTED_TOTAL_MATCHES = 104
EXPECTED_KNOCKOUT_MATCHES = 32


def _generated_rows():
    group_draw = load_group_draw(GROUP_DRAW_PATH)
    matches = load_world_cup_2026_matches(INTERNATIONAL_RESULTS_PATH)
    return build_stage_mapping_rows(matches, group_draw)


def test_filtered_match_count_is_104():
    matches = load_world_cup_2026_matches(INTERNATIONAL_RESULTS_PATH)
    assert len(matches) == EXPECTED_TOTAL_MATCHES


def test_stage_counts_match_validated_split():
    rows = _generated_rows()
    counts = {stage: 0 for stage in EXPECTED_STAGE_COUNTS}
    for row in rows:
        counts[row.stage] += 1
    assert counts == EXPECTED_STAGE_COUNTS


def test_group_letter_populated_only_for_group_stage_rows():
    rows = _generated_rows()
    knockout_rows = [row for row in rows if row.is_knockout == "True"]
    group_stage_rows = [row for row in rows if row.is_knockout == "False"]

    assert len(knockout_rows) == EXPECTED_KNOCKOUT_MATCHES
    assert all(row.group_letter == "" for row in knockout_rows)
    assert all(row.group_letter != "" for row in group_stage_rows)


def test_group_stage_matches_have_zero_group_mismatches():
    group_draw = load_group_draw(GROUP_DRAW_PATH)
    rows = _generated_rows()
    group_stage_rows = [row for row in rows if row.is_knockout == "False"]

    for row in group_stage_rows:
        assert group_draw[row.home_team] == group_draw[row.away_team] == row.group_letter


def test_generated_output_matches_committed_csv():
    generated_rows = _generated_rows()
    generated = [vars(row) for row in generated_rows]

    with OUTPUT_PATH.open(newline="", encoding="utf-8") as f:
        committed = list(csv.DictReader(f))

    assert generated == committed
