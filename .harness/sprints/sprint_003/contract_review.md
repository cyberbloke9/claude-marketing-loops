VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Contract Review: Sprint 003 — Format Templates Batch B

### Scope and Completeness
The contract specifies **four new format-slide templates (TIMELINE, VS-CONTRAST, LEADERBOARD, CHART)** rendered to **1080×1350** with raised v2 type floors, one dominant element per slide at ≥3× body_reference, and exact required-role counts per format. All new work is **additive** — no changes to v1 code paths, batch-A constants, or the frozen 139+254 test baseline.

### Verification of Load-Bearing Premises

**Code premise 1: `measure.dominant_ratio_ok` fallback**  
✓ Verified (measure.py:277, 285-297): `_BODY_REFERENCE_FALLBACK = 26` is defined, and `body_reference(elements)` returns it when no `body`-role elements exist. CHART (which has only `chart-label` role, not `body`) correctly falls back to 26, yielding 132/26 = 5.08 ≥ 3. The ratio table in §1.3 of the contract is mathematically proven.

**Code premise 2: `measure.format_slide_type_min` knows `chart-label`**  
✓ Verified (measure.py:395-420): `_V2_TYPE_MINIMUMS` already includes `"chart-label": 26,` with an associated function that handles it. The contract's assertion "already exists" is correct.

**Code premise 3: `render.py` batch-A infrastructure ready to extend**  
✓ Verified (render.py:610-657, 641-712): `_FMT_DIRECTIVE_MAP`, `_V2_BATCH_A_FORMATS`, all v2 style constants, `_FMT_DIRECTIVE_RE`, and `parse_formats` are in place. Line 623 comment explicitly anticipates batch-B: "TIMELINE/VS-CONTRAST/LEADERBOARD/CHART are Sprint 003 and are rejected fail-loud." The function signatures and infrastructure are ready for the three new directives (`Event:`, `Row:`, `Bar:`) and four new format tags.

### Specification Clarity and Testability

**Grammar and fail-loud behavior:**  
- §1.1 format tags table: all seven tags listed with clear per-format directive requirements  
- §1.1 new directives table: `Event:`, `Row:`, `Bar:` with exact role/style/rendered-as descriptions  
- §1.2 per-format required-role rules: exact minimums with fail-loud `ValueError` on every violation  
- §4 error states: every fail-loud case specified with exit code and expected exception  

All unambiguous.

**Ratio invariant (§1.3):**  
Mathematically proven table shows all four formats meet ≥3 dominant ratio. CHART's no-body fallback to 26 is the load-bearing assumption, now verified in code. `chart-label` is explicitly NOT a body role (so it never enters `body_reference`), preventing confusion.

**Decorative vs. manifest elements (§1.4):**  
Explicit per format:
- TIMELINE: chip borders/fills are decorative; only chip TEXT is a `body` element  
- VS-CONTRAST: asymmetry is documented; exactly one dominant (132) + one headline (52), both in manifest  
- LEADERBOARD: "accent on one row" = dominant only; other rows render ink-muted  
- CHART: bars are `--chart-up` decorative rectangles (zero-based, proportional); direct `chart-label` text elements are in the manifest; bars are NOT

Matrix row 4 and row 14 (adversarial) confirm these expectations are testable.

**Conscious regression change (§0, §10.6):**  
Explicitly scoped: `test_unknown_format_tag_fail_loud` re-pointed from TIMELINE (now valid) to PIE-CHART (genuinely bogus, still fails). One new positive assertion added. "Unknown tag fails loud" guarantee is preserved and re-proven. No other assertion weakened. This is a conscious extension, not a silent deletion.

**Verification commands (§7):**  
Eight bash command blocks (a–i) are copy-paste ready:
- (a) Render batch-B fixtures twice (determinism setup)
- (b) Canvas 1080×1350, schema "2", correct format tags, `has_axis:false`  
- (c) Decoded-RGBA SHA + manifest byte identity  
- (d) V13/V14 ratio and floor checks via Sprint-001 measure functions  
- (e) Confirm bars are decorative, not manifest elements  
- (f) validate.py exit-2 behavior on v2 assets  
- (g) Regression: hyd + tgrera byte-identical  
- (h) Test suite: render count > 219, loop count = 254  
- (i) Import sanity with network off

All are specific, unambiguous, and executable.

**Adversarial matrix (§8):**  
29 rows, each with a discrete attack and expected result:
- Rows 1–4: happy paths (TIMELINE, VS-CONTRAST, LEADERBOARD, CHART render)  
- Rows 5–9: measurement and schema checks  
- Rows 10–18: fail-loud cases (each one a ValueError with specific naming)  
- Rows 19–20: conscious test re-point (PIE-CHART fails, TIMELINE now renders)  
- Rows 21–23: validation behavior and regression  
- Rows 24–28: design invariants (token colors, decorative bars, visual inspection)  
- Row 29: test suite counts

Each row is independently testable and together cover the contract's surface.

**Definition of done (§10):**  
10 testable conditions + trace requirements. All observable on disk or via bash commands.

### Non-Goals and Scope Boundaries (§9)
- No PDF (Sprint 004)  
- No V13–V19 QA check wiring (Sprint 005)  
- No `has_axis:true` / plotted numeric axis on CHART  
- No `measure.py` changes (frozen; only calls existing functions)  
- No `validate.py` changes (schema + F-001 guard already cover batch-B)  
- No `acceptance.py` changes  
- No v1 renderer edits  
- No batch-A constant edits  

All explicitly stated and scoped tight.

### Risk and Ambiguity Assessment

**Very low risk:**  
- Contract does not require exact test count, only ">219" (strictly greater than baseline). This is intentional — as long as new tests are added for batch-B behavior, the count will rise. The §7 and §8 verification commands test behavior independently of count.  
- Bar-length rounding formula (§1.1) specifies `round(value / max_value * track_w)` with comment "deterministic integer math." The formula is clear (float division, then round); implementation is deterministic.  
- VS-CONTRAST asymmetry (§1.4) is documented visually ("132 vs 52 IS the design") and testable mechanically (exactly one `dominant` role, confirmed in row 7 of matrix).

**No blocking ambiguities:**  
- All directives, roles, and format tags are named exactly.  
- All per-format required minimums are specified as exact integers.  
- All fail-loud conditions are fail-loud (no partial writes, no silent fallbacks).  
- All deterministic behavior is stated with locked constants and integer math.  
- No gameable criteria: the §7 commands and §8 matrix are direct measurements or manifest structure checks, not subjective judgments.

### Summary
The contract is **well-formed, complete, and testable**. All three load-bearing code premises are verified. The spec is clear, the commands are copy-paste ready, the adversarial matrix covers all cases, and the regression budget is explicit. The conscious test re-point is documented and does not weaken the "unknown tag fails loud" guarantee. No blocking deficiencies.

**ACCEPT** — ready for implementation.
