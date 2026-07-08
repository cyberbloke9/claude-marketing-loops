VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

---

## Contract Review: Sprint 004 (Deterministic Multi-Page PDF Emitter)

### Summary

This is an exemplary contract. It defines the emission of `carousel.pdf` from format-slide surfaces with byte-determinism guarantees, regression-budget transparency, and non-gameable evidence standards. Every requirement is specific, every error state is covered, and every verification command is copy-paste-ready.

### Findings

#### ✓ Scope and Focus

The contract has a single, clear job:
- Emit `carousel.pdf` (one page per format-slide, in slide order) from assets with `schema_version "2"`
- Achieve byte-identical PDFs across independent `render.py` process runs
- Record top-level `"pdf": "carousel.pdf"` manifest key
- Leave v1 path (hyd, tgrera, frozen fixtures) completely unchanged
- Touch only `render.py` and `tests/test_render_v2.py`

Out-of-scope items are explicit: V13-V19 wiring (Sprint 005), validate.py edits (already tolerates `pdf` key), measure.py (frozen), acceptance.py (Sprint 006), TGRERA content (Sprint 006).

#### ✓ Output Specification (Exact)

- **File path:** `content/<slug>/render/carousel.pdf` (§1.1, R19)
- **Content:** ordered PNG rasters as PDF pages, 1080×1350 per page, one page per format-slide in manifest order (§1.1, R15)
- **Manifest key:** top-level `"pdf": "carousel.pdf"` (§1.2, §5.3), present iff `schema_version == "2"` (§1.2), JSON serialized with `sort_keys=True` for deterministic byte layout
- **v1 behavior:** no PDF emitted, no `pdf` key added, manifest byte-identical after re-render (§1.2, §1.5)

#### ✓ Byte-Determinism Requirement (R16) — Non-Gameable

§1.3 specifies the exact evidence standard and explains why it defeats common shortcuts:

> "the byte-equality proof renders the same input under **two separate `python3 render.py` invocations into two different parent dirs with an identical basename** (the Sprint-003 `s4a`/`s4b` two-parent slug-identity pattern) and compares the two on-disk `render/carousel.pdf` files with `cmp`/SHA-256. A same-process `BytesIO` round-trip proves only that the encoder is deterministic; it does **not** prove cross-run determinism (the R16 requirement) and does not exercise the real save path (where Title is filename-derived unless pinned)."

This explicitly prevents:
- Fake "proof" via `BytesIO` round-trip (proves encoder consistency, not cross-process stability)
- Skipping the real filesystem save path (where Pillow's filename-derived Title could vary)

Metadata suppression requirements are explicit and mechanically checkable:
- CreationDate/ModDate suppressed (no `time.gmtime()` per-run values leaked)
- Producer pinned to a fixed string (independent of environment beyond Pillow's embedded version comment)
- Title pinned independent of save path (no `os.path.splitext(basename(filename))` derivation)
- No `/ID` array in trailer (verified for Pillow 11.3.0)

#### ✓ Regression Budget Transparency (Exemplary)

§0 is the gold standard for handling conscious breaking changes:

> "Sprint 003 shipped **two** tests named `test_no_pdf_key_this_sprint` ... each asserting `assertNotIn("pdf", manifest)`. Emitting the PDF this sprint **legitimately flips both** — a v2 manifest now MUST carry `pdf: "carousel.pdf"`. Under the hard regression budget these two tests are **consciously re-pointed** to assert the **positive** invariant (`manifest["pdf"] == "carousel.pdf"` on a format-slide asset) **and** the preserved negative invariant (a `schema_version "1"` manifest — hyd/tgrera — still has **no** `pdf` key). This is a conscious extension (the "v1 manifests carry no pdf key" guarantee is preserved and re-proven; only the too-early "v2 has no pdf key" assertion moves to its correct post-Sprint-004 value), **never a silent deletion**. No other existing assertion is weakened."

This is clear because it:
- Names the exact tests (test_no_pdf_key_this_sprint)
- Names exact line numbers (`:84` batch-A, `:454` batch-B)
- Distinguishes "flip" (conscious change) from "deletion" (silent regression)
- Preserves the v1 guarantee ("v1 manifests carry no pdf key" is re-proven)
- States the scope ("No other existing assertion is weakened")

#### ✓ Error and State Handling (Complete)

§4 covers all cases:
- Missing asset folder → FileNotFoundError, exit 1, nothing written
- Success (v2) → PNGs + manifest (with `pdf` key) + carousel.pdf, exit 0
- Success (v1) → PNGs + manifest (no `pdf` key), no carousel.pdf, exit 0
- Invalid formats.md (e.g., ≥11 slides) → ValueError, exit 1, **no partial write** (R19 atomicity)
- validate.py on v2 asset (now carrying `pdf` key) → exit 2 cited, no traceback (schema already tolerates it)

Atomicity is explicitly required (§1.4): "The PDF is built in memory (or written) only **after** `render_asset` succeeds; any parse/layout error still raises **before** any file ... is written." Adversarial matrix row 15 tests this.

#### ✓ Verification Commands (10 Blocks, Copy-Paste Ready)

§7 provides commands a–j with explicit expected outputs:
- (a) Baseline: render `Ran 252 … OK`, loop `Ran 254 … OK`
- (b) Cross-process byte-determinism: `cmp /tmp/s4a/*/render/carousel.pdf /tmp/s4b/*/render/carousel.pdf` → identical
- (c) Page-count and manifest key: `assert m.get("pdf")=="carousel.pdf"`, `assert pages == len(fs)`
- (d) Multi-page proof: `n_frames == 3` for fmt-multi
- (e) No per-run metadata: `assert b"CreationDate" not in b`, `assert b"ModDate" not in b`, `assert b"/ID" not in b`
- (f) v1 freeze: hyd/tgrera emit no PDF, byte-identical re-render, `git status --porcelain content/` empty
- (g) validate.py on v2 asset: exit 2, cited, no traceback
- (h) Atomicity: 11-slide formats.md fails, no `render/` dir
- (i) Full suites: render `Ran N>252 … OK`, loop `Ran 254 … OK`
- (j) No-network import

#### ✓ Adversarial Matrix (20 Rows, Non-Overlapping)

§8 provides exhaustive, isolable attacks. Each row tests a single behavior:
- Rows 1–4: PDF existence, page count, page order
- Rows 5–9: Byte-determinism, metadata suppression, producer comment
- Rows 10–13: Manifest keys (v2 present, v1 absent), v1 freeze
- Rows 14–16: validate.py tolerance, atomicity, mixed-asset rule
- Rows 17–20: Test re-pointing, suite counts, no-network, no new deps

No row depends on another; each is independently testable.

#### ✓ Scope Boundaries and Risk Awareness

Explicitly stated:
- "R16 byte-equality is a **same-environment, same-Pillow-version** guarantee. ... cross-machine PDF byte-equality is out of scope and not claimed." (§0)
- "Pillow writes a fixed comment `created by Pillow <version> PDF driver` into every PDF; that version string is environment-pinned, not a cross-machine promise." (§0)
- Disclosed risks in definition of done (§10): "env-pinned Pillow producer comment; Title pinned independent of save path; mixed-asset page-set rule"

#### ✓ Non-Goals (Explicit, 9 items)

§9 lists what this sprint does NOT do:
- No V13-V19 QA wiring
- No measure.py change
- No validate.py change
- No acceptance.py change
- No new dependency
- No PDF for v1 assets
- No cross-machine byte-equality
- No 360px thumbnail / contrast gating
- No re-layout of PDF pages

#### ✓ New Fixture Under Version Control

§2 specifies: `tools/marketing-render/tests/inputs/fmt-multi/formats.md` — a new 3-slide renderer-input fixture (under `tests/inputs/`, not `fixtures/`, so it doesn't affect `acceptance.py`'s 12-fixture set). Used to prove page-count > 1. Illustrative/public copy, no TERREM DB numbers. PNG/PDF not committed (rendered to temp dir in tests).

#### ✓ Definition of Done (9 Measurable Criteria)

§10 provides Evaluator-verifiable conditions:
1. v2 asset emits carousel.pdf with correct page-count/order + manifest `pdf` key
2. PDF byte-identical cross-process + no per-run metadata
3. fmt-multi 3 slides → 3 pages
4. v1 freeze: hyd/tgrera emit no PDF, byte-identical re-render
5. Atomicity: 11-slide fails with no render/ dir
6. validate.py tolerates pdf key without edit
7. Conscious regression: two re-pointed tests
8. Test suite counts (render >252, loop 254), no new deps, no-network import
9. generator_trace.log records evidence path and risks

---

## Conclusion

This contract is **exceptionally well-written**. Every requirement is specific and testable. The evidence standard (cross-process on-disk `cmp`, not BytesIO round-trip) prevents the most common fake-determinism shortcut. The regression-budget transparency (named line numbers, preserved v1 guarantees, explicit "extension not deletion") sets a high bar for handling breaking changes in frozen test suites.

**No ambiguity. No gaps. No gameable claims.**
