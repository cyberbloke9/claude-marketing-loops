VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

Sprint 004 contract is clear, testable, and bounded. The validator CLI is fully specified with:

- **Exact exit codes:** 0 (PASS), 1 (FAIL), 2 (error).
- **Per-check method, predicate, and rule:** V2–V12 each state applicability, measurement method, FAIL condition, and rule citation. Skipped checks are recorded, not silently dropped.
- **Pixel-measured anti-stub core:** V3 (ink-present), V5 glyph cross-check, and V2 (canvas dims) all read real PNG bytes. A correct manifest over a blank PNG must FAIL.
- **Reproducible positive control:** `fx-good-min` fixture must PASS; all violation fixtures must FAIL on their specific check with rule cited.
- **Exact output schemas:** `qa-verdict.json` (§5.4), `meta.md` verdict block (§5.3). Both are specified verbatim.
- **Deterministic CLI:** `--checked-on` flag fixes verdict date; tests can assert reproducibility.
- **Clear seam contract:** Reuses `measure.py` functions (`contrast_check`, `type_min_ok`, `size_consistent`, `safe_zone_ok`, `parse_blacklist`, `scan_blacklist`). All six functions exist with correct signatures.
- **Scope honesty:** Distinguishes S004 (validator + fail-path fixtures) from S005 (adversarial content asset folders, README wiring, `/loop-qa` update). Does not overreach.

## Verification Path

The acceptance commands (§9) are directly executable:

1. `python3 -m unittest discover -s tools/marketing-render/tests -v` — validate S001/002/003 no regression; new V2–V12 tests present.
2. `python3 tools/marketing-render/validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on 2026-07-04` → exit 0, VERDICT: PASS.
3. Run each fixture fixture (fx-blank-png, fx-low-contrast, fx-size-lie, etc.) — each FAILs on its named check with rule cited.
4. Idempotency check: run validator twice, `meta.md` has exactly one verdict block.

## Notes for Generator Implementation

**Calibration discovery pattern (intentional, not a defect):**

- **V3 ink thresholds (INK_TOL, INK_MIN_PX):** Determined empirically by measuring real TGRERA elements. The contract specifies the acceptance bar (§8.2): "real TGRERA elements clear `INK_MIN_PX` with margin; blank PNG = 0 ink → FAIL." Record measured values + thresholds in trace.
- **V5 glyph constants (K_INTER, GAP):** Similarly determined from real TGRERA render. The discrimination targets are explicit (§8.5): 2×-lie → FAIL, real TGRERA → PASS, 0.5×-lie → FAIL. This bounds the constant on both sides.

These are engineering discipline, not vagueness. Do not hardcode thresholds before seeing the render. Measure real TGRERA, pick thresholds that satisfy the bounds, record findings.

**Date format for V8 (for S005 planning only):**

This sprint validates only TGRERA, which uses `...2026-06-22 / 27 / 30` (pure ISO). The regex `\b\d{4}-\d{2}-\d{2}\b` passes. The contract notes (Risk R-C, §12) this is "presence-based, not a date parser"; S005 fixtures will exercise wider date formats if needed. No S004 test is blocked.

**Provenance key value whitespace (for implementation clarity):**

The contract requires "non-empty value" for `sources:`, `terrem_db_numbers:`, `as_of:`. Recommend: strip each value before checking length (`len(value.strip()) > 0`). TGRERA block has real values; no edge case is tested S004.

**Vendor deliverables:**

- `tools/marketing-render/validate.py` — the CLI (required).
- `tools/marketing-render/tests/test_validate.py` — fail-path unit tests (required).
- `tools/marketing-render/fixtures/` — reproducible fixtures + `make_fixtures.py` generator (required; see §7).
- `brand/qa-checklist.md` — one-line Typography fix "IBM Plex Sans 600" → "Inter 600" (required; Risk 1).
- `content/2026-07-03-tgrera-enforcement-wave/meta.md` — add provenance block if missing (required; §4.11).

No modifications to `measure.py`, `render.py`, `test_render.py`, `test_chart_card.py`, or files outside this repo.

## Contract Clarity Assessment

All contract ambiguities this sprint actually tests are either bounded (calibration discovery) or deferred to S005 (carousel source-slide designation, exotic date formats). The TGRERA end-to-end path is unambiguous.

**One forward-facing note (S005):** V8 requires "every carousel source slide" to carry a source-stamp, but the §5.3 manifest schema has no field marking which slide is the source slide. For S004, TGRERA is chart-card-only, so this branch is not exercised. For S005, the carousel fixtures will need a design for marking the source slide in the manifest (e.g., a `is_source_slide: true` flag in the surface object, or designation in the spec YAML). Not a blocker for S004.
