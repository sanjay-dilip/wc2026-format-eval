# Decision Log — 2026 World Cup Format Evaluation

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
