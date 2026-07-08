VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 006 Findings — TGRERA v2 carousel + PDF + full end-to-end, no regression

Mode: EVALUATE. CLI/raster sprint — Playwright not applicable (no browser UI/DOM). Attacked by rendering real PNGs/PDF, byte/pixel-inspecting artifacts and qa-verdict.json, running both unittest suites + acceptance.py, and mutating the TGRERA input to prove gate teeth. All checks run from a clean tree with the committed code.

## Verdict summary
Clean PASS. Every DoD item (§10) verified on disk and reproduced independently. No blocker/high/medium findings. The disclosed deviation (TGRERA v1 chart-card test coverage relocated to a retained snapshot) is a TRUE relocation, not a weakening (see Deviation Audit).

## Evidence — reproduced independently
DoD 1 — pure carousel render (Risk B). render.py TGRERA -> exit 0; emits format-01.png, format-02.png, carousel.pdf, manifest.json. Manifest: schema_version "2", top-level pdf: carousel.pdf, both surfaces format-slide (RECEIPTS, CHECKLIST). NO chart-card.png. Confirmed.

DoD 2 — meta.md blocks. Provenance block byte-identical to git HEAD (cmp passes -> V11 intact, Risk E). Valid cover-pattern block: pattern: BIG-NUMBER, non-empty one_dataset:. Confirmed.

DoD 3 — full V2 gate PASS. validate.py --checked-on 2026-07-08 -> exit 0, verdict PASS, failed_checks: [] (98 checks, 26 skipped). Dispositions match §1.4: V2/V3/V4/V9/V11 PASS; V13/V14/V15/V16/V17/V18/V19 PASS; V5-floor/V7/V8/V10 skipped (frozen applicability — V8 skip on format-slides is per Risk 1, not a FAIL); V5-crosscheck PASS; V6-safezone PASS for gated roles / skipped for exempt roles. Confirmed.

DoD 4 — determinism (R8/R16). Two independent renders into separate temp dirs: both PNGs decoded-RGBA SHA-256 identical (28252b22..., ce0ec8d4...); carousel.pdf byte-identical (cmp passes). Confirmed.

DoD 5 — acceptance re-point (Risk 2/C). acceptance.py -> exit 0, ACCEPTANCE: PASS (25/25). run_tgrera re-pointed to v2 baseline: TGRERA_EXPECTATIONS=4 (render-shape / no chart-card / carousel.pdf present / schema-2 all format-slide; PNG decoded-RGBA determinism; PDF byte determinism; validate exit 0). Honest count (21 fixture rows + 4 TGRERA = 25). All 12 v1 + 9 v2 fixture rows byte-unchanged, reaching existing verdicts; 9 fx-v2 fixtures each fire their singleton target id; fx-v2-good exit 0. Confirmed.

DoD 6 — regression budget. Render suite Ran 266 ... OK (held). Loop suite Ran 254 ... OK (held). Confirmed.

DoD 7 — frozen v1 path. fx-good-min qa-verdict has ZERO V13-V19 records ([]). Chart-card coverage preserved (Deviation Audit). Confirmed.

DoD 8 — trace. generator_trace.log records baselines-before-code, files changed, shipped V15 bands, run_tgrera re-point, no-chart-card confirmation, provenance intact, deviation disclosure. Confirmed.

## Gate-teeth (adversarial matrix, run on copies)
- Drop inline So-what: -> failed_checks == ['V16-so-what'] (only). Right check, right rule.
- Invalid pattern: value -> failed_checks == ['V17-cover-pattern'] (only).
- Hand-shrink a body font_px to 20 in manifest -> V14-type-floor FAIL. V5-crosscheck co-fires — expected/correct (manifest edited without re-render, declared != measured); not a defect.
- Declare an 11th slide -> render exit != 0, "cap is 10 (R14, Instagram API limit)", NO render/ dir written (no partial write).

## Deviation Audit — TGRERA v1-test relocation (CONTROL POINT)
Generator relocated ~19 chart-card-coupled tests from the live content/...tgrera... folder to a retained snapshot under tools/marketing-render/tests/data/2026-07-03-tgrera-enforcement-wave/. Verified TRUE relocation, not weakening:
1. Snapshot input byte-identical to HEAD: chart-card.png, render/manifest.json, chart-spec.md, script.md, and meta provenance block all cmp-identical to git show HEAD.
2. Render path genuinely re-exercised: relocated test_chart_card.py reads chart-spec.md from the snapshot and re-runs render.parse_chart_spec / render.render_chart_card / render._layout_chart_card against byte-identical input — coverage is not reduced to a static PNG read.
3. Only the path constant moved: diffs of the four touched test files show _TGRERA re-pointed to the snapshot (plus one attachment-path string in test_package.py); every assertion preserved verbatim. None weakened/deleted.
4. Regression floor held: render suite stayed at 266 OK — coupled tests still run and pass; deletion would have dropped below the DoD-6 floor.
5. Spec-mandated: spec Risk 2 requires "the old chart-card render/validate code path stays exercised." Live-folder-as-v2 and folder-as-chart-card cannot coexist, so relocation is the only move satisfying DoD 1-5 + DoD 6 + Risk-D ("never weakened or deleted") together. Generator's disclosure that the contract Risk-D parenthetical ("only run_tgrera qualifies") was empirically wrong is honest and correct.

## Visual inspection (screenshots, not claims)
Read both shipped PNGs directly (Read renders images):
- format-01 (RECEIPTS cover): clean hierarchy — bold ink headline "3 builders. 9 days.", large teal dominant "SALES FROZEN" (two lines, no collision with the chip stack), three bordered white chips well-spaced and legible (amount/consequence leading, builder + date), TERREM wordmark bottom-right in accent-deep. Exactly one accent (teal) on the dominant. No tofu/clipping/overflow/slop.
- format-02 (CHECKLIST): teal "3" index dominant, three legible steps, inline so-what wrapping cleanly to two lines ("Check the RERA number before you pay — free -> intel.terrem.in"), muted source stamp. Denser but legibility and hierarchy intact; within the CHECKLIST grammar. No defect.
Design/Originality scores are now evidenced by the rendered artifacts, not the generator's assertion.

## V15 reconciliation (Risk A)
The real LANCZOS ink-band measurement the gate uses (qa-verdict.json V15 detail) is: format-01 headline "360px band 16px >= 13" (+3, thin but clears), format-01/02 dominant "band 32px >= 21" (+11). This matches the generator's recorded 16 exactly; my earlier arithmetic thumbnail_scale_band(52)=17.3 was a different proxy computation, not the gate's measurement — the dispositive number is the gate's 16, and V15-thumbnail PASS is genuine.

## Determinism / no-network / provenance
Render + validate ran offline (stdlib + vendored Pillow only; no new third-party dep). TGRERA copy is public regulator-order facts only, no TERREM DB numbers; provenance block byte-frozen. No secrets introduced.

## Scoring (systems/infra — Functionality + Evidence weighted up)
- Functionality: 5 — full end-to-end PASS; happy + failure paths reproduce.
- Evidence/process: 5 — exhaustive reproducible trace; deviation disclosed and independently verified.
- Craft: 5 — fully additive to frozen code; only acceptance.py run_tgrera + asset authoring + path-only test relocation; frozen v1/v2 paths byte-intact.
- Design: 4.5 — real information-hierarchy format library (dominant >=3x body), one accent per surface, no slop.
- Originality: 4.5 — genuine format-grammar/QA-gate design, not a library default.
Weighted (Functionality 25%, Evidence 25%, Craft 20%, Design 15%, Originality 15%) ~= 4.8. Passing bar met (no blockers/highs, evidence >=4, functionality >=4, total >=4).
