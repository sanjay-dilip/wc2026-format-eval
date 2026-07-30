"""Reusable data-quality checks for the WC2026 match dataset.

Each check takes rows shaped like wc2026_stage_mapping.csv (csv.DictReader
output: string values) and returns the list of rows that fail, so callers
get both a failure count and the actual offending records rather than a
bare pass/fail boolean.
"""

from datetime import date

VALID_MATCH_DATE_START = date(2026, 6, 11)
VALID_MATCH_DATE_END = date(2026, 7, 19)
MAX_PLAUSIBLE_SCORE = 20

EXPECTED_STAGE_COUNTS = {
    "Group Stage": 72,
    "Round of 32": 16,
    "Round of 16": 8,
    "Quarterfinals": 4,
    "Semifinals": 2,
    "Third Place Playoff": 1,
    "Final": 1,
}


def find_duplicate_join_keys(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return every row whose (match_date, home_team, away_team) key repeats."""
    counts: dict[tuple[str, str, str], int] = {}
    for row in rows:
        key = (row["match_date"], row["home_team"], row["away_team"])
        counts[key] = counts.get(key, 0) + 1
    return [
        row
        for row in rows
        if counts[(row["match_date"], row["home_team"], row["away_team"])] > 1
    ]


def find_group_mismatches(
    rows: list[dict[str, str]], group_draw: dict[str, str]
) -> list[dict[str, str]]:
    """Return group-stage rows where home/away team's group disagrees with
    the row's own group_letter."""
    mismatches = []
    for row in rows:
        if row["is_knockout"] == "True":
            continue
        home_group = group_draw.get(row["home_team"])
        away_group = group_draw.get(row["away_team"])
        if not (home_group == away_group == row["group_letter"]):
            mismatches.append(row)
    return mismatches


def stage_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    """Return a count of rows per stage value."""
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["stage"]] = counts.get(row["stage"], 0) + 1
    return counts


def find_missing_teams(
    rows: list[dict[str, str]], known_teams: set[str]
) -> list[dict[str, str]]:
    """Return rows where home_team or away_team isn't in the known roster."""
    return [
        row
        for row in rows
        if row["home_team"] not in known_teams or row["away_team"] not in known_teams
    ]


def find_invalid_scores(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return rows with a negative or implausibly high score."""
    invalid = []
    for row in rows:
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        if not (0 <= home_score <= MAX_PLAUSIBLE_SCORE) or not (
            0 <= away_score <= MAX_PLAUSIBLE_SCORE
        ):
            invalid.append(row)
    return invalid


def find_impossible_dates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return rows whose match_date falls outside the validated 2026
    tournament window."""
    invalid = []
    for row in rows:
        match_date = date.fromisoformat(row["match_date"])
        if not (VALID_MATCH_DATE_START <= match_date <= VALID_MATCH_DATE_END):
            invalid.append(row)
    return invalid
