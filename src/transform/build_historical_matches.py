"""Build the historical-comparison match table (data/processed/wc_historical_matches.csv).

Filters the full historical results dataset down to the World Cups this
project uses as a comparison baseline against 2026, per Build 5
(docs/build_plan.md): 2022 (32-team format) and 1994 (24-team format).
Chosen deliberately, not "all history" - see docs/decision_log.md for why
these two years and not others.

Unlike wc2026_stage_mapping.csv, there is no verified stage/round source
for these years in this project (the Yahoo Sports crosswalk Build 0 used
is 2026-specific) - so this output carries no stage/group columns at all,
rather than guessing. See docs/decision_log.md for the same reasoning
Build 4 already applied to went_to_et/neutral_site.

The `neutral` column IS carried through here (unlike wc2026_stage_mapping.csv,
which dropped it - see docs/decision_log.md, Build 4 entry) since this is a
fresh extraction, not constrained by that earlier decision.
"""

import csv
from dataclasses import dataclass, fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERNATIONAL_RESULTS_PATH = REPO_ROOT / "data" / "raw" / "international_results_full.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "wc_historical_matches.csv"

WORLD_CUP_TOURNAMENT_NAME = "FIFA World Cup"

# The specific prior tournaments this project compares 2026 against -
# deliberately not "every World Cup ever played". See docs/decision_log.md.
COMPARISON_YEARS = [2022, 1994]


@dataclass
class HistoricalMatchRow:
    """One row of the historical-comparison match table."""

    tournament_year: str
    match_date: str
    home_team: str
    away_team: str
    home_score: str
    away_score: str
    venue_city: str
    venue_country: str
    neutral_site: str


def load_historical_world_cup_matches(
    path: Path, comparison_years: list[int]
) -> list[dict[str, str]]:
    """Filter the full international results dataset to World Cup matches
    from the given comparison years."""
    with path.open(newline="", encoding="utf-8") as f:
        matches = [
            row
            for row in csv.DictReader(f)
            if row["tournament"] == WORLD_CUP_TOURNAMENT_NAME
            and int(row["date"][:4]) in comparison_years
        ]
    return matches


def build_historical_match_rows(matches: list[dict[str, str]]) -> list[HistoricalMatchRow]:
    """Convert filtered raw rows into the output row shape."""
    rows = []
    for match in matches:
        rows.append(
            HistoricalMatchRow(
                tournament_year=match["date"][:4],
                match_date=match["date"],
                home_team=match["home_team"],
                away_team=match["away_team"],
                home_score=match["home_score"],
                away_score=match["away_score"],
                venue_city=match["city"],
                venue_country=match["country"],
                neutral_site=match["neutral"],
            )
        )
    return rows


def write_historical_matches(rows: list[HistoricalMatchRow], path: Path) -> None:
    """Write the filtered rows to a CSV file, sorted for a stable diff."""
    fieldnames = [f.name for f in fields(HistoricalMatchRow)]
    rows_sorted = sorted(rows, key=lambda r: (r.tournament_year, r.match_date, r.home_team))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_sorted:
            writer.writerow(vars(row))


def main() -> None:
    """Regenerate data/processed/wc_historical_matches.csv from raw inputs."""
    matches = load_historical_world_cup_matches(INTERNATIONAL_RESULTS_PATH, COMPARISON_YEARS)
    rows = build_historical_match_rows(matches)
    write_historical_matches(rows, OUTPUT_PATH)


if __name__ == "__main__":
    main()
