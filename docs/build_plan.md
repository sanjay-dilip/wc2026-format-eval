# Build Plan — 2026 World Cup Format Evaluation

Status as of this writing: Build 0 in progress. No Snowflake object exists yet.
No GitHub repo pushed yet (instructions given, execution pending, per last session).

**Sequencing note, stated once here rather than per-build**: primary Snowflake
account credits expire soon. Builds 2–4 (ingestion, validation, core model) are
prioritized ahead of their "natural" position in a purely logical dependency
order, because they're the paid-account-dependent work. This means some schema
decisions in Build 1 will be made before every metric is fully defined — a
deliberate exception to "don't finalize schema before data is understood,"
made explicitly so it isn't rediscovered as an accident later.

---

## Build 0 — Repo & Feasibility Scaffolding

**Goal**: A real, committed, public repo exists with the feasibility-phase
findings already produced, not stranded in chat.

**Work**:
- `.gitignore`, `.gitattributes`, `LICENSE` (MIT), `CONTEXT.md` stub
- Two commits: scaffold, then feasibility docs + validated stage/group mapping
- GitHub repo created empty, remote added, pushed
- `data_feasibility_report.md`, `decision_log.md` — in place
- `wc2026_stage_mapping.csv` — in place, validated (72/16/8/4/2/1/1, zero mismatches)

**Open blockers carried in from feasibility phase, not yet closed**:
- FIFA rankings sourcing — untouched
- Group draw — single-source (Yahoo Sports); second independent cross-check not yet done
- Venue lat/long — not yet independently re-verified (currently only seen in the unlicensed repo)
- Tactical efficiency theme — no free 2026 event-data source found; go/no-go not yet decided
- `src/transform/build_stage_mapping.py` + `tests/test_stage_mapping.py` — the actual transformation logic still only exists as ad hoc commands in a chat session, not as reproducible, testable code. This is a real gap, not a formality — closing it is what makes the stage-mapping CSV's correctness checkable by someone other than the person who ran the original commands.

**Success criteria**: `git log` shows real history; repo is public and clonable; nothing above is hidden, all four blockers appear in `CONTEXT.md`.

---

## Build 1 — Problem Statement Lock + Architecture Definition

**Goal**: Falsifiable problem statement finalized. Schema *shape* decided (names, grain, dimension list) — not yet implemented in Snowflake.

**Work**:
- Revise the provisional problem statement using what feasibility actually found (in particular: tactical efficiency likely drops or shrinks; rankings still unresolved)
- Lock schema names: `RAW`, `VALIDATION`, `CORE`, `ANALYTICS`, `AUDIT` (drop `SHARED` unless Build 9 cross-account sharing is confirmed worth doing)
- Draft dimensional model: `dim_team`, `dim_group`, `dim_stage`, `dim_venue`, `dim_confederation`, `dim_date`, `fact_match` (grain: one row per match)
- For every candidate Snowflake feature on the original list, apply the 5-question test (what problem, why not simpler, what it costs, how demonstrated, how tested) and cut anything that fails it — this is where "resume-keyword" features get killed on paper before they get built

**Depends on**: Build 0 complete.

**Success criteria**: Schema diagram (even ASCII) committed to `docs/architecture.md`; problem statement committed; every kept Snowflake feature has a written justification, every cut feature has a one-line reason it was cut.

---

## Build 2 — Raw Ingestion (Snowflake, primary account)

**Goal**: Match data physically inside Snowflake's RAW schema, not just sitting in CSVs.

**Work**:
- Internal stage + file format + `COPY INTO` for the 104-row 2026 subset and `shootouts_full.csv`
- `src/ingestion/` scripts, using `config.py` for all paths — no hardcoded filenames
- X-Small warehouse, auto-suspend/auto-resume on from the first `CREATE WAREHOUSE`
- Audit table logging: rows loaded, warehouse used, duration, credits

**Depends on**: Build 1 schema names locked.

**Success criteria**: `RAW.MATCH` row count == 104, exactly. Audit log entry exists for the load. Warehouse auto-suspended, confirmed via query history, not assumed.

---

## Build 3 — Validation Layer

**Goal**: Every check that was run ad hoc in chat becomes a real, re-runnable SQL or Python check that fails loudly.

**Work**:
- Port the duplicate-join-key check, the group-crosswalk mismatch check, and the 72/16/8/4/2/1/1 stage-count check into `VALIDATION` schema SQL + `tests/test_stage_mapping.py`
- Add the checks not yet built: missing teams, invalid scores, impossible dates, missing venue coordinates, source-to-warehouse count reconciliation
- Rejected-records table — nothing gets silently dropped
- Deliberately inject one bad row in a test fixture and confirm the pipeline actually fails, not just that it theoretically would

**Depends on**: Build 2 (something has to exist to validate).

**Success criteria**: Data quality summary table exists and is queryable. The deliberate-bad-row test fails as expected, then passes once the row is fixed — proving the check does something, not just that it exists.

---

## Build 4 — Core Dimensional Model

**Goal**: `CORE` schema populated, `fact_match` joined cleanly to every dimension.

**Work**:
- Build dimension tables from the validated stage/group mapping (Build 0's CSV becomes a seed table here, loaded through the same COPY INTO pattern, not hand-typed into Snowflake)
- `fact_match` at match grain, FK to every dimension
- Zero-copy clone of `CORE` before any risky transformation, if the cost/benefit still holds by this point — revisit the Build 1 justification, don't assume it

**Depends on**: Build 3 (don't build a dimensional model on unvalidated data).

**Success criteria**: `fact_match` row count still 104. No orphaned foreign keys — checked with an actual query, not assumed from the Build 0 validation (Snowflake load could introduce new issues; re-verify in place).

---

## Build 5 — Historical Comparison Layer

**Goal**: 2026 metrics have something to be compared against.

**Work**:
- Fetch script (not a committed static blob) pulling the full historical Jürisoo dataset when needed
- Standardize team/confederation names across eras (32-team, 24-team, 48-team formats)
- Explicit handling for format differences (documented, not glossed over) per the spec's Historical Comparison rules

**Depends on**: Build 4.

**Success criteria**: At least 2–3 prior World Cups computed alongside 2026 on the same metric definitions, with format differences called out in the same place the numbers are shown.

---

## Build 6 — Rankings Resolution + Analytical Marts

**Goal**: Close the rankings gap; build the marts that actually need it.

**Work**:
- Resolve FIFA rankings sourcing — this has been an open blocker since it was first flagged and needs to actually get worked, not just carried forward again
- `ANALYTICS` schema marts: competitive balance, group difficulty, upset rate, confederation performance, expected-vs-actual
- Statistical validation per spec: state hypothesis, check assumptions, report effect size and practical significance, use "associated with" / "consistent with" language, never causal claims

**Depends on**: Build 5 (needs historical baseline) and rankings resolution specifically.

**Success criteria**: Every metric has a written definition (business meaning, formula, grain, null handling, ET/shootout handling, historical comparability). Every statistical claim has an effect size attached, not just a p-value.

---

## Build 7 — Geospatial / Travel (conditional)

**Goal**: Decide, then build only if justified.

**Work**:
- Independently re-verify venue coordinates (public facts — don't inherit them from the unlicensed repo)
- Distance-between-consecutive-venues logic, not home-country-every-time
- Rest-day definitions, time zone handling documented before any calculation runs

**Depends on**: Build 4. Explicitly gated — decide whether this theme survives before writing any code, per the spec's own "optional until feasibility confirmed" instruction.

**Success criteria**: Either a working, caveated travel/rest mart, or a documented decision to cut the theme — both are valid outcomes; silence is not.

---

## Build 8 — Incremental Pipeline Demonstration

**Goal**: Prove incremental load equals full rebuild.

**Work**:
- Simulate initial load, new-match arrival, a correction, idempotent reruns
- Automated comparison: incremental result vs. full-refresh result, byte- or hash-identical

**Depends on**: Build 4 minimum; more convincing after Build 6 exists (more to compare).

**Success criteria**: The automated comparison passes and is itself a committed test, not a one-time manual check.

---

## Build 9 — Cross-Account Sharing (conditional)

**Goal**: Demonstrate producer/consumer separation, only if it earns its complexity.

**Work**:
- Confirm both account regions and sharing compatibility before building anything
- Secure Data Share from primary → secondary account
- Verify from the consumer side that RAW is genuinely inaccessible, not just assumed hidden

**Depends on**: Build 4. Explicitly conditional — the spec says don't force this if it doesn't add enough portfolio value; make that call in writing before starting, not after building it and rationalizing it.

**Success criteria**: Consumer account runs BI-shaped queries against the share; a direct attempt to query RAW from the consumer account fails, confirmed by actually trying it.

---

## Build 10 — Power BI Layer

**Goal**: Presentation layer, built last, on stable ground.

**Work**:
- `.pbip` format from the start, for git diffability (established two turns ago)
- Report pages only for themes that survived Builds 6–7 — no page gets built just because it was on the original candidate list
- Every visual: a defined metric, a reason to exist, a caveat where the metric needs one

**Depends on**: Builds 6 (and 7/9 if kept) stable and tested. Explicit gate: don't start dashboard design before metrics and dimensional model are settled.

**Success criteria**: Every PBI measure reconciles against the Snowflake SQL output it's supposed to represent — checked directly, not assumed from matching row counts.

---

## Build C — Consolidation

**Goal**: Everything the spec requires before "Complete" is a legitimate word.

**Work**: `CONSOLIDATION_PROTOCOL.md` steps 1–9 — structure by domain, duplication extracted, deps pinned/split, cold-clone test actually run in a fresh environment, every README claim traced to a committed artifact, decay/limitations listed, surface trimmed, tree clean, tagged `v1.0`.
- Cost report, limitations doc, demo script, final polished README (only now — not before)

**Success criteria**: A stranger can clone the repo, follow the README, and reproduce the headline claim from committed artifacts alone — no credential, no memory of this conversation, no trust required.

---

## Cross-cutting, every build

- **Git**: every session ends committed and pushed, not just committed. Push cadence is what the streak actually depends on, not commit cadence.
- **Cost**: warehouse size, query duration, credits, rows processed, refresh duration — recorded at every build that touches the primary account, not retrofitted at the end.
- **Documentation**: any research-only day still produces a decision-log or feasibility-report entry — this is the same mechanism that turned this session's chat exploration into real committed files, applied consistently rather than as a one-off.
