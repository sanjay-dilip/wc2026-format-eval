-- Standard date dimension. Covers the 2026 match date range only for now
-- (Build 5 will need to extend this once historical tournaments join).
CREATE TABLE IF NOT EXISTS CORE.DIM_DATE (
    date_id NUMBER PRIMARY KEY,
    full_date DATE NOT NULL,
    year NUMBER,
    month NUMBER,
    day NUMBER,
    day_of_week VARCHAR
);
