-- CSV format shared by every RAW load: header row skipped, comma-delimited,
-- matching the source files under data/raw and data/processed.
CREATE FILE FORMAT IF NOT EXISTS RAW.CSV_STANDARD
    TYPE = 'CSV'
    SKIP_HEADER = 1
    FIELD_DELIMITER = ','
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    EMPTY_FIELD_AS_NULL = TRUE;
