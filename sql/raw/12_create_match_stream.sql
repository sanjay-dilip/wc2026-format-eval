-- Detects new-match-arrival (INSERT) and correction (UPDATE) events on
-- RAW.MATCH for Build 8's incremental-load demonstration - the actual
-- change-detection mechanism docs/architecture.md already committed to
-- ("Streams" under Kept), not a nice-to-have. Not append-only: corrections
-- need UPDATE/METADATA$ISUPDATE visibility, not just inserts.
CREATE STREAM IF NOT EXISTS RAW.MATCH_STREAM ON TABLE RAW.MATCH;
