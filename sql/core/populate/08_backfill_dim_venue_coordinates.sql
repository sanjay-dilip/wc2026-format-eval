-- Backfills what Build 4 left NULL: venue_name and lat/long, now that
-- Build 7 has independently sourced and cited them (docs/decision_log.md).
UPDATE CORE.DIM_VENUE v
SET venue_name = vc.venue_name,
    latitude = vc.latitude,
    longitude = vc.longitude
FROM RAW.VENUE_COORDINATES vc
WHERE v.city = vc.city
  AND v.country = vc.country
