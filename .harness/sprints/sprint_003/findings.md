VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 003 Findings — Chart-card renderer + TGRERA receipts spec

## Mode & scope
EVALUATE, Sprint 003. Headless Python/Pillow CLI raster tool — no browser/web UI,
so no Playwright click-path exists (correctly declared in contract §0). Attacked at
the CLI directly; output PNG + manifest probed with Python; independent visual read
of the rendered PNG. All checks run from a clean render state.

## Evidence summary (all reproduced independently)

1. Unit suite — `python3 -m unittest discover -s tools/marketing-render/tests -v`
   -> Ran 93 tests OK (exit 0). 69 Sprint-001/002 tests still pass (no regression)
   + 24 new chart-card tests.

2. Clean render (R2, R9) — removed render/, ran render.py on TGRERA -> exit 0,
   wrote exactly chart-card.png + manifest.json under render/, nothing else.

3. §9 adversarial attack script -> "OK — all §9 assertions hold" (exit 0).
   Independently confirmed: real pixel dims 1080x1920 from image bytes (V2); bg
   dominates canvas (>=1900/2000 sampled px); schema_version/slug correct; single
   chart-card surface; has_axis=false with axis fields null; every color/bg a brand
   token; V5 type mins (headline 44>=36, body 27>=24); V6 vertical safe-zone for
   headline/body; V3 anti-stub ink inside every bbox; source-stamp has Source + as of
   + 2026-06-22 (V8-ready); wordmark literal TERREM, #0d3d38, right-anchored x+w=990;
   exact 6-element copy/order match.

4. Determinism (R8) — rendered twice cross-process; decoded-RGBA SHA-256 of PNG and
   byte SHA-256 of manifest identical -> DETERMINISTIC.

5. HYD non-regression — re-rendered hyd -> still 8 carousel-slide surfaces, no chart
   card (old free-form chart-spec.md skipped for lack of Surface: chart-card marker).
   hyd source untouched.

6. Import purity (R4) — AST scan: only PIL, argparse, json, math, measure, pathlib,
   re, sys — subset of allowed; no network/third-party beyond Pillow.

7. Fail-loud states (independent, not from contract self-test) — each exits non-zero,
   writes no render/ dir: has_axis:true -> exit1; Canvas:1080x1080 -> exit1; missing
   Wordmark -> exit1; garbage line -> exit1; empty folder -> exit1; missing folder ->
   exit1. Each names the offending value.

8. Scope integrity — measure.py and test_render.py SHA-256 unchanged; hyd chart-spec
   has 0 Surface: chart-card markers; TGRERA meta.md not edited (0 verdict lines —
   correctly deferred to Sprint 004).

9. Visual inspection of chart-card.png — real, non-stub, brand-faithful: bold ink
   headline over two lines, three muted receipt lines (Jun 22/27/30) with em-dashes,
   %, Rs, middots all rendering (no tofu), muted source stamp with dates, accent-deep
   TERREM wordmark bottom-right, flat cream #faf8f3 canvas. Tufte-clean, no chartjunk,
   single accent, left-aligned editorial. Matches §7 design direction.

## Trace review
generator_trace.log records contract authoring, build, 93-test run, render, §8/§9
checks — each with reproducible output. Two self-declared minor risks (outside-fence
garbage not fail-loud; _assert_glyphs reuses the word "slide" in a chart-card tofu
message) are honestly flagged, non-blocking, and consistent with the code. No skipped
failures, no claims without artifacts, no broad rewrite after small findings.
Authored TGRERA copy is provenance-safe (public regulator orders; Rs not DB numbers).

## Scoring
- Functionality 5 (render, manifest, determinism, all error states, hyd non-regression)
- Evidence/process 5 (every claim independently reproduced from clean state)
- Craft 5 (deterministic integer layout, anti-tofu guard, atomic writes, safe-zone-by-construction)
- Design 5 (locked-token fidelity, Tufte-clean, correct brand reproduction)
- Originality 4 (intentional fidelity/reproduction tool, not novelty — scored on faithfulness per §0)
Weighted (20% each): (5+5+5+5+4)/5 = 4.8. No blockers, no highs, evidence>=4,
functionality>=4, weighted>=4 -> PASS.

## Evidence completeness note (V5 seam, deferred not silently passed)
The spec V5 property "manifest cannot lie about font size" (bbox-height <-> font_px
±25% cross-check) is NOT proven this sprint — the validator that performs it (V5)
does not exist until Sprint 004. Bboxes were verified non-degenerate and ink-
present, but that a declared font_px:44 actually rasterizes at ~44px is asserted-
not-proven here. This is legitimately Sprint 004 territory and does not block. No
red flag: the visual headline/body glyph-height ratio (~1.6x) matches the declared
44/27 ratio, so the manifest sizes are consistent with the render. Flagged for the
S004 evaluator to prove mechanically.

## No findings
No Blocker, High, Medium, or Low defects observed. The sprint delivers exactly its
declared scope and every contract check reproduces.
