-- One row per hypothesis test run by
-- src/analytics/run_statistical_validation.py. Every column required by
-- docs/problem_statement.md's validation rule (hypothesis, effect size,
-- practical significance alongside any p-value) is a first-class column
-- here, not left implicit in a comment - so a query against this table
-- alone, with no code alongside it, still carries the full result.
CREATE TABLE IF NOT EXISTS ANALYTICS.STATISTICAL_VALIDATION (
    row_id NUMBER AUTOINCREMENT PRIMARY KEY,
    metric_name VARCHAR NOT NULL,
    hypothesis VARCHAR NOT NULL,
    comparison VARCHAR NOT NULL,
    test_used VARCHAR NOT NULL,
    assumption_check VARCHAR NOT NULL,
    sample_sizes VARCHAR NOT NULL,
    statistic FLOAT NOT NULL,
    p_value FLOAT NOT NULL,
    effect_size FLOAT NOT NULL,
    effect_size_metric VARCHAR NOT NULL,
    interpretation VARCHAR NOT NULL
);
