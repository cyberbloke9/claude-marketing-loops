VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 002 Findings — Carousel Renderer + Manifest

Mode: EVALUATE. Sprint 002. Headless CLI raster tool (no browser / no Playwright,
as contract §0 states). The Evaluator attacked the CLI directly and inspected the
produced PNGs + manifest. Every check below was re-run independently from a clean
render — not trusted from generator_trace.log.

## Result summary

All required behaviors (R1, R3, R4, R7, R8, R9 for the carousel surface; §5.3 manifest
schema; §6 states; §7 design fidelity) are implemented, observable, and reproducible.
No blockers, no high findings. Recommend advancing to Sprint 003.

## Evidence (independently reproduced)

1. Unit tests (§8.0): `python3 -m unittest discover -s tools/marketing-render/tests`
   -> Ran 70 tests ... OK (exit 0). Read the suite directly (not trace-trusted): it has
   genuine assertions for parse, style assignment, layout/safe-zone, glyph-guard/tofu
   (asserts slide+role in message), font SHA-256 pin, chart_ref, and error states that
   assert exit code 1 AND no `render/` dir written (test_missing_folder / test_missing_carousel
   / test_unparseable_writes_nothing), plus stack-overflow fail-loud (test_overflow_fails_loud).
   Note: the §6 "missing vendored font" state has no dedicated named unit test; it is covered
   by the §8.4 presence/SHA-pin test (all four TTFs + OFL confirmed present) and by the atomic
   design (fonts load during the in-memory render phase, before any write) — a missing font
   would raise FileNotFoundError -> exit 1 with no partial output by construction. Not a gate.
2. Render (§8.1): clean `rm -rf render/` then render.py on the hyd asset -> exit 0;
   wrote carousel-01..08.png + manifest.json under render/, nowhere else.
3. Determinism / R8 (§8.2): cross-process double render; decoded-RGBA SHA-256 per PNG
   and byte-identical manifest -> DETERMINISTIC.
4. Import purity (§8.3): imports = PIL,argparse,json,math,measure,pathlib,re,sys; no extras.
5. Fonts vendored (§8.4 + R4): four Inter TTFs + OFL.txt present; source contains no
   /System/Library, /opt/homebrew, /Library font path. Font SHA-256 (first 16) match the
   contract §2.1 pin exactly: Regular 3127f0b873387ee3, Medium a645f55492d1c8cd,
   SemiBold b0b540e69bf67170, Bold 412c068eab6f36e6. OFL.txt is real SIL OFL 1.1 (90 lines)
   with the Inter copyright line.
6. §9 adversarial attack script (full): prints "OK — dims, tokens, schema, bg-dominance,
   exact-copy, one-hook, hook<=10 words, safe zones, ink-present all hold". Covers real
   1080x1350 pixel dims from bytes; >=1800/2000 bg-token dominance; every color/bg a locked
   token; V5 type minimums; V6 safe-zone containment; V3 anti-stub ink-present in every bbox;
   exactly one hook (slide 1, <=10 words); source-stamp with Source+"as of" on S3 and S8;
   TERREM wordmark accent-deep on S8; verbatim (role,text) match for all 8 slides with
   per-slide element-count equality (no dropped/phantom/mangled copy).
7. Error states (§6) — beyond the contract's own script:
   - Missing folder -> "error: asset folder not found: ...", exit 1, no writes.
   - Missing carousel.md -> "error: carousel.md not found in ...", exit 1, no writes.
   - Unparseable line -> "error: unparseable line on slide 1: '...'", exit 1; confirmed the
     asset dir contains NO render/ afterward (atomic, no partial output).
   Also verified in the manifest: chart_ref is "chart-spec.md" on carousel-03 only, null elsewhere.
8. Scope (§2): git diff --name-only -> only carousel.md modified. The diff is exactly the
   three §3.4 disambiguation edits (S3 caption/source split, S7 UTM comment, S8 link prefix +
   comment) — no rendered copy changed. New files confined to tools/ and the tool's render/.
9. Visual inspection (not just ink-present): carousel-05 and carousel-08 render correctly —
   bold ink headline, muted body, ₹ / en-dash − / em-dash — / middot · all render as real
   glyphs (no .notdef tofu), clean greedy wrap, flat #faf8f3 canvas, one accent per surface.
   S8 link correctly in ink-muted (wordmark present) and TERREM wordmark bottom-right in
   accent-deep #0d3d38. Brand-token fidelity is faithful, not slop.

## Scope-honesty check

The demo asset is KILLED on provenance (its meta.md); contract §0 correctly scopes Sprint 002
to rendering correctness only and does not claim a QA PASS. Not mis-scored on "should publish"
— a QA verdict is Sprint 004 (V11).

## Trace review

generator_trace.log records contract authoring, the CR-001/CR-002 rejection + in-place fixes
(dead-code bgc line removed; exact-text assertion block added), the BUILD, and the determinism
re-verify after the source-stamp-prefix fix. Commands + outputs present with artifacts. Every
claim was independently reproduced — no claim-without-artifact, no skipped failure, no broad
rewrite after a small finding.

## Scoring (systems/infra reweight)

- Functionality 30% -> 5.0 (all behaviors + error states work, verified).
- Craft 25% -> 5.0 (deterministic, atomic, fail-loud, anti-tofu guard, no scope creep).
- Evidence/process 25% -> 5.0 (every check independently reproduced from clean state).
- Design 15% -> 5.0 (faithful token fidelity, real-glyph rendering, clean layout).
- Originality 5% -> 3.0 (intentionally non-novel: brand-preservation raster tool; §7 mandates fidelity).

Weighted total ~= 4.8. Functionality 5 >= 4, Evidence 5 >= 4, weighted >= 4, zero blockers,
zero high -> PASS is legal.

## Findings

None. No Blocker, High, Medium, or Low findings.
