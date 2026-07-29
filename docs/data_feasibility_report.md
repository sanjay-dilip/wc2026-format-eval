# Data Feasibility Report — 2026 World Cup Format Evaluation

Status: Phase 1 (partial). Covers match-result, stage/group, and event-data sourcing.
Not yet covered: FIFA rankings, venue geospatial independent verification, travel/rest inputs.
Compiled: July 21, 2026.

---

## Source 1: International football results (martj42/international_results)

- **Candidate source**: `martj42/international_results` (GitHub, mirrored on Kaggle)
- **Source owner**: Mart Jürisoo (individual maintainer), aggregated from Wikipedia, rsssf.com, and national federation sites
- **Access method**: Public GitHub repo, flat CSV files (`results.csv`, `shootouts.csv`, `goalscorers.csv`, `former_names.csv`), fetched directly via `raw.githubusercontent.com`
- **Data grain**: One row per international match
- **Time coverage**: 1872–2026-07-19. Verified: contains exactly 104 rows tagged `tournament = "FIFA World Cup"` with `date >= 2026-06-11`, including the July 19 final (Spain 1–0 Argentina), matching the confirmed official match count
- **Important fields**: date, home_team, away_team, home_score, away_score (FT+ET, excludes shootouts — documented in README), tournament, city, country, neutral flag. Separate `shootouts.csv` gives shootout winner/first-shooter.
- **Missing fields**: No match-stage/round label, no lineups, no event-level data, no venue coordinates
- **Reliability level**: High for this grain. Actively maintained since ~2017, correction process via GitHub pull requests, 141k+ downloads, no synthetic-data red flags found on inspection
- **Licensing notes**: **CC0 1.0 Universal** (public domain dedication) — confirmed by reading the repo's LICENSE file directly. No attribution required, no reuse restriction.
- **Expected ingestion method**: Direct CSV pull into RAW schema; low complexity
- **Known limitations**: No stage/round field (addressed separately — see Source 4); team name spellings sometimes diverge from other sources (confirmed: "Turkey" not "Türkiye," "Czech Republic" not "Czechia," "United States" not "USA" — see Decision Log)
- **Recommended use**: **Primary backbone for the Match fact table and for historical cross-tournament comparison.**

---

## Source 2: StatsBomb Open Data

- **Candidate source**: `statsbomb/open-data` (GitHub)
- **Source owner**: StatsBomb (commercial sports-analytics vendor), free tier
- **Access method**: Public GitHub repo, JSON files
- **Data grain**: Would be event-level (passes, shots, xG, freeze frames) per match, if available
- **Time coverage confirmed by direct inspection of `competitions.json`**: Men's FIFA World Cup entries exist for 2022, 2018, 1990, 1986, 1974, 1970, 1962, 1958. **No 2026 entry exists as of today's check.**
- **Important fields**: N/A — not available for this tournament
- **Missing fields**: Everything, for 2026 specifically
- **Reliability level**: High in general (industry-standard provider) — irrelevant here since coverage doesn't extend to this tournament
- **Licensing notes**: Free but conditional — requires registration and StatsBomb attribution on publication, not public domain
- **Expected ingestion method**: N/A
- **Known limitations**: **Confirmed dead end for 2026.** No free event-level dataset for this tournament was found anywhere in this pass.
- **Recommended use**: **None for this project as scoped.** Directly impacts the "tactical efficiency" theme — recommend downgrading that theme to whatever aggregate box-score stats are publicly reported (shots, possession) rather than raw event data, or dropping it.

---

## Source 3: mominullptr/FIFA-World-Cup-2026-Dataset

- **Candidate source**: `FIFA-World-Cup-2026-Dataset` (GitHub, also mirrored on Kaggle and Hugging Face)
- **Source owner**: Individual contributor ("mominullptr"); self-marketed with SEO copy explicitly targeting AI search/voice-crawl discovery
- **Access method**: Public GitHub repo, CSV + SQLite
- **Data grain**: Match, team, player, venue, stage, referee
- **Time coverage**: Claims full tournament; confirmed 104/104 matches present
- **Important fields**: `tournament_stages.csv` (useful stage taxonomy design), `venues.csv` (lat/long/elevation/capacity for all 16 venues), `teams.csv` (pre-tournament FIFA ranking + Elo per team, group letter)
- **Missing/unreliable fields**: **Confirmed by reading `generate_dataset.py` directly**: player `market_value` is fabricated via `random.seed(player_id); random.uniform(0.4, 1.6) * base_val` for any player not manually curated. Match-level `home_xg`/`away_xg` values are hardcoded directly in the generation script with no visible source citation. This contradicts the dataset's own claim of "zero synthetic data."
- **Reliability level**: **Low for numeric/statistical fields. Structural scaffolding (stage IDs, venue geography) is plausible but independently re-verified before use, not trusted from this repo alone.**
- **Licensing notes**: **No LICENSE file present in the repo (confirmed — 404 on direct request).** Default all-rights-reserved copyright applies. Real legal exposure if reused in a public portfolio without contacting the author.
- **Expected ingestion method**: Not recommended as an ingestion source. Reference only, for schema-design ideas.
- **Known limitations**: Marketing claims do not match source code behavior. Do not cite as a data source of record for any numeric claim.
- **Recommended use**: **Schema/structure reference only.** Do not ingest as a system of record. Venue coordinates should be re-derived independently (public facts, easily re-sourced) rather than copied from here.

---

## Source 4: Yahoo Sports — group draw and round schedule

- **Candidate source**: "2026 World Cup results, standings and schedule" article, sports.yahoo.com
- **Source owner**: Yahoo Sports (professional editorial staff, byline: Sean Leahy)
- **Access method**: Direct page fetch (server-rendered, unlike fifa.com — see limitations below)
- **Data grain**: Group draw (12 groups × 4 teams), round-by-round date windows, venue-by-round schedule
- **Time coverage**: Full tournament, draw fixed since December 2025, schedule fixed by venue contracts — not expected to change retroactively
- **Important fields**: Group letter per team (all 48 confirmed), start/end date per round (Group Stage, R32, R16, QF, SF, 3rd Place, Final)
- **Missing fields**: N/A for this specific use
- **Reliability level**: **Tier 5 per project research-rules hierarchy ("reputable sports-data provider") — not official, but above community/wiki sources.** Cross-validated: date-window logic applied to this source's boundaries, run against the independently-sourced Jürisoo match data, reproduced the exact expected 72/16/8/4/2/1/1 stage-count split with zero unmatched rows and zero group-assignment mismatches.
- **Licensing notes**: Standard news-article copyright; used here for factual/structural data only (dates, groupings), not reproduced text, consistent with project copyright handling
- **Expected ingestion method**: Manually transcribed into a seed/reference table (`wc2026_stage_mapping.csv`), not scraped programmatically — this was a one-time historical reconstruction, not a live feed
- **Known limitations**: Not an official FIFA source — must be labeled as such in any published documentation, not presented as authoritative. The same article also contains an internal inconsistency (uses both "Cape Verde" and "Cabo Verde" in different sections) — a reminder that even reliable secondary sources need cross-checking, not blind trust.
- **Recommended use**: **Source of record for the Tournament Stage and Group dimensions**, pending the option of a second independent cross-check before this becomes load-bearing in a published claim.

---

## Source 5: FIFA.com (official)

- **Candidate source**: fifa.com match centre and schedule pages
- **Source owner**: FIFA (official)
- **Access method**: **Attempted directly, twice — both the schedule article and a live match-centre page returned only empty HTML meta tags. Confirmed: fifa.com is a fully JS-rendered single-page application; no server-rendered content is retrievable without a headless browser.**
- **Reliability level**: Would be highest possible (official) if accessible
- **Licensing notes**: Not fully resolved. FIFA's store subdomain explicitly prohibits "spiders, robots, data mining techniques" in its terms; the match-centre-specific terms were not directly located. Treat automated collection from fifa.com as a live legal risk, not a resolved shortcut, if revisited later.
- **Known limitations**: Not currently accessible with available tooling.
- **Recommended use**: **Not usable in current form.** Would require a headless-browser tool and a separate ToS review before any scraping is attempted.

---

## Open gap: FIFA World Ranking (pre-tournament)

Not resolved in this pass. No clean official bulk export exists; community GitHub scrapers found in an earlier search round were confirmed stale (capped at September 2024 or earlier). This blocks any metric requiring a ranking baseline — group difficulty, upset rate, ranking-adjusted performance, expected-vs-actual performance. **Flagged as the next open dependency, not yet started.**
