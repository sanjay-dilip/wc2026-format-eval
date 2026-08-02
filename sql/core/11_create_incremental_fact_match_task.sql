-- Orchestrates RAW.MATCH_STREAM's changes into CORE.FACT_MATCH via
-- CORE.SP_APPLY_MATCH_STREAM() - the "Tasks" feature docs/architecture.md
-- already committed to for Build 8. Snowflake creates tasks SUSPENDED by
-- default and this is never explicitly RESUMEd: a continuously scheduled
-- task would poll the warehouse every SCHEDULE interval regardless of
-- whether there's anything to do, real (if small) compute cost this
-- project's trial-credit constraint doesn't need to spend. The schedule
-- below documents what a production deployment would use; the actual
-- demonstration in src/incremental/demo_incremental_load.py drives this
-- with an explicit EXECUTE TASK, on demand, not the schedule.
CREATE TASK IF NOT EXISTS CORE.INCREMENTAL_FACT_MATCH_TASK
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = '60 MINUTE'
AS
    CALL CORE.SP_APPLY_MATCH_STREAM();
