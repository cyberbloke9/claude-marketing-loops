VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

---

## Summary

The Sprint 006 contract is **testable, specific, and well-scoped**. It authorizes TGRERA as a pure v2 carousel (format-slides only, no chart-card), validates it through the V2 gate to a clean PASS, and re-points `acceptance.py`'s TGRERA baseline from a frozen v1 chart-card to the new v2 carousel PNG/PDF determinism. The scope is limited to asset authoring + acceptance.py update; no render.py, validate.py, or measure.py changes are required. Pass/fail conditions are explicit (PASS verdict, `failed_checks: []`, pixel/byte determinism, no regression), commands are detailed (§6.1), and adversarial tests isolate each check (§6.2).

## Testability & Specificity

- **Commands (§6.1):** Seven concrete, runnable commands verify rendering, validation, determinism, acceptance, test suites, and v1 path immutability. Each produces machine-readable output (exit codes, JSON, test counts). ✓
- **Adversarial matrix (§6.2):** Fifteen attacks, each targeting a single check with the right rule cited (V16 missing so-what, V14 body at 24px, V15 thumbnail-illegible, V17 invalid pattern, R14 11-slide render fail). One-fixture-one-check discipline enforced. ✓
- **File scope (§2):** Four files touched: `formats.md` (new), `meta.md` (add block), `chart-spec.md` (supersede), `acceptance.py` (re-point). All others frozen. ✓
- **Expected outputs (§1.4, §6.1):** PASS verdict, `failed_checks: []`, PNG determinism (decoded-RGBA SHA), PDF byte-equality, schema v2 with pdf key, no chart-card.png, all v1/v2 fixture verdicts unchanged. ✓

## Non-Vagueness

- **Slide plan (§1.1):** Two slides specified (RECEIPTS cover, CHECKLIST utility+evidence), with dominant figures, inline so-what/source, wordmark on each. The contract allows flexibility on chip count (2-4 per RECEIPTS grammar) and copy wording, but mandatory roles/structure are clear. ✓
- **Meta.md blocks (§1.2):** Exact block format with required keys (`pattern`, `one_dataset`), literal values (pattern ∈ {BIG-NUMBER, CHART-FIRST}), and preservation of existing provenance block. ✓
- **Determinism (R8/R16/R18):** No network at render time, fonts from vendored `fonts/` only, identical input → pixel-identical PNGs (decoded-RGBA SHA) and byte-identical PDF. Stated as inherited from prior sprints. ✓
- **Regression budget (§9 Risk D):** Render suite must stay ≥266 OK; loop suite must stay 254 OK; acceptance.py must stay PASS with all 12 v1 + 9 v2 fixture rows unchanged and only `run_tgrera` re-pointed. ✓

## Load-Bearing Assumptions (Verified)

- **V8-skipped-on-format-slides (§1.4, §0.1):** The contract asserts V8 (source-stamp presence) is "skipped" on format-slides and applies only to chart-card/carousel-slide surfaces. Verified in `validate.py` frozen code: V8 check conditionally applies `is_chart or (srole == "carousel-slide" and has_stamps)`, returning "skipped" for `format-slide`. This is Sprint-005 frozen behavior. ✓
- **Prior-sprint implementations (Sprints 001-005):** The contract assumes V13-V19 checks, measure functions, manifest v2 schema, and PDF emitter are already correct. This is unavoidable in cumulative work and acceptable given the contract's explicit "frozen" lists. The §7 pre-contract probe (Path-A asset rendered + validated → PASS, 98 checks, 0 failed) provides empirical evidence. ✓

## Non-Gameable

- **Asset authenticity:** Copy restricted to public-order-only (provenance block kept, no TERREM DB numbers). Wordmark required on every slide. Dominant and so-what must be present and render-checkable (R11, V13, V16). ✓
- **V15 anti-gaming (Risk A + §4 Risk 5):** The contract forbids lowering thresholds to make TGRERA pass. "If the shipped headline band ever measures < 13, the asset copy/format must change (author-side) — not the threshold." The pre-contract probe recorded headline → 360px band **16** (floor 13, +3 margin). BUILD must re-confirm in trace. Thin but documented and enforced. ✓
- **No chart-card leak (Risk B):** Explicitly checked: `ls` verify no `chart-card.png`, manifest check `pdf` key present and all surfaces `format-slide`. ✓
- **Determinism attestation:** PNG and PDF byte-equality tested in §6.1(c) and §6.2 rows 3-4, and enforced by §10 definition of done points 4-6. ✓

## Well-Structured Risks & Mitigations

- **Risk A (V15 headline +3 margin):** Documented; BUILD must record 360px bands in trace and confirm ≥13/21. Contingency: author-side copy/format change, not threshold lowering. ✓
- **Risk B (mixed-asset leak):** Supersede `chart-spec.md`; verify `render_asset` emits no chart-card.png. ✓
- **Risk C (acceptance re-point is conscious extension):** `run_tgrera` re-points from v1 chart-card baseline to v2 carousel baseline; all other fixture rows kept byte-identical. Reactive-single coverage retained via `fx-good-min`. ✓
- **Risk D (regression budget):** 266/254/PASS counts must not fall. ✓
- **Risk E (provenance drift):** Copy must be public-order-only; provenance block kept intact (V11). ✓

## Minor Clarity Notes (Advisory, not blocking)

1. **Pattern vs. format distinction:** The contract correctly distinguishes the RECEIPTS *format* tag (one of seven templates) from the `pattern:` *designation* in meta.md (BIG-NUMBER or CHART-FIRST for A/B). Both are required but separate; this is explained in §1.2 and Risk 6 but requires reading the full contract to internalize. Well-resolved in text. ✓

2. **"Three order chips" example:** Described in §1.1 but flexed to 2-4 in the "Generator may adjust" clause. Clear once read in full. ✓

3. **§10 point 3 prescriptive skipped-check naming:** The contract specifies "V13–V19 all applicable-and-passing per §1.4 (V8/V5-floor/V7/V10 `skipped` as specified)". This is advisable to verify the validator reports skipped checks with the right reason; it's testable and not a vague demand. ✓

## Absence of Keyboard / Responsive / ARIA

§5 correctly marks these N/A for a CLI/raster sprint (no DOM, no viewport). ✓

## Non-Goals Honored

§8 correctly excludes: render.py/validate.py/measure.py changes, utility (dominant-less) standalone slides, PDF-fidelity lossy-page rework, v1 fixture edits, semantic "one-dataset" judgment, stub/placeholder copy, publisher/posting, and new brand tokens. The contract scope is tight. ✓

---

## Recommendation for BUILD

Execute in this order, **recording each step in trace:**

1. **Before code:** Confirm 266 render tests + 254 loop tests green; `acceptance.py` exits PASS on all 12 v1 + 9 v2 fixtures.
2. **Author TGRERA:** Create `formats.md` with 2-slide Path-A carousel (RECEIPTS + CHECKLIST, both dominant-bearing, inline so-what/source, wordmark per slide). Ensure all copy is public-order-only.
3. **Update meta.md:** Add `<!-- cover-pattern:start -->` block with `pattern: BIG-NUMBER` (RECEIPTS is the format; BIG-NUMBER is the cover pattern). Keep provenance block.
4. **Supersede chart-spec.md:** Rename or mark inactive so `render_asset` emits only format-slides (no chart-card.png).
5. **Render + validate:** Run §6.1 commands (a)-(b). Record manifest schema/pdf/roles and verdict/failed_checks.
6. **Re-render + compare:** Run §6.1(c) twice; record PNG decoded-RGBA SHA-256 and PDF byte-hash both times. Verify identical.
7. **Record V15 bands:** Manually or via V15 measurement tool, record headline + dominant 360px ink-band heights at 360px resampling. Confirm ≥13/21 and document in trace.
8. **Run acceptance.py:** Confirm exit 0, PASS, with `run_tgrera` on new v2 baseline and all other fixture rows unchanged.
9. **Run §6.2 adversarial tests:** Rows 1-5 (happy path), then rows 6-9 (mutations, each should fire the right check). Document any deviations.
10. **Verify regression:** Run §6.1(e)-(g) and confirm render suite ≥266, loop suite 254, and `fx-good-min` exits 0 with zero V13-V19 checks.

---

## Verdict

The contract is **ready to execute**. It has exact commands, expected outputs, adversarial attacks, regression safeguards, and well-documented risks. The only load-bearing assumption (V8 skipped on format-slides) is verified as Sprint-005 frozen code. No vagueness, no gaming opportunities, no blockers.

**ACCEPT.**
