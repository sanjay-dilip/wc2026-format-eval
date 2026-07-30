# Decision Log — 2026 World Cup Format Evaluation

## 2026-07-30 — Build 7 research: venue coordinates independently sourced

**Decision**: `data/raw/wc2026_venue_coordinates.csv` (16 venues, one row
each) is the independently re-verified replacement for the venue
coordinates that were ruled out in Build 0's feasibility pass (open
blocker #3). Each row cites its own Wikipedia source URL — not copied
from the disqualified "FIFA-World-Cup-2026-Dataset" repo
(`docs/data_feasibility_report.md`, Source 3: no LICENSE file, confirmed
fabricated data elsewhere in the same repo).

**Why Wikipedia**: `docs/data_feasibility_report.md` characterizes venue
coordinates as "public facts, easily re-sourced" — this isn't a
disputed-numbers problem the way rankings or tactical stats are, it's a
sourcing-and-citation problem. Wikipedia's per-stadium infobox
coordinates are independently checkable (each cites its own primary
source in turn) and structurally distinct from the disqualified repo:
no licensing conflict (facts aren't copyrightable), no relation to that
repo's confirmed fabrication.

**Cross-checks performed**:
- The 16-stadium list itself was verified against Wikipedia's "2026 FIFA
  World Cup" venues section, independent of any per-stadium page.
- Every city name in the coordinates file was checked for exact string
  match against `RAW.MATCH`'s 16 normalized venue cities (after the
  Dallas→Arlington fix in PR #10) — zero missing, zero extra.
- Guadalupe (not Monterrey) and Zapopan (not Guadalajara) were confirmed
  directly from each stadium's own Wikipedia article, matching what
  `RAW.MATCH` already records — these are real suburb/city distinctions,
  not naming inconsistencies like Dallas/Arlington.

**Not yet done**: A second independent source per venue (the same
standard the group draw and confederation crosswalk are held to,
pending). Coordinates are precise enough for the intended use (travel
distance between consecutive venues) but each one is currently backed by
a single source. Loading these into `dim_venue` and building the
travel-distance mart is Build 7's implementation, done separately from
this research pass. Also depends on PR #10 (Dallas/Arlington fix)
merging first, so coordinates get backfilled onto the correctly-deduped
16-row `dim_venue`, not a 17-row table with a phantom duplicate.

---

## 2026-07-30 — Build 4: zero-copy clone of CORE cut for the initial load

**Decision**: Do not zero-copy clone `CORE` before populating it for the
first time in Build 4.

**Why**: Build 1 kept zero-copy cloning provisionally, explicitly deferring
the cost/benefit call to Build 4 ("revisit at that point, don't assume it
still holds" — `docs/architecture.md`). The actual justification for
cloning is protection against a risky transformation mutating *existing*
valuable data. `CORE`'s tables are empty going into this build — there is
no prior state worth protecting, and Time Travel (already kept, per
`docs/architecture.md`) already gives a free rollback path for anything
that goes wrong during this session. Cloning empty tables adds no real
protection here.

**Revisit condition**: Once `CORE` holds validated data that a later build
would risk mutating (e.g. a schema change or backfill after Build 5/6),
re-apply the original justification then, not retroactively here.

---

## 2026-07-30 — Team→confederation crosswalk compiled, not scraped

**Decision**: `data/raw/wc2026_confederation_map.csv` (48 teams → 6 FIFA
confederations) is compiled directly from known 2026 World Cup qualifying
outcomes, not pulled from any external file or source in this repo — no
confederation data existed anywhere in the project before this.

**Why**: Unlike the venue-coordinate problem (Source 3, ruled out for
license and fabrication reasons), FIFA confederation membership by country
is stable, publicly known, and not the kind of fact that gets fabricated
or disputed between sources — there's no equivalent "unlicensed repo with
plausible-looking numbers" risk here. The compiled split (16 UEFA / 10 CAF
/ 9 AFC / 6 CONCACAF / 6 CONMEBOL / 1 OFC = 48) was checked against the
confirmed 48-team roster (`data/raw/wc2026_group_draw.csv`) for exact name
match — zero missing, zero extra.

**Residual risk, stated plainly**: A small number of teams reached the
tournament via intercontinental or confederation playoff routes (e.g.
Iraq, Jordan, DR Congo) rather than direct qualification. The confederation
assignment itself is not in question (playoff route doesn't change which
confederation a team belongs to), but this crosswalk has not been
cross-checked against a second independent source the way the group draw
was. Treat it the same way the group draw is treated pending its own
second cross-check: usable, not yet load-bearing in a published claim
without one.

---

## 2026-07-30 — Build 4: `went_to_et` and `neutral_site` left NULL in `fact_match`

**Decision**: `fact_match.went_to_et` and `fact_match.neutral_site` are
populated as `NULL` for all 104 rows in Build 4, not derived or guessed.

**Why**: `docs/data_dictionary.md` documents that `home_score`/`away_score`
in the Jürisoo source are already FT+ET combined, with no separate
regulation-time-only score field — so there is no way to tell, from data
currently in `RAW`, whether a given knockout match actually went to extra
time versus being decided in 90 minutes. Similarly, the upstream source
(`international_results_full.csv`) carries a `neutral` flag, but
`data/processed/wc2026_stage_mapping.csv` (the actual `RAW.MATCH` load
source) does not carry that column through — it was dropped when the
Build 0 transform was built, before this need was identified.
`went_to_so` *is* derivable (a shootout record for the match exists or it
doesn't) and is populated correctly.

**Revisit condition**: If `neutral_site` is needed later, extend
`src/transform/build_stage_mapping.py`'s output to carry the `neutral`
column through from `international_results_full.csv` (surgical change,
not now — that CSV is a validated, committed artifact, not touched as a
side effect of Build 4). `went_to_et` would need a genuinely new source
with regulation-time scores; none has been found in this project.

---

## 2026-07-21 — Match-results backbone: use martj42/international_results, not a 2026-specific dataset

**Decision**: The CC0-licensed, historically-maintained Jürisoo dataset is the source of record for match results and historical comparison, in preference to any of the 2026-specific Kaggle/GitHub datasets found.

**Why**: Verified by direct download — 104/104 2026 WC matches present, correct through the final, license confirmed CC0 (zero reuse risk), scoring convention documented (FT+ET, excludes shootouts). The alternative 2026-specific datasets looked more complete on paper but were not built to the same standard.

**Risk in the rejected alternatives**: The most feature-rich 2026-specific dataset (mominullptr) markets itself as having "zero synthetic data," but its own generation script was found, on direct inspection, to fabricate player market values via a seeded random-number formula and to hardcode xG figures with no source citation. Had this been adopted without inspection, synthetic numbers would have entered the pipeline labeled as real.

**What this does NOT solve**: Stage/round labeling and lineups are not in this dataset. Addressed separately below.

---

## 2026-07-21 — Tactical efficiency theme: downgrade, pending confirmation

**Decision**: Treat "tactical efficiency" as at-risk in its originally scoped form (event-level xG, pressures, possession value).

**Why**: Direct inspection of StatsBomb's live `competitions.json` shows no 2026 FIFA World Cup entry in their free open-data tier. No other free, reputable, event-level source was identified in this pass.

**Action needed before final scoping**: Either confirm FIFA's own match-centre aggregate stats (shots, possession, final-third entries — seen directly on the final's match page) can substitute at a shallower grain, or formally cut this theme. Not yet decided — flagged here so it isn't silently dropped later without a record of why.

---

## 2026-07-21 — Stage and Group dimensions: sourced from Yahoo Sports, not Wikipedia, not the unlicensed repo

**Decision**: Round date-boundaries and the 12-group draw are sourced from a Yahoo Sports schedule article, not Wikipedia.

**Why**: Per this project's own research-rules hierarchy, Wikipedia is a community source and ranks below "reputable sports-data providers." FIFA.com — the actually-preferred tier — was attempted directly and found technically inaccessible (JS-rendered SPA, no server-rendered content retrievable with current tooling). Yahoo Sports is professionally staffed editorial content, sits one tier below official, and was directly fetchable and directly verifiable.

**Validation performed, not assumed**: The date-window logic derived from this source was run against the independently-sourced Jürisoo match data. Result: exact 72/16/8/4/2/1/1 stage-count match, zero unmatched rows, zero group-assignment mismatches (every group-stage match has both teams landing in the same group under the derived crosswalk).

**Correction applied**: Team-name spellings differ between the two sources ("Turkey" vs. "Türkiye," "Czech Republic" vs. "Czechia," "United States" vs. "USA"). The crosswalk uses the Jürisoo spelling as canonical, since that dataset is the fact-table backbone. Documented so this isn't rediscovered as a mystery bug later.

**Residual risk, not yet closed**: This is still a single non-official source for the group draw. A second independent cross-check was proposed but not yet performed before treating this as load-bearing in a published claim.

---

## 2026-07-28 — Team→group crosswalk extracted into its own committed file

**Decision**: The Yahoo Sports-sourced team→group crosswalk (48 teams → 12
groups) that was implicitly embedded in `wc2026_stage_mapping.csv` is now
also committed on its own as `data/raw/wc2026_group_draw.csv`, and
`src/transform/build_stage_mapping.py` reads it explicitly rather than
having the mapping exist only inside a derived output file.

**Why**: Not a new sourcing decision — same Yahoo Sports data already
logged in the 2026-07-21 entry above, no new risk introduced. This is a
reproducibility fix: the transform script that regenerates
`wc2026_stage_mapping.csv` needs the crosswalk as a real input, not
something reverse-engineered from its own output. It also gives Build 4 a
ready-made seed table for `dim_group`.

**Validation performed**: `tests/test_stage_mapping.py` regenerates the
mapping table from `international_results_full.csv` and this crosswalk and
asserts the result matches the already-committed
`wc2026_stage_mapping.csv` row-for-row (5/5 tests pass).

---

## 2026-07-21 — FIFA.com ruled out for direct ingestion (for now)

**Decision**: Do not build a scraper against fifa.com in the current phase.

**Why**: Two direct fetch attempts (schedule article, live match-centre page) returned only empty HTML shells — confirmed JS-rendered SPA. Separately, FIFA's store subdomain explicitly prohibits automated data collection in its terms; the match-centre-specific terms were not directly located, so the legal picture is incomplete, not resolved in either direction.

**Revisit condition**: If richer per-match stats (shots, possession, xG-adjacent metrics) become necessary to salvage the tactical-efficiency theme, this decision should be revisited with (a) a headless-browser-capable tool and (b) a direct reading of the actual match-centre terms of use — not inferred from a sibling subdomain.
