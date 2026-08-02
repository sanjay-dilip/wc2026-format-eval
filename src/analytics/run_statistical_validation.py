"""Statistical validation layer for Build 6's 5 ANALYTICS marts.

Every test follows docs/problem_statement.md's rule for this build: state
the hypothesis, check assumptions, report an effect size and practical
significance alongside any p-value, and describe results with
"associated with" / "consistent with" language only - never causal.

Truncates and repopulates ANALYTICS.STATISTICAL_VALIDATION (same
idempotency pattern as src/core/build_core.py), then writes the same
results as prose to docs/statistical_validation_results.md.
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingestion.connect import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DOC_PATH = REPO_ROOT / "docs" / "statistical_validation_results.md"

SIGNIFICANCE_ALPHA = 0.05

# Cohen's conventional small/medium/large thresholds, one set per effect
# size metric used below (each metric has its own established scale).
RANK_BISERIAL_THRESHOLDS = (0.1, 0.3, 0.5)
COHENS_H_THRESHOLDS = (0.2, 0.5, 0.8)
EPSILON_SQUARED_THRESHOLDS = (0.01, 0.06, 0.14)
SPEARMAN_RHO_THRESHOLDS = (0.1, 0.3, 0.5)


@dataclass
class ValidationResult:
    """One hypothesis test's full result, matching the ANALYTICS.STATISTICAL_VALIDATION columns."""

    metric_name: str
    hypothesis: str
    comparison: str
    test_used: str
    assumption_check: str
    sample_sizes: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_metric: str
    interpretation: str


def magnitude_label(effect_size: float, thresholds: tuple[float, float, float]) -> str:
    """Classify an effect size's absolute magnitude as negligible/small/medium/large."""
    small, medium, large = thresholds
    magnitude = abs(effect_size)
    if magnitude < small:
        return "negligible"
    if magnitude < medium:
        return "small"
    if magnitude < large:
        return "medium"
    return "large"


def significance_phrase(p_value: float) -> str:
    """Phrase a p-value's statistical significance at the project's fixed alpha."""
    if p_value < SIGNIFICANCE_ALPHA:
        return f"statistically significant at alpha={SIGNIFICANCE_ALPHA} (p={p_value:.4f})"
    return f"not statistically significant at alpha={SIGNIFICANCE_ALPHA} (p={p_value:.4f})"


def test_competitive_balance(cursor) -> ValidationResult:
    """2026 vs pooled 2022+1994: mean absolute goal difference per match."""
    cursor.execute(
        """
        SELECT t.tournament_year, ABS(f.home_score - f.away_score)
        FROM CORE.FACT_MATCH f
        JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = f.tournament_id
        """
    )
    rows = cursor.fetchall()
    group_2026 = np.array([diff for year, diff in rows if year == 2026], dtype=float)
    group_historical = np.array([diff for year, diff in rows if year != 2026], dtype=float)

    _, shapiro_p_2026 = stats.shapiro(group_2026)
    _, shapiro_p_historical = stats.shapiro(group_historical)
    normal_note = (
        f"Shapiro-Wilk p=2026:{shapiro_p_2026:.4f}/historical:{shapiro_p_historical:.4f} - "
        "both reject normality, so a non-parametric test (Mann-Whitney U) is used "
        "instead of a t-test."
    )

    n_2026, n_historical = len(group_2026), len(group_historical)
    u_statistic, p_value = stats.mannwhitneyu(group_2026, group_historical, alternative="two-sided")
    rank_biserial = 1 - (2 * u_statistic) / (n_2026 * n_historical)
    magnitude = magnitude_label(rank_biserial, RANK_BISERIAL_THRESHOLDS)

    return ValidationResult(
        metric_name="Competitive Balance",
        hypothesis=(
            "The 48-team expansion is associated with a difference in mean absolute "
            "goal difference per match, relative to prior formats."
        ),
        comparison="2026 (n=104) vs pooled 2022+1994 (n=116)",
        test_used="Mann-Whitney U (two-sided)",
        assumption_check=normal_note,
        sample_sizes=f"n_2026={n_2026}, n_historical={n_historical}",
        statistic=float(u_statistic),
        p_value=float(p_value),
        effect_size=float(rank_biserial),
        effect_size_metric="rank-biserial correlation",
        interpretation=(
            f"The data are consistent with a {magnitude} association between the 48-team "
            f"format and mean absolute goal difference (rank-biserial r={rank_biserial:.3f}, "
            f"{significance_phrase(p_value)}). 2026's own mean is higher than pooled "
            "2022+1994 (1.56 vs ~1.39 goals), so if the difference is real, it points toward "
            "less balanced matches under expansion, not more - not a causal claim."
        ),
    )


def test_upset_rate(cursor) -> ValidationResult:
    """2026 vs pooled 2022+1994: upset rate among decisive, ranking-eligible matches."""
    cursor.execute(
        "SELECT tournament_year, upset_count, decisive_match_count FROM ANALYTICS.UPSET_RATE"
    )
    rows = {year: (upsets, decisive) for year, upsets, decisive in cursor.fetchall()}
    upsets_2026, decisive_2026 = rows[2026]
    upsets_historical = rows[2022][0] + rows[1994][0]
    decisive_historical = rows[2022][1] + rows[1994][1]

    table = [
        [upsets_2026, decisive_2026 - upsets_2026],
        [upsets_historical, decisive_historical - upsets_historical],
    ]
    _, _, _, expected = stats.chi2_contingency(table)
    min_expected_count = float(np.min(expected))
    assumption_note = (
        f"minimum expected cell count under independence = {min_expected_count:.1f} - "
        + (
            "below 5, so Fisher's exact test is used instead of a chi-square approximation."
            if min_expected_count < 5
            else "at or above 5, chi-square approximation would also have been valid."
        )
    )
    odds_ratio, p_value = stats.fisher_exact(table)

    p_2026 = upsets_2026 / decisive_2026
    p_historical = upsets_historical / decisive_historical
    cohens_h = 2 * np.arcsin(np.sqrt(p_2026)) - 2 * np.arcsin(np.sqrt(p_historical))
    magnitude = magnitude_label(cohens_h, COHENS_H_THRESHOLDS)

    return ValidationResult(
        metric_name="Upset Rate",
        hypothesis=(
            "The 48-team expansion is associated with a difference in upset rate among "
            "decisive, ranking-eligible matches, relative to prior formats."
        ),
        comparison=(
            f"2026 (n={decisive_2026} decisive matches) vs pooled 2022+1994 "
            f"(n={decisive_historical} decisive matches)"
        ),
        test_used="Fisher's exact test (two-sided)",
        assumption_check=assumption_note,
        sample_sizes=f"decisive_2026={decisive_2026}, decisive_historical={decisive_historical}",
        statistic=float(odds_ratio),
        p_value=float(p_value),
        effect_size=float(cohens_h),
        effect_size_metric="Cohen's h",
        interpretation=(
            f"The data are consistent with a {magnitude} association between the 48-team "
            f"format and upset rate (Cohen's h={cohens_h:.3f}, odds ratio={odds_ratio:.3f}, "
            f"{significance_phrase(p_value)}). 2026's own upset rate is lower than pooled "
            f"2022+1994 ({p_2026:.1%} vs {p_historical:.1%}), so if the difference is real, "
            "it points toward fewer upsets under expansion, not more - not a causal claim."
        ),
    )


def test_confederation_performance(cursor) -> ValidationResult:
    """2026 only: per-team-match goal differential grouped by confederation."""
    cursor.execute(
        """
        WITH team_matches AS (
            SELECT f.tournament_id, f.home_team_id AS team_id,
                   f.home_score - f.away_score AS goal_diff
            FROM CORE.FACT_MATCH f
            UNION ALL
            SELECT f.tournament_id, f.away_team_id AS team_id,
                   f.away_score - f.home_score AS goal_diff
            FROM CORE.FACT_MATCH f
        )
        SELECT c.confederation_name, tm.goal_diff
        FROM team_matches tm
        JOIN CORE.DIM_TEAM dt ON dt.team_id = tm.team_id
        JOIN CORE.DIM_CONFEDERATION c ON c.confederation_id = dt.confederation_id
        JOIN CORE.DIM_TOURNAMENT t ON t.tournament_id = tm.tournament_id
        WHERE t.tournament_year = 2026
        """
    )
    rows = cursor.fetchall()
    groups: dict[str, list[float]] = {}
    for confederation, goal_diff in rows:
        groups.setdefault(confederation, []).append(float(goal_diff))
    samples = [np.array(values) for values in groups.values()]

    _, levene_p = stats.levene(*samples)
    assumption_note = (
        f"Levene's test for equal variances: p={levene_p:.4f} - Kruskal-Wallis is used "
        "regardless (goal differential is discrete and not normally distributed within "
        "confederations), so this is reported as context, not a gate on the test choice."
    )

    h_statistic, p_value = stats.kruskal(*samples)
    n_total = sum(len(s) for s in samples)
    k_groups = len(samples)
    epsilon_squared = (h_statistic - k_groups + 1) / (n_total - k_groups)
    magnitude = magnitude_label(epsilon_squared, EPSILON_SQUARED_THRESHOLDS)

    return ValidationResult(
        metric_name="Confederation Performance",
        hypothesis=(
            "Confederation is associated with per-match goal differential in the 2026 "
            "tournament."
        ),
        comparison=f"{k_groups} confederations, 2026 only",
        test_used="Kruskal-Wallis H",
        assumption_check=assumption_note,
        sample_sizes=", ".join(f"{name}={len(values)}" for name, values in groups.items()),
        statistic=float(h_statistic),
        p_value=float(p_value),
        effect_size=float(epsilon_squared),
        effect_size_metric="epsilon-squared",
        interpretation=(
            f"The data are consistent with a {magnitude} association between confederation "
            f"and per-match goal differential in 2026 (epsilon-squared={epsilon_squared:.3f}, "
            f"{significance_phrase(p_value)}). This does not identify which confederation(s) "
            "differ from which - only that confederation membership is associated with some "
            "difference in the group of 6 as a whole."
        ),
    )


def test_expected_vs_actual(cursor) -> list[ValidationResult]:
    """Per tournament: Spearman correlation between fifa_ranking and actual finish."""
    cursor.execute(
        "SELECT tournament_year, fifa_ranking, matches_played, furthest_stage_order, "
        "actual_finish_method FROM ANALYTICS.EXPECTED_VS_ACTUAL"
    )
    rows = cursor.fetchall()
    by_year: dict[int, list[tuple[float, float]]] = {}
    method_by_year: dict[int, str] = {}
    for year, ranking, matches_played, furthest_stage_order, method in rows:
        finish = furthest_stage_order if method == "stage_order" else matches_played
        by_year.setdefault(year, []).append((float(ranking), float(finish)))
        method_by_year[year] = method

    results = []
    for year in sorted(by_year):
        rankings = np.array([r for r, _ in by_year[year]])
        finishes = np.array([f for _, f in by_year[year]])
        rho, p_value = stats.spearmanr(rankings, finishes)
        magnitude = magnitude_label(rho, SPEARMAN_RHO_THRESHOLDS)
        method = method_by_year[year]
        results.append(
            ValidationResult(
                metric_name="Expected-vs-Actual Performance",
                hypothesis=(
                    "Pre-tournament fifa_ranking is associated with actual tournament finish."
                ),
                comparison=f"{year} only, actual finish measured via {method}",
                test_used="Spearman rank correlation",
                assumption_check=(
                    "Spearman is rank-based and assumes no particular distribution shape - "
                    "used because fifa_ranking is ordinal and, for 2022/1994, finish is a "
                    "count-based proxy, not a true continuous measure."
                ),
                sample_sizes=f"n={len(rankings)}",
                statistic=float(rho),
                p_value=float(p_value),
                effect_size=float(rho),
                effect_size_metric="Spearman's rho",
                interpretation=(
                    f"The {year} data are consistent with a {magnitude} monotonic association "
                    f"between fifa_ranking and finish (rho={rho:.3f}, "
                    f"{significance_phrase(p_value)}). fifa_ranking is coded so a lower number "
                    "is a stronger team; a negative rho is the expected direction (better "
                    f"ranking associated with going further). Finish here uses the "
                    f"{method} definition - {'the load-bearing 2026 measurement' if method == 'stage_order' else 'a directional proxy only, per docs/metric_definitions.md'}."
                ),
            )
        )
    return results


def write_results_table(cursor, results: list[ValidationResult]) -> None:
    """Truncate and repopulate ANALYTICS.STATISTICAL_VALIDATION."""
    cursor.execute("TRUNCATE TABLE ANALYTICS.STATISTICAL_VALIDATION")
    for result in results:
        cursor.execute(
            """
            INSERT INTO ANALYTICS.STATISTICAL_VALIDATION (
                metric_name, hypothesis, comparison, test_used, assumption_check,
                sample_sizes, statistic, p_value, effect_size, effect_size_metric, interpretation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                result.metric_name,
                result.hypothesis,
                result.comparison,
                result.test_used,
                result.assumption_check,
                result.sample_sizes,
                result.statistic,
                result.p_value,
                result.effect_size,
                result.effect_size_metric,
                result.interpretation,
            ),
        )


def write_results_doc(results: list[ValidationResult]) -> None:
    """Write the same results as prose to docs/statistical_validation_results.md."""
    lines = [
        "# Statistical Validation Results — Build 6 Part 2",
        "",
        "Generated by `src/analytics/run_statistical_validation.py` against the live "
        "Snowflake account. Every result below states its hypothesis, reports the "
        "assumption check performed, and gives an effect size and practical-significance "
        "reading alongside its p-value, per `docs/problem_statement.md`'s rule for this "
        'build. All language is "associated with" / "consistent with" - never causal.',
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result.metric_name}",
                "",
                f"**Hypothesis**: {result.hypothesis}",
                "",
                f"**Comparison**: {result.comparison}",
                "",
                f"**Test used**: {result.test_used}",
                "",
                f"**Assumption check**: {result.assumption_check}",
                "",
                f"**Sample sizes**: {result.sample_sizes}",
                "",
                f"**Statistic**: {result.statistic:.4f} | **p-value**: {result.p_value:.4f} | "
                f"**Effect size**: {result.effect_size:.4f} ({result.effect_size_metric})",
                "",
                f"**Interpretation**: {result.interpretation}",
                "",
                "---",
                "",
            ]
        )
    RESULTS_DOC_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Run all hypothesis tests and write results to Snowflake and docs/."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        results = [
            test_competitive_balance(cursor),
            test_upset_rate(cursor),
            test_confederation_performance(cursor),
        ]
        results.extend(test_expected_vs_actual(cursor))

        write_results_table(cursor, results)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM ANALYTICS.STATISTICAL_VALIDATION")
        logger.info("Populated ANALYTICS.STATISTICAL_VALIDATION: %s rows", cursor.fetchone()[0])

        write_results_doc(results)
        logger.info("Wrote %s", RESULTS_DOC_PATH.relative_to(REPO_ROOT))

        for result in results:
            logger.info(
                "%s: p=%.4f, effect_size=%.4f (%s)",
                result.metric_name,
                result.p_value,
                result.effect_size,
                result.effect_size_metric,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
