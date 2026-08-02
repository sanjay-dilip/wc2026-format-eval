-- Grants only ever touch the SHARED schema - never
-- RAW/VALIDATION/CORE/ANALYTICS directly - so the share's surface is
-- exactly the 8 secure views in 01_create_secure_views.sql, nothing more.
-- Each view is granted individually, by name, rather than
-- "GRANT SELECT ON ALL VIEWS IN SCHEMA ... TO SHARE" - Snowflake
-- rejects bulk (ALL/FUTURE) grants of views to a share outright
-- ("Bulk grant on objects of type VIEW to SHARE is restricted"),
-- confirmed by trying it against the live account before writing this
-- version. Adding a 9th shared view later means adding a 9th GRANT line
-- here, not just a new CREATE VIEW. WC2026 is this project's fixed
-- database name (set at Build 2, unlikely to change) - GRANT ON DATABASE
-- needs an explicit identifier, unlike every other statement in sql/
-- which relies on the connection's schema-scoped default database.
CREATE SHARE IF NOT EXISTS WC2026_SHARE;
GRANT USAGE ON DATABASE WC2026 TO SHARE WC2026_SHARE;
GRANT USAGE ON SCHEMA WC2026.SHARED TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.COMPETITIVE_BALANCE TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.GROUP_DIFFICULTY TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.UPSET_RATE TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.CONFEDERATION_PERFORMANCE TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.EXPECTED_VS_ACTUAL TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.TOURNAMENT_FORMAT_COMPARISON TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.TEAM_TRAVEL_REST TO SHARE WC2026_SHARE;
GRANT SELECT ON VIEW WC2026.SHARED.STATISTICAL_VALIDATION TO SHARE WC2026_SHARE;
