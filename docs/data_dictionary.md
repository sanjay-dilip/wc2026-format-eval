# Data Dictionary — 2026 World Cup Format Evaluation

Status: Column-level and structural documentation only. For source provenance,
licensing, and reliability tiering, see `docs/data_feasibility_report.md`. For
why a given source/crosswalk was chosen over alternatives, see
`docs/decision_log.md`. This document does not repeat either.

Compiled: 2026-07-28. Verified directly against the files on disk in
`data/raw/` and `data/processed/` — every row count, null count, and
uniqueness check below was run with a script (`csv` module, exact string
comparison; no assumptions from filenames or prior docs). Method: full parse
of each file's rows, per-column null count (empty string after strip), unique
value count, and explicit duplicate-key check on the candidate join key.

---

## `data/raw/international_results_full.csv`

- **Produced by**: Raw pull, unmodified. Corresponds to `results.csv` from
  the martj42/international_results source (see feasibility report, Source 1).
- **Grain**: One row per international football match, all competitions,
  1872–2026-07-19.
- **Row count**: 49,520 data rows (49,521 lines including header). Counted
  directly, not assumed from `wc -l`.
- **File size on disk**: 3,727,748 bytes (~3.6 MiB).
- **Columns**:

| Column | Inferred type | Nullable (verified) | Unique values | Example |
|---|---|---|---|---|
| `date` | date (string, `YYYY-MM-DD`) | No (0 nulls) | 16,491 | `1872-11-30` |
| `home_team` | string (categorical) | No (0 nulls) | 328 | `Scotland` |
| `away_team` | string (categorical) | No (0 nulls) | 322 | `England` |
| `home_score` | integer | No (0 nulls) | 26 | `0` |
| `away_score` | integer | No (0 nulls) | 22 | `0` |
| `tournament` | string (categorical) | No (0 nulls) | 201 | `Friendly` |
| `city` | string | No (0 nulls) | 2,092 | `Glasgow` |
| `country` | string | No (0 nulls) | 269 | `Scotland` |
| `neutral` | boolean (string `TRUE`/`FALSE`) | No (0 nulls) | 2 | `FALSE` |

- **Candidate join key**: `date + home_team + away_team`. **Checked, not
  assumed: NOT unique.** 49,519 unique combinations out of 49,520 rows — one
  duplicate:
  - `1974-02-17, Tahiti, New Caledonia` appears twice, with different scores
    (2–1 and 1–2). This looks like either a genuine same-day double-header
    or an upstream data-entry error (e.g. a swapped-scoreline duplicate).
    Not resolved here — flagging it rather than silently deduping, since
    picking one row would be a judgment call this doc shouldn't make alone.
- **Known limitations (file-specific)**:
  - The duplicate key above means any downstream join on
    `date+home_team+away_team` must either tolerate a 1-row fan-out for this
    specific match or explicitly filter it.
  - This file is the full 1872–2026 history; only 104 of its 49,520 rows are
    the 2026 World Cup matches actually needed for this project's tournament
    analysis (see next file).

---

## `data/raw/shootouts_full.csv`

- **Produced by**: Raw pull, unmodified. Corresponds to `shootouts.csv` from
  the same source as above.
- **Grain**: One row per international match that was decided by a penalty
  shootout, all competitions.
- **Row count**: 683 data rows.
- **File size on disk**: 29,050 bytes.
- **Columns**:

| Column | Inferred type | Nullable (verified) | Unique values | Example |
|---|---|---|---|---|
| `date` | date (string, `YYYY-MM-DD`) | No (0 nulls) | 596 | `1967-08-22` |
| `home_team` | string | No (0 nulls) | 189 | `India` |
| `away_team` | string | No (0 nulls) | 199 | `Taiwan` |
| `winner` | string | No (0 nulls) | 184 | `Taiwan` |
| `first_shooter` | string | **Yes — 423 / 683 nulls (61.9%)** | 97 (incl. blank) | `Czechoslovakia` |

- **Candidate join key**: `date + home_team + away_team`. **Checked and
  confirmed unique**: 683 unique combinations across 683 rows, 0 duplicates.
- **Known limitations (file-specific)**: `first_shooter` is null in nearly
  two-thirds of rows — usable for shootout outcome (`winner`) but not
  reliable for any analysis specifically about which team shot first.

---

## `data/raw/wc2026_matches_raw_subset.csv` — flagged, not raw

**This file should not be treated as raw input as currently structured or
located. Two separate issues, not silently fixed here:**

1. **It is not raw — it is a filtered derivative of
   `international_results_full.csv`, sitting in `data/raw/`.** Verified
   directly: every one of its 104 rows matches, value-for-value on all
   shared columns, a row in `international_results_full.csv` where
   `tournament == "FIFA World Cup"` and `date >= 2026-01-01` (e.g. its first
   row, `2026-06-11,Mexico,South Africa,2,0,...`, is byte-identical to line
   49,418 of the parent file). Filtering 49,520 rows down to 104 is a
   transformation, not a pull.
2. **The file has no header row.** Its first line is already data
   (`2026-06-11,Mexico,South Africa,2,0,...`). Column names below are
   inferred by matching column order and values against
   `international_results_full.csv`, not read from the file itself — loading
   this file with a default `pandas.read_csv()` today will silently treat
   that first match as a header and lose it.

**Recommendation**: Don't just rename or move this file without deciding
which problem it's solving. Two options, either is better than the status
quo:
- If a static WC2026-only file is wanted for convenience, move it to a
  `data/interim/` (or `data/processed/`) location, add the missing header
  row, and document it as derived.
- Better: regenerate it on demand via a small committed script (e.g.
  `scripts/filter_wc2026.py`) that filters `international_results_full.csv`
  at run time, so there's no static duplicate that can silently drift out of
  sync if the raw file is ever refreshed.

- **Grain** (as currently structured): one row per 2026 FIFA World Cup match.
- **Row count**: 104 data rows (matches the confirmed official count).
- **File size on disk**: 7,883 bytes.
- **Columns** (inferred — see header issue above): `date`, `home_team`,
  `away_team`, `home_score`, `away_score`, `tournament`, `city`, `country`,
  `neutral` — same types as `international_results_full.csv` above. No nulls
  in any column (checked).
- **Candidate join key**: `date + home_team + away_team`. Checked and
  confirmed unique: 104/104.

---

## `data/processed/wc2026_stage_mapping.csv`

- **Produced by**: Derived. Joins the 104 WC2026 matches (home/away teams,
  scores, venue city/country) against the manually transcribed Yahoo Sports
  stage/group crosswalk described in the feasibility report (Source 4) and
  decision log (2026-07-21 entry). Not a raw pull from any single source.
- **Grain**: One row per 2026 FIFA World Cup match, enriched with tournament
  stage and group.
- **Row count**: 104 data rows.
- **File size on disk**: 8,028 bytes.
- **Columns**:

| Column | Inferred type | Nullable (verified) | Unique values | Example |
|---|---|---|---|---|
| `match_date` | date (string, `YYYY-MM-DD`) | No (0 nulls) | 34 | `2026-06-11` |
| `home_team` | string | No (0 nulls) | 48 | `Mexico` |
| `away_team` | string | No (0 nulls) | 46 | `South Africa` |
| `home_score` | integer | No (0 nulls) | 8 | `2` |
| `away_score` | integer | No (0 nulls) | 7 | `0` |
| `venue_city` | string | No (0 nulls) | 17 | `Mexico City` |
| `venue_country` | string | No (0 nulls) | 3 | `Mexico` |
| `stage` | string (categorical) | No (0 nulls) | 7 | `Group Stage` |
| `group_letter` | string (categorical) | **Yes — 32 / 104 nulls** | 13 (incl. blank) | `A` |
| `is_knockout` | boolean (string `True`/`False`) | No (0 nulls) | 2 | `False` |

- **Candidate join key**: `match_date + home_team + away_team`. Checked and
  confirmed unique: 104/104.
- **Verified structural check**: `stage` value counts are exactly
  `Group Stage=72, Round of 32=16, Round of 16=8, Quarterfinals=4,
  Semifinals=2, Third Place Playoff=1, Final=1` (sums to 104), and
  `is_knockout` splits exactly `False=72 / True=32`. This matches the
  72/16/8/4/2/1/1 validation already recorded in the feasibility report — not
  re-deriving that validation, just confirming the file on disk still
  reflects it.
- **`group_letter` nulls are structural, not a data quality defect**: all 32
  null rows are exactly the 32 knockout-stage rows (Round of 32 through
  Final), where a team's original group is not tracked in this table.
  Confirmed by cross-tabulating nulls against `stage` directly.
- **Known limitations (file-specific)**:
  - No group lookup for knockout-stage teams — a group-based analysis that
    needs to cover knockout matches (e.g. "how did Group C teams perform in
    the Round of 16") needs a separate team→group table, not derivable from
    this file alone once a team is past the group stage.
  - Depends on the Yahoo Sports crosswalk, which the decision log already
    flags as a single non-official source pending a second independent
    cross-check — not re-litigated here.

---

## Not yet verified / out of scope for this pass

- No `data/interim/` directory currently exists — the recommendation above
  to relocate `wc2026_matches_raw_subset.csv` would create one.
- Encoding was not independently audited beyond successful UTF-8 parsing of
  all four files with no decode errors; no BOM or non-UTF-8 byte sequences
  were checked for explicitly.
- No content validation beyond structural checks above (e.g. no check that
  `home_score`/`away_score` values are non-negative integers in a sane range,
  no check that every team name in `wc2026_stage_mapping.csv` matches the
  spelling convention documented in the decision log for the other three
  files).
