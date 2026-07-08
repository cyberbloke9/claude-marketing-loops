VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Rationale

Sprint 002 contract is **clear, testable, and grounded in Sprint 001's delivered state**. All critical dependencies verified on disk:

- ✓ `measure.dominant_ratio_ok(els)` exists with correct signature: returns dict with `{exempt, dominant_count, body_reference, dominant_font_px, ratio, passes, reason}`
- ✓ `measure.format_slide_type_min(role, font_px)` exists with correct signature: returns dict with `{minimum, passes}`
- ✓ `PreconditionError` defined in validate.py; main() maps it to exit code 2
- ✓ Git repo exists (enables §7f freeze verification via `git status`)
- ✓ Baseline confirmed in generator_trace.log: "render Ran 182 tests ... OK" (Sprint 001 completed)

## Scope is Sharp

**In scope:** Three batch-A format templates (BIG-NUMBER, RECEIPTS, CHECKLIST) at 1080×1350 with one dominant element each (132px, ratio 4.4 ≥ 3×body), raised type floors, on-card wordmark, schema_version "2" manifest emission, deterministic re-render (decoded-RGBA PNG equality + manifest byte-equality), formats.md input grammar (Risk 7), fail-loud on invalid input (no partial writes), v1 path byte-frozen (schema "2" iff format-slide surface exists).

**Explicitly out of scope:** PDF emission (Sprint 004), V13–V19 check wiring (Sprint 005), batch-B formats (Sprint 003), acceptance.py/fixtures changes (Sprint 006), measure.py additions (Sprint 001 frozen), v1 renderer edits.

**F-001 discharge:** Contract adds minimal, additive exit-2 guard in validate.py (after schema check, before run_checks). If any surface has role="format-slide", raise PreconditionError with cited message → exit 2, no traceback. Guard cannot fire on v1 fixtures or hyd/tgrera. Superseded by Sprint 005 V13–V19 wiring. Pre-authorized by Sprint 001 findings.

## Exact Behaviors are Testable

- **§1–§2:** User-visible inputs (formats.md directives), outputs (format-NN.png, manifest.json), file locations are pinned.
- **§1.3:** Type sizes locked (dominant 132, headline 52, body 30, source-stamp 26, wordmark 26); ratio provable (132/30 = 4.4 ≥ 3).
- **§1.4–§1.5:** Per-format rules (1 dominant, exact wordmark, 2–4 chips, ≥2 steps, ≤10 slides) enforced fail-loud.
- **§1.6:** schema_version "2" emission rule (iff ≥1 format-slide surface) is unambiguous and testable via manifest inspection.
- **§3:** Determinism — decoded-RGBA SHA of PNG + byte-equality of manifest across runs; fonts vendored only, zero network.
- **§4:** Error states fully specified (missing folder, no renderable input, invalid format tag, 0/≥2 dominants, missing wordmark, chip count ∉[2,4], ≥11 slides, band overflow, tofu glyph, validate on v2 → clean exit 2).
- **§7:** Eight concrete command blocks (render, canvas+schema, determinism, measure, validate guard, regression, suites, import). Each is runnable and produces observable evidence.
- **§8:** Twenty-three adversarial rows covering success, every fail-loud path, measure predicates, wordmark count, regression (v1 byte-frozen), token compliance, determinism, suite counts. One-fixture-one-check discipline enabled.

## No Vague, Untestable, or Gameable Requirements

- Type sizes are exact integers, not ranges or "should be".
- Pass/fail conditions are binary (1080×1350 or not; 1 dominant or not; ≤10 slides or not).
- Determinism is falsifiable (hash comparison, not "seems similar").
- Manifest schema is validated via _validate_manifest_schema + measure.* predicates (provable).
- v1 freeze is verified via git (no silent byte changes).

## Minor Notes (Non-Blocking)

1. **Manifest bbox accuracy not tested in §7 commands.** Contract specifies bboxes in manifest (§1.6) but doesn't verify they correspond to rendered pixel positions. Correct by design — V15 pixel-truth (rendered ink measurement) is Sprint 005. Evaluator can post-hoc measure rendered ink against manifest font_px for consistency guidance (not a gate). Noted for EVALUATE phase.

2. **"Real glyph" / "tofu guard" terminology.** §8 row 21 references anti-tofu guard; spec links to v1's `_assert_glyphs`. Not re-explained in contract, but context is sufficient (glyph validation is stable v1 code).

3. **Determinism byte-order implicit.** Contract says "decoded-RGBA SHA-256" and §7c uses PIL's `Image.convert("RGBA").tobytes()`. Byte order is deterministic by PIL construction; not explicitly stated, but sufficient.

4. **"Content band" and visual positioning vague.** Contract describes BIG-NUMBER as "vertical stack centered in the content band" (§1.4) without pixel coordinates. Correct by design — layout is the Generator's to choose deterministically; the manifest specifies exact bboxes (measurable), and §8 row 4 asserts ratio via manifest elements (not visual inspection). Implementation detail deferred appropriately.

5. **Minimum slides not specified.** R14 says ≤10, but is ≥1 required? Contract doesn't say. Reasonable omission: a 0-slide asset would fail R19 (must have ≥1 surface) implicitly, and render_asset would raise before write. Not gameable.

## Regression Baseline Confirmed

- render suite: 182 tests (Sprint 001); Sprint 002 must deliver >182 (new tests added).
- loop suite: 254 tests (unchanged, doesn't import render/validate/measure).
- v1 fixtures (12) + hyd + tgrera must stay byte-identical (schema "1", manifest bytes, PNG RGBA).

## Conclusion

This contract is **ready to execute**. The scope is precisely bounded, all external dependencies are met, all behaviors are testable via concrete commands, and the v1 regression gate is verifiable. The F-001 forward-carry (exit-2 guard) is well-motivated, pre-authorized, and minimal. No vague, untestable, or gameable requirements exist.

**Acceptance recommended.**
