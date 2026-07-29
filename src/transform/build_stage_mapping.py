"""Build the 2026 World Cup match/stage/group mapping table.

Filters the full historical results dataset down to the 104 2026 FIFA World
Cup matches, then enriches each match with tournament stage and (for group-
stage matches only) group letter, reproducing
data/processed/wc2026_stage_mapping.csv from raw inputs instead of leaving
that derivation as an unreproducible one-off.
"""

import csv
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERNATIONAL_RESULTS_PATH = REPO_ROOT / "data" / "raw" / "international_results_full.csv"
GROUP_DRAW_PATH = REPO_ROOT / "data" / "raw" / "wc2026_group_draw.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "wc2026_stage_mapping.csv"

WORLD_CUP_TOURNAMENT_NAME = "FIFA World Cup"
WORLD_CUP_2026_START = date(2026, 1, 1)

# Non-overlapping match-date windows, derived from the validated 2026
# schedule. Each tuple is an inclusive (start, end) date range.
STAGE_DATE_WINDOWS: dict[str, tuple[date, date]] = {
    "Group Stage": (date(2026, 6, 11), date(2026, 6, 27)),
    "Round of 32": (date(2026, 6, 28), date(2026, 7, 3)),
    "Round of 16": (date(2026, 7, 4), date(2026, 7, 7)),
    "Quarterfinals": (date(2026, 7, 9), date(2026, 7, 11)),
    "Semifinals": (date(2026, 7, 14), date(2026, 7, 15)),
    "Third Place Playoff": (date(2026, 7, 18), date(2026, 7, 18)),
    "Final": (date(2026, 7, 19), date(2026, 7, 19)),
}


@dataclass
class StageMappingRow:
    """One row of the output stage/group mapping table."""

    match_date: str
    home_team: str
    away_team: str
    home_score: str
    away_score: str
    venue_city: str
    venue_country: str
    stage: str
    group_letter: str
    is_knockout: str


def load_group_draw(path: Path) -> dict[str, str]:
    """Load the team-to-group crosswalk as a dict of team name to group letter."""
    with path.open(newline="", encoding="utf-8") as f:
        return {row["team"]: row["group_letter"] for row in csv.DictReader(f)}


def load_world_cup_2026_matches(path: Path) -> list[dict[str, str]]:
    """Filter the full international results dataset to 2026 World Cup matches."""
    with path.open(newline="", encoding="utf-8") as f:
        matches = [
            row
            for row in csv.DictReader(f)
            if row["tournament"] == WORLD_CUP_TOURNAMENT_NAME
            and date.fromisoformat(row["date"]) >= WORLD_CUP_2026_START
        ]
    return matches


def resolve_stage(match_date: date) -> str:
    """Return the tournament stage whose date window contains match_date."""
    for stage, (start, end) in STAGE_DATE_WINDOWS.items():
        if start <= match_date <= end:
            return stage
    raise ValueError(f"No stage defined for match date {match_date.isoformat()}")


def build_stage_mapping_rows(
    matches: list[dict[str, str]], group_draw: dict[str, str]
) -> list[StageMappingRow]:
    """Enrich each match with stage and group letter."""
    rows = []
    for match in matches:
        match_date = date.fromisoformat(match["date"])
        stage = resolve_stage(match_date)
        is_knockout = stage != "Group Stage"
        group_letter = "" if is_knockout else group_draw[match["home_team"]]
        rows.append(
            StageMappingRow(
                match_date=match["date"],
                home_team=match["home_team"],
                away_team=match["away_team"],
                home_score=match["home_score"],
                away_score=match["away_score"],
                venue_city=match["city"],
                venue_country=match["country"],
                stage=stage,
                group_letter=group_letter,
                is_knockout=str(is_knockout),
            )
        )
    return rows


def write_stage_mapping(rows: list[StageMappingRow], path: Path) -> None:
    """Write the enriched rows to a CSV file."""
    fieldnames = [f.name for f in fields(StageMappingRow)]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(vars(row))


def main() -> None:
    """Regenerate data/processed/wc2026_stage_mapping.csv from raw inputs."""
    group_draw = load_group_draw(GROUP_DRAW_PATH)
    matches = load_world_cup_2026_matches(INTERNATIONAL_RESULTS_PATH)
    rows = build_stage_mapping_rows(matches, group_draw)
    write_stage_mapping(rows, OUTPUT_PATH)


if __name__ == "__main__":
    main()
