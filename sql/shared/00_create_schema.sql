-- SHARED holds the curated, external-facing surface for Build 9's Secure
-- Data Share - deliberately not created until now. docs/architecture.md
-- dropped it from the original schema list pending this exact decision;
-- docs/decision_log.md's 2026-08-01 "Build 9 go/no-go" entry is that
-- decision. Nothing in RAW/VALIDATION/CORE/ANALYTICS is ever granted
-- directly to the share - only objects that live in this schema are (see
-- 02_create_share_and_grants.sql).
CREATE SCHEMA IF NOT EXISTS SHARED;
