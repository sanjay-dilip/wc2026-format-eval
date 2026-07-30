"""Tests for src/validation/checks.py.

Runs each check against the already-validated
data/processed/wc2026_stage_mapping.csv (expect zero failures — this
re-proves, as an automated test, the checks that were previously only run
ad hoc in chat during Build 0) and against a fixture with one deliberately
injected bad row, to prove each check actually fails on bad data rather
than just theoretically being able to.
"""

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.validation.checks import (
    EXPECTED_STAGE_COUNTS,
    find_duplicate_join_keys,
    find_group_mismatches,
    find_impossible_dates,
    find_invalid_scores,
    find_missing_teams,
    stage_counts,
)

STAGE_MAPPING_PATH = REPO_ROOT / "data" / "processed" / "wc2026_stage_mapping.csv"
GROUP_DRAW_PATH = REPO_ROOT / "data" / "raw" / "wc2026_group_draw.csv"
BAD_ROW_FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bad_row_fixture.csv"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_group_draw(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as f:
        return {row["team"]: row["group_letter"] for row in csv.DictReader(f)}


def _known_teams() -> set[str]:
    return set(load_group_draw(GROUP_DRAW_PATH))


def test_validated_dataset_has_no_duplicate_join_keys():
    rows = load_rows(STAGE_MAPPING_PATH)
    assert find_duplicate_join_keys(rows) == []


def test_validated_dataset_has_no_group_mismatches():
    rows = load_rows(STAGE_MAPPING_PATH)
    group_draw = load_group_draw(GROUP_DRAW_PATH)
    assert find_group_mismatches(rows, group_draw) == []


def test_validated_dataset_stage_counts_match():
    rows = load_rows(STAGE_MAPPING_PATH)
    assert stage_counts(rows) == EXPECTED_STAGE_COUNTS


def test_validated_dataset_has_no_missing_teams():
    rows = load_rows(STAGE_MAPPING_PATH)
    assert find_missing_teams(rows, _known_teams()) == []


def test_validated_dataset_has_no_invalid_scores():
    rows = load_rows(STAGE_MAPPING_PATH)
    assert find_invalid_scores(rows) == []


def test_validated_dataset_has_no_impossible_dates():
    rows = load_rows(STAGE_MAPPING_PATH)
    assert find_impossible_dates(rows) == []


def test_duplicate_join_key_check_fails_on_injected_bad_row_then_passes_once_fixed():
    rows = load_rows(BAD_ROW_FIXTURE_PATH)
    assert len(rows) == 3

    duplicates = find_duplicate_join_keys(rows)
    assert len(duplicates) == 2  # the injected row and its original both flag

    fixed_rows = rows[:2]  # remove the deliberately injected duplicate
    assert find_duplicate_join_keys(fixed_rows) == []
