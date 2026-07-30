-- One row per record that failed a check. Nothing gets silently dropped.
CREATE TABLE IF NOT EXISTS VALIDATION.REJECTED_RECORDS (
    rejected_id NUMBER AUTOINCREMENT PRIMARY KEY,
    check_name VARCHAR,
    table_name VARCHAR,
    match_date VARCHAR,
    home_team VARCHAR,
    away_team VARCHAR,
    detail VARCHAR,
    rejected_at TIMESTAMP_NTZ
);
