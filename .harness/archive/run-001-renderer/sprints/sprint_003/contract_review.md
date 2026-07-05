VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

Sprint 003 contract is **comprehensive, unambiguous, and testable**. It specifies a headless CLI chart-card renderer with deterministic output, non-regression checks, and a detailed attack script. All requirements are verifiable via code and test output.

---

## Strengths

1. **Grammar is explicit** (§3.3): Exact regex patterns for each directive (`^Surface:\s*chart-card\s*$`, etc.), roles pinned to font sizes/weights/colors.

2. **Complete test coverage** (§8):
   - Unit tests (existing + new)
   - TGRERA render + output verification
   - Determinism via SHA-256 (decoded-RGBA for PNGs, raw bytes for JSON)
   - Non-regression of hyd carousel (must remain 8 surfaces, no chart card)
   - Import purity check

3. **Attack script** (§9) is detailed and adversarial:
   - Schema version, slug, surface ID/role
   - Real pixel dims from PNG bytes (1080×1920)
   - Background token dominance (1900/2000 samples)
   - All element colors are brand tokens
   - Type minimums via `measure` module (headline ≥36px, body ≥24px for chart-card)
   - Safe-zone containment (y ∈ [250,1480] for critical roles)
   - Anti-stub ink presence (pixel sampling inside bbox)
   - Source-stamp content (must contain "Source" + "as of" + date)
   - Wordmark exact string "TERREM", accent-deep color, right-anchored (x+w=990)
   - Exact copy match: 6 elements in file order

4. **Non-goals clarity** (§11): Explicitly defers plotted-axis engine (has_axis:true rejected fail-loud), validator, and TGRERA carousel — keeping scope tight.

5. **Determinism specification** (§5.7, §8 cmd 2): Byte-deterministic JSON via `json.dumps(…, ensure_ascii=False, indent=2, sort_keys=True)` + trailing newline. No timestamps, no run-varying metadata.

6. **Fail-loud states** (§3.5, §6): Unparseable spec, has_axis:true, bad Canvas, missing required elements → specific ValueErrors. Missing glyph (tofu) → RuntimeError. Stack overflow → error. No silent drops or partial output.

7. **Atomicity** (§5.7): All surfaces rendered in memory; written only after success; on error, nothing partial is written.

8. **Layout is invariant-based** (§5.3, §5.6): Does NOT hard-code bbox pixel coordinates; verifies by invariant (safe-zone, ink-present, exact copy). Allows layout freedom while closing the loopholes.

---

## Non-Blocking Notes

### Note 1: Source-stamp rendering — editorial contradiction (§3.3)

The table in §3.3 states the Source element is "rendered text **includes** the `Source:` prefix (**verbatim whole line**, …)."

The note immediately after (bottom of §3.3) states "only the leading marker + surrounding whitespace are stripped."

These appear contradictory. **Resolution:** §4 (author notes), §5.6 (expected manifest), and §9 (assertion) all agree: the rendered text is the **captured group with the leading marker stripped**, producing one `Source:` prefix, not two (the TGRERA example uses `Source: Source: …` as input so the parser emits `Source: NewsMeter…` as output).

**Generator should implement to pass §9.** But this editorial ambiguity could burn a debug cycle. **Recommendation:** Change the §3.3 table row's parenthetical from `(…**verbatim whole line**, …)` to `(…captured group with leading marker and whitespace stripped, so full rendered text is `Source: <attribution>`, …)`.

### Note 2: Example manifest bbox is degenerate (§5.5)

The example surface in §5.5 shows `"bbox": [90, 0, 0, 0]` (zero width and height). This is a documentation placeholder. §9 asserts `assert w>0 and h>0`, so a real degenerate bbox would fail the test. Clarification: the example is schema illustration only; real bboxes must be computed from rendering and satisfy width/height > 0.

---

## Closure

The contract successfully avoids:
- Vague wording ("looks good", "reasonable")
- Untestable gates (all assertions are executable)
- Implicit assumptions (explicit error cases, grammar rules, required elements)
- Scope creep (non-goals listed; deferred work marked for Sprint 004+)
- Over-specification of layout (invariant-based, not pixel-coordinate-hard-coded)
- Regression risk (explicit hyd carousel non-regression check)

The two editorial notes above are self-resolving via the test suite (§9 will pass iff the Generator implements correctly) and are not blockers to implementation.

**Proceed to Sprint 003 generation.**
