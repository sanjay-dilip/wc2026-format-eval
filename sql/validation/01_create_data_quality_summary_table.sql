-- One row per check run: what was checked, how many rows failed, and when.
CREATE TABLE IF NOT EXISTS VALIDATION.DATA_QUALITY_SUMMARY (
    check_id NUMBER AUTOINCREMENT PRIMARY KEY,
    check_name VARCHAR,
    table_name VARCHAR,
    rows_checked NUMBER,
    rows_failed NUMBER,
    passed BOOLEAN,
    notes VARCHAR,
    checked_at TIMESTAMP_NTZ
);
