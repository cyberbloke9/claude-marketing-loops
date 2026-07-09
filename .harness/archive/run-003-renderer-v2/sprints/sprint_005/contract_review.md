VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

This is a rigorous, testable contract for Sprint 005 (QA Gate V2 checks V13–V19 + adversarial fixtures). The contract is well-scoped, provides concrete commands and fixture specifications, and correctly depends on Sprint 001's pure measurement functions (verified on disk: `dominant_ratio_ok`, `format_slide_type_min`, `thumbnail_ink_ok`, `parse_cover_pattern_block`, `cover_pattern_valid`, `one_dataset_present` all exist with correct signatures and thresholds).

The route invariant is clear: V13–V19 checks fire only on `format-slide` surfaces, leaving the 12 v1 fixtures + hyd carousel + TGRERA unchanged. The guard at `validate.py:728–733` is correctly identified for removal. The adversarial fixture matrix (§6.4) is precise: each fixture targets one check id, and the acceptance runner's singleton assertion (`failed_checks == [target_id]`) will catch any co-firing defect.

The contract embeds strong self-checks (Risk A empirical probe in trace, singleton matrix assertion) that mitigate potential edge cases. Verification commands in §6.3 are executable and complete.

**The contract is ACCEPT-ready.** No blocking defects found.

---

## Medium-level notes (non-blocking clarifications)

### M-001: Fixture value `fx-v2-dominant-small` margin is thin but defended

**Risk:** The fixture specifies `dominant 80px` on a `body 30px` slide, yielding ratio 2.67 (target: V13 FAIL). Risk A mitigation says "every non-V15 fixture render … dominant ≥100px so measured bands clear 13/21 with ≥3px margin." Arithmetic shows 80px yields ~22.1px band at 360px, only 1.1px above the V15 floor (21px). This is below the ≥3px margin guidance.

**Mitigation:** The contract already requires empirical band measurement for positive control AND this fixture in §1.1 Risk A and §10: "BUILD MUST record the actual measured bands … in `generator_trace.log`." The acceptance matrix row 2 asserts singleton (`failed_checks == [V13]`), so any co-firing V15 will be visible and fail the matrix. This is a self-checking design. The risk is real but defended.

**Action:** None — the contract's empirical probe requirement is sufficient. Builder should verify 80px renders cleanly and yields ≥21px band with margin, recorded in trace.

---

### M-002: Fixture "degrade-render" mechanism for `fx-v2-thumb-illegible` unspecified

**Gap:** The contract says illegible headline should be "degrade-rendered so its 360px band < 13" (contract §6.1). The mechanism (thin font weight, blur filter, reduced rendering quality, etc.) is not specified. The contract only specifies the test outcome: (V14 floor passes declared 48px, V5-crosscheck passes ±25% band measurement, V15 fails).

**Status:** Non-blocking. The test condition is precise and testable. The builder has freedom in implementation method as long as the outcome is met. Risk B mitigation (singleton assertion) will catch any deviation.

---

### M-003: `make_v2_fixtures.py` determinism verification command incomplete

**Gap:** Contract §6.3 says:
```
# (d) Regenerate v2 fixtures deterministically, then diff (no drift)
python3 tools/marketing-render/fixtures/make_v2_fixtures.py
```

The comment says "then diff" but no diff command is shown. The contract states in §7 "byte-identical PNGs + manifests (decoded-RGBA SHA / byte-equality)" but doesn't specify how to verify this during evaluation.

**Suggestion:** Add explicit diff command:
```
cp -r tools/marketing-render/fixtures/fx-v2-* /tmp/fixtures_backup
python3 tools/marketing-render/fixtures/make_v2_fixtures.py
diff -r /tmp/fixtures_backup tools/marketing-render/fixtures/fx-v2-* || exit 1
```

Or clarify the script's output behavior (in-place regeneration with assertion, or temp-dir output for comparison).

**Status:** Non-blocking clarity issue. The builder will understand "regenerate, then diff" and implement the natural approach. The acceptance test can verify byte-equality directly.

---

### M-004: R14 fail-loud test case placeholder

**Gap:** Contract §6.3 command (g) references `<11-slide formats.md folder>` without a concrete fixture path or example. The builder should know to create a test input, but the contract could show which fixture or where to place it.

**Status:** Minor. The builder understands the requirement (11-slide → exit 1, no partial write). Can create an ad-hoc test input or fixture.

---

### M-005: V5-floor skipped on format-slides, V14 owns it — routing clarity

**Note:** The contract correctly specifies (§1.1 routing invariant) that V5-floor is `skipped` on format-slides and V14-type-floor owns the per-element floor checks. The code must ensure `_check_element` does NOT call `measure.type_min_ok("format-slide", …)` (which would raise ValueError — `type_min_ok` only knows `{carousel-slide, chart-card}`), and instead calls `measure.format_slide_type_min(element_role, …)`.

**Status:** Verified in code. `measure.type_min_ok` at line 150 raises ValueError if surface_role not in `{carousel-slide, chart-card}`. Contract correctly specifies this must be routed through V14 in `validate.py`. Builder will follow the contract's wiring instructions.

---

## Verification checklist (Evaluator will confirm at EVALUATE time)

- [ ] `validate.py` guard at 728–733 is removed and replaced with V13–V19 check execution
- [ ] V13–V19 emit zero records on pure-v1 assets (regression check: v1 fixtures reach unchanged verdicts)
- [ ] Nine `fx-v2-*` fixtures exist and are deterministically regenerable (byte-equality confirmed)
- [ ] Each adversarial fixture's `failed_checks` is a singleton of its target id (matrix assertion)
- [ ] `fx-v2-good` exits 0 (clean PASS)
- [ ] `acceptance.py` EXPECTATIONS table extended with 9 v2 rows; all pass
- [ ] Render test suite count ≥263 and passing
- [ ] Loop test suite = 254 passing (no regression)
- [ ] R14 fail-loud (11-slide formats.md → exit 1, no partial write) re-confirmed
- [ ] Risk A empirical band probe for positive control and `fx-v2-thumb-illegible` recorded in trace with measured values

---

## Conclusion

The contract is **ACCEPT**. All core requirements are specific, testable, and grounded in verified code. The non-blocking notes are clarifications that do not prevent build. The self-checking infrastructure (empirical probes, singleton matrix assertions) is strong and will catch edge cases at evaluation time.
