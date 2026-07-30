CREATE TABLE IF NOT EXISTS CORE.DIM_STAGE (
    stage_id NUMBER PRIMARY KEY,
    stage_name VARCHAR NOT NULL,
    stage_order NUMBER NOT NULL,
    date_window_start DATE,
    date_window_end DATE
);
