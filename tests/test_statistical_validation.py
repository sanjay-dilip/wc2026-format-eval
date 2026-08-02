"""Tests for the pure-Python helpers in src/analytics/run_statistical_validation.py.

Only the helpers that don't need a live Snowflake connection are covered
here - same split as tests/test_validation_checks.py (pure logic tested
locally, live-account behavior verified separately at run time).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analytics.run_statistical_validation import (
    RANK_BISERIAL_THRESHOLDS,
    SIGNIFICANCE_ALPHA,
    magnitude_label,
    significance_phrase,
)


def test_magnitude_label_boundaries() -> None:
    """Magnitude labels use each threshold as an inclusive lower bound."""
    assert magnitude_label(0.0, RANK_BISERIAL_THRESHOLDS) == "negligible"
    assert magnitude_label(0.1, RANK_BISERIAL_THRESHOLDS) == "small"
    assert magnitude_label(0.3, RANK_BISERIAL_THRESHOLDS) == "medium"
    assert magnitude_label(0.5, RANK_BISERIAL_THRESHOLDS) == "large"


def test_magnitude_label_uses_absolute_value() -> None:
    """A negative effect size is classified by its magnitude, not its sign."""
    assert magnitude_label(-0.6, RANK_BISERIAL_THRESHOLDS) == "large"


def test_significance_phrase_below_alpha() -> None:
    """A p-value under the fixed alpha is reported as statistically significant."""
    phrase = significance_phrase(SIGNIFICANCE_ALPHA - 0.01)
    assert "not statistically significant" not in phrase
    assert "statistically significant" in phrase


def test_significance_phrase_at_or_above_alpha() -> None:
    """A p-value at or above the fixed alpha is reported as not statistically significant."""
    assert "not statistically significant" in significance_phrase(SIGNIFICANCE_ALPHA)
    assert "not statistically significant" in significance_phrase(SIGNIFICANCE_ALPHA + 0.01)
