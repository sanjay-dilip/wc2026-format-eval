-- One row per COPY INTO run: what was loaded, which warehouse ran it, how
-- long it took, and how many credits that warehouse burned in the process.
CREATE TABLE IF NOT EXISTS AUDIT.LOAD_LOG (
    load_id NUMBER AUTOINCREMENT PRIMARY KEY,
    target_table VARCHAR,
    source_file VARCHAR,
    rows_loaded NUMBER,
    warehouse_name VARCHAR,
    load_started_at TIMESTAMP_NTZ,
    load_ended_at TIMESTAMP_NTZ,
    duration_seconds NUMBER,
    credits_used FLOAT
);
