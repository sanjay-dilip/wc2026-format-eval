-- Reusing the trial account's default COMPUTE_WH rather than creating a new
-- one. Forcing auto-suspend/auto-resume here protects the trial's credit
-- balance regardless of whatever the account default was.
ALTER WAREHOUSE COMPUTE_WH SET
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;
