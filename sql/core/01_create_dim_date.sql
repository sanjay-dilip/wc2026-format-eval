-- Standard date dimension. Covers the 2026 match date range plus each
-- Build 5 historical comparison tournament's own date range (populate
-- query unions per-tournament windows, not one span covering the gap
-- years too - see sql/core/populate/01_dim_date.sql).
CREATE TABLE IF NOT EXISTS CORE.DIM_DATE (
    date_id NUMBER PRIMARY KEY,
    full_date DATE NOT NULL,
    year NUMBER,
    month NUMBER,
    day NUMBER,
    day_of_week VARCHAR
);
