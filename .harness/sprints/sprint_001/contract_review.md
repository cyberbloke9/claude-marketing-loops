VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Contract Review — Sprint 001 (Measurement Core + Schema-v2 Seam)

### Scope Clarity ✓

The contract is precise and tightly scoped: **pure functions only**, no rendering, no V-check wiring, no check-routing edits. The "Isolation guarantee" (§1.2) is explicit — edits to schema-acceptance frozensets only, no changes to `_FORMAT_BY_ROLE`, `_SAFEZONE_ROLES`, or `run_checks`. This prevents the "shipped-but-untested bug" risk (routing v2 surfaces through v1 checks before V13–V19 exist) and is correctly motivated.

### Exact Signatures & Return Types ✓

All required functions specified:
- `body_reference(elements) -> int` (deterministic fallback to 26)
- `count_dominant(elements) -> int`
- `is_utility_slide(elements) -> bool` (well-defined: empty list → False, content role present → False)
- `dominant_ratio_ok(elements) -> dict` (with explicit keys: `exempt`, `dominant_count`, `body_reference`, `dominant_font_px`, `ratio`, `passes`, `reason`)
- `format_slide_type_min(element_role, font_px) -> dict` (with `minimum` and `passes` keys)
- `thumbnail_ink_ok(role, effective_px) -> dict` (with role, minimum, effective_px, passes keys)
- `thumbnail_scale_band(full_band_px, canvas_w=1080, thumb_w=360) -> float`
- `parse_cover_pattern_block(meta_text) -> dict|None`
- `cover_pattern_valid(parsed) -> bool`
- `one_dataset_present(parsed) -> bool`

Constants pinned: `_V2_TYPE_MINIMUMS` table (8 rows, source cited for each floor), `THUMB_W`/`CANVAS_W`/`THUMB_HEADLINE_MIN_PX`/`THUMB_DOMINANT_MIN_PX`.

### Boundary Testing — Adversarial Matrix ✓

The §8 matrix is comprehensive (26 rows) and each row is isolable and testable:
- **Dominant ratio:** boundary at 3.0 (rows 1–2: 78/26 = 3.0 pass, 77/26 ≈ 2.96 fail); zero/multiple dominants (rows 3–4)
- **Type floors:** rows 9–13 test body 26/25, source 24/23/20, headline 48/47, wordmark exempt, invalid role → ValueError
- **Thumbnail comparator:** rows 14–16 test headline/dominant at exact 13.0/21.0 boundaries, invalid role → ValueError
- **Cover-pattern parser:** rows 18–21 test valid/invalid patterns, missing block → None, validation on None → False
- **Manifest schema:** rows 22–26 test v1 → still accepted, v2 → accepted, v2 with bogus format → PreconditionError, v1 malformed → PreconditionError (unchanged)

**Boundary arithmetic verified:** 39.84 × (1/3) = 13.28 (row 17). Comparators pin exact thresholds (13.0, 21.0) with one-line precision (12.99 → fail), preventing hardcoding shortcuts and false positives.

### Test Coverage & Baseline Stability ✓

- Render suite baseline: 139 tests, must increase post-sprint (new tests added) and remain OK
- Loop suite baseline: 254 tests, must stay 254 and OK (loop suite does not import measure/validate — verified as doc-comment-only)
- Widening invariant explicitly stated: every previously-accepted manifest still validates (rows 22, 25, 26 guard this)

### Non-Goals Explicit ✓

Section 9 clearly delineates what is **not** in scope:
- No rendering, no PNG/PDF
- No V-check wiring (V13–V19 not added to `run_checks`)
- No check-routing edits
- No `font_px → thumbnail pass` predictor (Risk-4 forbidden)
- No mutation of existing measure.py/validate.py symbols
- No acceptance.py change, no fixture change

These boundaries prevent scope creep and undefined test failures.

### Error States & Invalid Input ✓

All error paths specified (§4):
- Empty elements → body_reference returns 26, is_utility_slide returns False, dominant_ratio_ok fails on "no dominant"
- Missing block → parse_cover_pattern_block returns None
- Invalid pattern value (e.g., TIMELINE not in VALID_COVER_PATTERNS) → cover_pattern_valid returns False
- Unknown role (e.g., "banana") → ValueError naming the role
- Malformed manifest with unknown format tag → PreconditionError naming surface + value
- v1 manifest with missing field or non-token color → PreconditionError (unchanged rejection)

### Verification Commands ✓

Section 7 provides four exact shell commands:
1. Render suite count
2. Loop suite count
3. New measurement tests in isolation
4. No-network import sanity check

All are runnable and produce machine-readable pass/fail output.

### Spec Alignment ✓

- Spec §5.2 V13 (dominant ratio): covered by §1.1.A ✓
- Spec §5.2 V14 (raised type floors): covered by §1.1.B ✓
- Spec §5.2 V15 (thumbnail gate): covered by §1.1.C ✓
- Spec §5.4 meta blocks: covered by §1.1.D ✓
- Spec §5.3 manifest schema v2: covered by §1.2 ✓
- Spec §10 Risk 1 (raised floors on v1 surfaces): explicitly resolved — new rules apply **only** to format-slide surfaces, v1 surfaces frozen ✓
- Spec §10 Risk 3 (body_reference denominator): pinned to max body or fallback 26 ✓
- Spec §10 Risk 4 (thumbnail measured pixels, not font_px math): contracted as measured-pixel route (PNG downscale + ink measurement in Sprint 005), this sprint ships comparator only ✓
- Spec §10 Risk 5 (one_dataset presence-only, not semantic): covered by §1.1.D — `one_dataset_present` checks presence, not truth ✓

### One Documented Observation — No Blocker

**Spec §11 (Sprint breakdown) mentions "16/24 thresholds" for thumbnail gates, but Spec §5.2 V15 (normative behavior section) specifies "13px / 21px," and the contract implements 13/21.**

- §5.2 is the authoritative behavior spec; §11 is a summary breakdown
- The contract shows its work: `K_INTER = 0.83`, headline floor 48 → `0.83 × 48 / 3 ≈ 13.3` → floor 13; dominant floor 78 → `0.83 × 78 / 3 ≈ 21.6` → floor 21
- The contract explicitly marks these thresholds **provisional** (§1.1.C: "Because **no v2 render exists yet**, these integers are **provisional pending Sprint-006 real-render revalidation**")
- The binding invariant is the *logic* (threshold boundary test: 13.0 pass, 12.99 fail), not the absolute value — which will be revalidated when real PNGs are rendered
- This is sound — the contract correctly pins the arithmetic *for this sprint* and makes clear it may shift based on Sprint-006 real rendering

This is **documented, resolved-in-favor-of-13/21, and provisioned for change** — not an ambiguity or error.

### Definition of Done ✓

Section 10 lists five verifiable criteria:
1. Named measure.py additions (14 new symbols)
2. validate.py schema-acceptance changes (specific roles, format values, pdf key)
3. Test coverage (full §8 matrix)
4. Test-count validation (N > 139 for render, 254 for loop)
5. Generator trace (baseline, files changed, new-test count, passing run output, disclosed risks)

All are checkable on disk without ambiguity.

### Verdict

This contract is **testable, implementable, and unambiguous**. The scope is tight (pure functions, no rendering), the boundaries are explicit (schema widening only, no check routing), the adversarial matrix is comprehensive (26 rows, each isolable), and the non-goals are clear. The provisional thresholds (13/21) are correctly marked as provisional pending real rendering and will be validated in Sprint 006. The isolation guarantee prevents the "shipped-but-untested" regression risk. No vagueness, no hidden scope, no gameable criteria.

**ACCEPT.**
