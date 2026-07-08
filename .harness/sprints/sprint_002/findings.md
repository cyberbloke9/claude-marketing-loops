VERDICT: PASS
SCORE: 4.9
BLOCKERS: 0
HIGH: 0

# Sprint 002 Findings — Format Templates Batch A (BIG-NUMBER, RECEIPTS, CHECKLIST) + manifest v2

Mode: EVALUATE. Sprint 002. Verdict: **PASS**. No blockers, no high findings.
CLI/raster sprint — Playwright N/A. Attacked by rendering real PNGs, measuring
pixels/canvas, hashing decoded-RGBA bytes, feeding violating `formats.md` fixtures,
running both unittest suites, and visually inspecting the rendered slides.

## Evidence Ledger (reproduced, not claimed)

| Check | Result |
|---|---|
| Render fmt-big-number / fmt-receipts / fmt-checklist | PNG 1080x1350; role=format-slide; correct format tag; has_axis:false; schema_version="2" — PASS |
| V13 dominant ratio (measure.dominant_ratio_ok on emitted manifest) | BIG-NUMBER 132/26=5.08 (no-body fallback), RECEIPTS/CHECKLIST 132/30=4.40; exactly 1 dominant — PASS |
| V14 raised floors (measure.format_slide_type_min per non-wordmark element) | headline 52, body/so-what 30, source 26 clear floors — PASS |
| Exactly 1 wordmark per format-slide (R13) | 1 each — PASS |
| Color/bg tokens in §9 nine-token set + full schema field completeness | all in set, all fields present — PASS |
| Determinism (R18): re-render same asset folder | decoded-RGBA and raw PNG bytes identical; manifest byte-identical — PASS (see F-001 note) |
| F-001 exit-2 guard: validate.py <v2-asset> | exit 2, cited "format-slide … V13-V19 … [PIPELINE-V2.md §4]", no traceback, nothing written — PASS |
| Fail-loud: 0 dominant / 2 dominant / 0 wordmark | ValueError, exit 1, no render/ written — PASS |
| Fail-loud: RECEIPTS 1-chip / 5-chip; CHECKLIST 1-step | ValueError naming [2,4] / min>=2, no partial write — PASS |
| Fail-loud: 11-slide carousel (R14) | ValueError "cap is 10 (R14…)", no write — PASS |
| Fail-loud: unsupported tag TIMELINE / unparseable line | ValueError naming slide+tag / slide+line — PASS |
| Atomicity: valid slides 1-2 then broken slide 3 | ValueError, nothing written (in-memory build, atomic emit) — PASS |
| v1 freeze: re-render hyd + tgrera | schema_version "1", git status content/ clean (byte-identical) — PASS |
| v1 guard-silence: validate.py fixtures/fx-good-min | VERDICT: PASS, exit 0 — guard does not fire — PASS |
| Render suite | Ran 219 … OK (baseline 182; +37, none weakened) — PASS |
| Loop suite | Ran 254 … OK (unaffected) — PASS |
| No-network import of render/validate/measure | import-ok — PASS |
| Additivity: git diff render.py / validate.py | deletions confined to render_asset docstring/body (explicitly extended per contract §2) + schema-version conditional + widened schema frozensets; no v1 style constant or v1 parse/render function edited — PASS |

## Visual inspection (raster craft)

Read all three rendered PNGs directly:
- BIG-NUMBER — ink context headline, single accent dominant ₹14.95L doing the hook, muted so-what line, TERREM accent-deep wordmark bottom-right. One accent, clean hierarchy.
- RECEIPTS — ink eyebrow, accent dominant SALES FROZEN, three bordered white chips, wordmark. Verified RECEIPTS manifest has exactly 6 elements (1 dominant + 1 headline + 3 body-chips + 1 wordmark), zero empty-text rows — chip borders are decorative primitives (--border/--surface), NOT phantom manifest elements (contract row 2 / §1.4). Correct grammar.
- CHECKLIST — accent dominant index numeral 3, ink context, three muted numbered steps, so-what link, wordmark.

No AI slop, no Lorem/placeholder copy, no generic defaults. Copy is domain-specific
(RERA numbers, TERREM, Hyderabad builders). Brand tokens + Inter faces honored;
one-accent discipline held on every surface.

---

## Contract Note CN-002 (informational, NOT a blocker, NOT a Generator code defect): contract §7(c) determinism command is mis-specified

Severity: Low
Category: Process
Status: Informational — behavior is correct; the contract's own test command has a bug.

### Observation
Contract §7(a)/(c) copies each fixture to /tmp/$f-a and /tmp/$f-b (different folder
basenames) then asserts manifest.json bytes identical. The literal command yields an
AssertionError — but only on the slug field, derived from folder basename
(slug = folder.name, frozen v1 behavior). PNGs are raw-byte-identical; manifests differ
solely by "slug": "fmt-big-number-a" vs "…-b". Confirmed across ALL THREE fixtures
(big-number, receipts, checklist): the diff's only differing line is the slug in each.

### Why this is NOT a defect
The real R18 guarantee — same asset folder rendered twice -> byte-identical output —
holds (verified: rendered /tmp/det-test twice -> cmp identical manifest + PNG). The
Generator's shipped test_written_outputs_byte_identical_across_runs correctly renders
same-basename folders in different temp parents (slug identical) and passes. The manifest
is a deterministic function of (folder basename + formats.md); copying to differently-named
dirs changes an input, so a different slug is correct, not a determinism break. Mirrors
frozen v1 renderer behavior.

### Required Fix (contract hygiene only — no code change)
A future contract asserting manifest byte-equality must render the same-basename folder
twice (as the Generator's own test does), or exclude slug from the comparison. Do not copy
to -a/-b basenames and expect identical slugs.

### Pass Condition
Already met: R18 same-input determinism proven by cmp-identical re-render and the
Generator's passing byte-equality test.

---

## Scoring

Weights (raster/infra, additive freeze-sensitive): Functionality 25%, Craft 25%,
Design 20%, Evidence/Process 20%, Originality 10%.

- Functionality: 5 — every §10 DoD item and §8 matrix row reproduced; all 8 fail-loud states raise with no partial write; atomic emission holds; F-001 guard clean exit-2.
- Craft: 5 — purely additive; v1 code byte-frozen (hyd/tgrera clean diff, fx-good-min PASS, 182->219 tests none weakened); 37 new tests.
- Design: 5 — brand-locked formats, one accent per surface, strong dominant hierarchy, no slop.
- Evidence/Process: 5 — trace records 182/254 baseline confirmed before code, files changed, new-test count, freeze evidence, disclosed risks. Independently reproduced.
- Originality: 4 — domain-specific, non-generic; faithful spec execution (not a novelty sprint).

Weighted total ~= 4.9. Passing bar met: 0 blockers, 0 high, evidence >=4, functionality >=4, weighted >=4.

## Verdict
PASS. Sprint 002 delivers the three batch-A format templates at 1080x1350 with a provable
>=3x dominant, raised floors, on-card wordmark, schema-v2 manifest emission, atomic
fail-loud invalid states, the F-001 exit-2 guard, and a byte-for-byte v1 freeze — all
reproduced on real renders and both green test suites. The single non-passing item
(contract §7c literal command) is a contract-test artifact, not a code defect, and does
not gate the sprint.
