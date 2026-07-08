# Sprint 004 Contract — Deterministic Multi-Page PDF Emitter (`carousel.pdf`)

Run 004 · Renderer V2 Format Library + QA Gate V2
Spec refs: §5.1 (R15 multi-page PDF, R16 PDF byte-determinism, R18 determinism/no-network, R19 output-location/atomic), §5.3 (top-level `pdf` manifest key), §6 (states), §9 (Python+Pillow+vendored, no new dep, no network), §10 Risk 1 (v1 freeze) / Risk 8 (PDF page-order + metadata suppression), §11 Sprint-004 row.
Builds on: Sprint 001 (measure v2 + widened schema), Sprint 002 (batch-A renderer + `formats.md`), Sprint 003 (batch-B renderer, render suite now **252 OK**), all evaluated PASS.

---

## 0. One-paragraph scope

For every asset that renders **≥1 `format-slide` surface** (i.e. `schema_version "2"`), the renderer additionally emits a single **`content/<slug>/render/carousel.pdf`**: the format-slide PNGs as PDF pages, **one page per format-slide, in slide order**, and records a **top-level `"pdf": "carousel.pdf"`** key in `manifest.json`. The PDF is **byte-identical across two independent `render.py` process invocations of the same input** (R16): per-run PDF metadata (CreationDate, ModDate) is suppressed, the Producer string is fixed, the Title is pinned independent of the output path, and Pillow emits no run-varying document `/ID`. This sprint touches **only `render.py`** (PDF build + manifest key + CLI "wrote" line) and its tests/input-fixtures. It wires **no** V13–V19 QA check, changes **no** `measure.py` / `validate.py` / `acceptance.py` / `fixtures/*`, and edits **no** TGRERA/hyd content asset. The v1 path stays **byte-frozen**: hyd (carousel-slide) and tgrera (chart-card) carry no format-slide, so **no PDF is emitted and no `pdf` key is added** — their `manifest.json` and PNGs stay byte-identical (Risk 1 freeze).

**Conscious regression-budget change, stated up front (spec §9 regression budget; the Sprint-003 PIE-CHART re-point discipline).** Sprint 003 shipped **two** tests named `test_no_pdf_key_this_sprint` (`tools/marketing-render/tests/test_render_v2.py:84` for batch-A fixtures and `:454` for batch-B fixtures), each asserting `assertNotIn("pdf", manifest)`. Emitting the PDF this sprint **legitimately flips both** — a v2 manifest now MUST carry `pdf: "carousel.pdf"`. Under the hard regression budget these two tests are **consciously re-pointed** to assert the **positive** invariant (`manifest["pdf"] == "carousel.pdf"` on a format-slide asset) **and** the preserved negative invariant (a `schema_version "1"` manifest — hyd/tgrera — still has **no** `pdf` key). This is a conscious extension (the "v1 manifests carry no pdf key" guarantee is preserved and re-proven; only the too-early "v2 has no pdf key" assertion moves to its correct post-Sprint-004 value), **never a silent deletion**. No other existing assertion is weakened. `test_validate.py:458 test_top_level_pdf_tolerated` already proves the validator tolerates the `pdf` key — that test is **unchanged** and re-run as a regression witness.

**Determinism scope note (state, do not over-claim).** R16 byte-equality is a **same-environment, same-Pillow-version** guarantee. Pillow writes a fixed comment `created by Pillow <version> PDF driver` into every PDF; that version string is environment-pinned, not a cross-machine promise. The Evaluator runs the byte-equality check on **one machine / one interpreter** (Pillow 11.3.0 present); cross-machine PDF byte-equality is out of scope and not claimed.

Playwright is **not applicable** — no browser UI. This is a CLI/raster sprint. The Evaluator attacks it by rendering real assets across two separate processes, hashing/`cmp`-ing the emitted `carousel.pdf` bytes, counting/ordering PDF pages, confirming the manifest `pdf` key, confirming v1 assets emit no PDF and stay byte-frozen, and running both unittest suites — not click paths.

---

## 1. Exact user-visible behaviors

The "user" is a content operator (or `/loop-create` agent) who authors `content/<slug>/formats.md` and runs one command. Sprint 004 adds one new output file and one manifest key to the existing v2 render.

### 1.1 New output: `carousel.pdf`

- Running `python3 tools/marketing-render/render.py content/<slug>/` on an asset with **≥1 `format-slide`** surface writes, in addition to the existing `format-NN.png`s and `manifest.json`, a **`content/<slug>/render/carousel.pdf`**.
- The CLI prints an additional `wrote …/render/carousel.pdf` line (after the PNG lines, before or after the manifest line — deterministic order the Generator fixes; the manifest line stays last is acceptable).
- **PDF page set + order (R15):** exactly the asset's `format-slide` surfaces, **one page each, in manifest surface-list order** (which is `format-01 … format-NN` slide order, R19). No chart-card or carousel-slide page ever appears in `carousel.pdf`. Page count == number of format-slide surfaces (≤10, R14).
- **PDF page pixels:** each page is the same 1080×1350 raster as its `format-NN.png` (built from the identical in-memory `RGB` image, so the page and the PNG are the same rendered pixels). Default 72 dpi / 72.0 resolution (Pillow default, pinned — no `dpi=`/`resolution=` override that would vary).

### 1.2 New manifest key: top-level `pdf`

- When a `carousel.pdf` is emitted, `manifest.json` carries a **top-level** `"pdf": "carousel.pdf"` key (spec §5.3). Present **iff** `schema_version == "2"` (≥1 format-slide surface). Value is the exact filename string `"carousel.pdf"` (a `render/`-relative name, matching the `png` per-surface convention — a bare filename, not an absolute path).
- A `schema_version "1"` manifest (hyd carousel-slide, tgrera chart-card, all 12 v1 fixtures) carries **no** `pdf` key — byte-unchanged from Sprint 003 (Risk 1 freeze).
- Manifest JSON serialization is unchanged (`json.dumps(..., ensure_ascii=False, indent=2, sort_keys=True) + "\n"`). Because `sort_keys=True`, the new `pdf` key sorts deterministically among the top-level keys (`pdf` between `slug` and `surfaces`… actually alphabetical: `pdf`, `schema_version`, `slug`, `surfaces`) — a single fixed byte-layout across runs.

### 1.3 R16 — PDF byte-determinism (the load-bearing behavior)

`carousel.pdf` MUST be **byte-identical across two independent `render.py` process invocations of the same `formats.md`** on the same environment. The renderer achieves this by, on the Pillow PDF save, explicitly:

- suppressing the per-run **CreationDate** and **ModDate** (Pillow defaults them to `time.gmtime()` — the sole per-run source; passing them as `None`/omitting drops the `/Info` `CreationDate`/`ModDate` entries),
- pinning a **fixed Producer** string (a constant, not run- or environment-derived beyond the version comment Pillow itself writes),
- pinning **Title** to a fixed value **independent of the output filename** (Pillow otherwise derives Title from `os.path.splitext(basename(filename))` — `"carousel"` — which is deterministic per this fixed filename but is pinned explicitly so the bytes do not depend on the save path/method),
- relying on Pillow 11.3.0 emitting **no `/ID` array** in the trailer (verified: `PdfParser.write_xref_and_trailer` writes only `Root`/`Size`/`Info`, no document ID) — so there is no run-varying ID to suppress.

**Evidence standard (must be cross-process, not same-process):** the byte-equality proof renders the same input under **two separate `python3 render.py` invocations into two different parent dirs with an identical basename** (the Sprint-003 `s4a`/`s4b` two-parent slug-identity pattern) and compares the two on-disk `render/carousel.pdf` files with `cmp`/SHA-256. A same-process `BytesIO` round-trip proves only that the encoder is deterministic; it does **not** prove cross-run determinism (the R16 requirement) and does not exercise the real save path (where Title is filename-derived unless pinned).

### 1.4 Atomicity + no-partial-write (R19, inherited)

The PDF is built in memory (or written) only **after** `render_asset` succeeds; any parse/layout error still raises **before** any file (`format-NN.png`, `manifest.json`, or `carousel.pdf`) is written. A ≥11-slide `formats.md` (R14) still fails loud with **no `render/` dir written** — no partial PDF. The Generator may build the PDF bytes in `render_asset` (returned alongside images/manifest) or in `write_outputs` from the in-memory images filtered to format-slide surfaces; either way the "build in memory, then write" invariant holds and no file is written on error.

### 1.5 Which assets get a PDF (exhaustive)

| Asset shape | format-slides? | schema_version | `carousel.pdf` | `pdf` key |
|---|---|---|---|---|
| `formats.md` (v2 batch A/B, 1–10 slides) | ≥1 | "2" | **emitted** | **present** |
| hyd `carousel.md` (carousel-slide) | 0 | "1" | **not emitted** | **absent** |
| tgrera `chart-spec.md` (chart-card) | 0 | "1" | **not emitted** | **absent** |
| 12 v1 `fixtures/*` | 0 | "1" | **not emitted** | **absent** |
| mixed (carousel.md + formats.md in one folder) | ≥1 | "2" | **emitted — only the format-slide pages** | **present** |

The mixed case is not a required fixture but MUST behave as stated (PDF pages = format-slide surfaces only; carousel-slide/chart-card surfaces never enter the PDF). Rule: **PDF emitted iff ≥1 format-slide surface**, exactly the `schema_version == "2"` condition.

---

## 2. Routes / screens / components affected

No routes/screens (no UI). Files:

- `tools/marketing-render/render.py` — **add** a fixed PDF-metadata constant block (producer/title); **build** `carousel.pdf` bytes from the in-memory format-slide `RGB` images in manifest surface-list order with CreationDate/ModDate suppressed + fixed Producer/Title; **add** the top-level `pdf` key to the manifest when a PDF is emitted; **write** `carousel.pdf` in `write_outputs` (atomic, after PNGs/manifest or alongside); **add** its `wrote …` CLI line. **All v1 code paths, batch-A/B `_FMT_*` constants, `render_slide`/`render_chart_card`/`render_format_slide`/layout functions stay byte-unchanged** (only the emission seam gains a PDF).
- `tools/marketing-render/tests/test_render_v2.py` — **consciously re-point** both `test_no_pdf_key_this_sprint` (`:84` batch-A, `:454` batch-B) to assert the **positive** `pdf == "carousel.pdf"` invariant on v2 assets **plus** the preserved **negative** invariant that a `schema_version "1"` manifest has no `pdf` key; **add** PDF test class(es): page-count == slide-count, page order, cross-process byte-determinism, PDF metadata contains no CreationDate/ModDate, v1 asset emits no PDF, manifest `pdf` key presence/absence. No existing assertion weakened or deleted beyond the two documented re-points.
- `tools/marketing-render/tests/inputs/fmt-multi/formats.md` — **new** multi-slide (**3** format-slide) renderer-input fixture, so page-count/order is provable against a >1-page PDF (existing single-format fixtures give 1-page PDFs only). Illustrative/public copy, no TERREM DB numbers. Under `tests/inputs/` (NOT `fixtures/`, so `acceptance.py`'s 12-fixture set is untouched); no committed PDF/PNG — rendered to a temp dir in tests and by the Evaluator.

**Out of scope (do not touch):** `render.py` v1 functions/constants + batch-A/B `_FMT_*` constants (byte-unchanged except the new PDF emission seam); `measure.py` (frozen); `validate.py` (schema already tolerates the `pdf` key — `test_top_level_pdf_tolerated` proves it; F-001 guard unchanged); `acceptance.py`; any `fixtures/*` or `make_fixtures.py`; TGRERA/hyd content assets; V13–V19 wiring; V15 thumbnail / V4 contrast gating; any file outside `tools/marketing-render/`.

---

## 3. Data / state transitions

- Input: `content/<slug>/formats.md`. Output (v2): `render/format-NN.png` × N + `render/manifest.json` (with `pdf` key) + **`render/carousel.pdf`**. No DB, no network, no state beyond files.
- `render_asset` builds all images + manifest in memory; PDF bytes derive from the same in-memory images; `write_outputs` writes PNGs, manifest, and (when present) the PDF into `render/` only; any error raises before any write (atomic, R19).
- **Determinism (R18 + R16):** identical `formats.md` → pixel-identical PNGs (decoded-RGBA SHA-256), byte-identical `manifest.json`, **and byte-identical `carousel.pdf`** across two independent process runs. No embedded per-run timestamp/ID; fixed Producer/Title; images encoded from deterministic RGB pixel data (proven: same-input PDF bytes equal). Fonts loaded only from vendored `fonts/`; zero network.

---

## 4. Empty / loading / success / error / invalid states

- **Missing asset folder / no renderable input** → `FileNotFoundError`, exit 1, nothing written (no PDF). Unchanged.
- **Success (v2)** → `format-NN.png` × N + `manifest.json` (schema "2", with `pdf`) + `carousel.pdf` under `render/`, exit 0, per-file "wrote …" lines including the PDF.
- **Success (v1)** → hyd/tgrera/fixtures render exactly as Sprint 003: PNGs + `manifest.json` (schema "1", **no** `pdf` key), **no** `carousel.pdf`, exit 0.
- **Fail-loud invalid `formats.md`** (unknown tag, unparseable line, wrong dominant/wordmark count, per-format minima, `Bar:` no-numeric, **≥11 slides**, band overflow, tofu glyph) → `ValueError`/`RuntimeError`, exit 1, **no partial write — no `render/` dir, no PDF** (R19 atomic). Unchanged, now also proven to leave no partial PDF.
- **validate.py on a v2 asset (now carrying the `pdf` key)** → still clean **exit 2** with the inherited cited "V13–V19 not yet wired" message, **no traceback**, nothing written; the `pdf` key is tolerated by the schema check (`test_top_level_pdf_tolerated`, unchanged). No validate.py edit.
- **No loading state** (synchronous CLI).

---

## 5. Keyboard / focus / ARIA / contrast / responsive

- **UI a11y:** N/A — no DOM/viewport. Stated so the omission is not read as a gap.
- **Raster/PDF legibility:** PDF pages are the identical 1080×1350 rendered slides (raised floors + ≥3× dominant already met by construction, Sprints 002/003). PDF is a re-container of the same pixels — it introduces no new legibility surface. V15 thumbnail / V4 contrast gating remains Sprint 005.
- **Responsive proxy:** unchanged from Sprint 003; the 360px thumbnail gate is Sprint 005.

---

## 6. Security / privacy assumptions

- No network at import- or render-time. Evaluator may run with network disabled.
- No secrets/tokens/credentials; no `.env`; no DB writes; no writes outside `content/<slug>/render/` (and, in tests, a temp dir).
- **No new third-party dependency:** PDF via already-vendored Pillow's `Image.save(..., format="PDF", save_all=True, append_images=…)`. `render.py` gains **no import beyond what it already uses** (Pillow's PDF driver is part of the existing Pillow; no `reportlab`/`fpdf`/etc.).
- New multi-slide fixture copy is illustrative/public-style — no TERREM DB numbers (spec §9). Provenance-checked TGRERA is Sprint 006.
- `.gitignore` hygiene: no `carousel.pdf` / `render/` artifact committed by this sprint (outputs are regenerated; tests use temp dirs).

---

## 7. Commands to run (Evaluator)

From repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`:

```bash
# (a) BASELINE re-confirm BEFORE reading Sprint-004 code changes.
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"   # expect Ran 252 ... OK (pre-004 baseline)
python3 -m unittest discover -s tools/marketing-loops/tests   2>&1 | grep -E "^(Ran|OK|FAILED)"   # expect Ran 254 ... OK

# (b) Cross-process PDF byte-determinism (R16) — TWO separate render.py invocations,
#     identical basename in two parents (slug-identity), compare on-disk carousel.pdf bytes.
rm -rf /tmp/s4a /tmp/s4b
for f in fmt-multi fmt-chart fmt-receipts; do
  mkdir -p /tmp/s4a/$f /tmp/s4b/$f
  cp tools/marketing-render/tests/inputs/$f/formats.md /tmp/s4a/$f/
  cp tools/marketing-render/tests/inputs/$f/formats.md /tmp/s4b/$f/
  python3 tools/marketing-render/render.py /tmp/s4a/$f >/dev/null
  python3 tools/marketing-render/render.py /tmp/s4b/$f >/dev/null
  cmp /tmp/s4a/$f/render/carousel.pdf /tmp/s4b/$f/render/carousel.pdf && echo "PDF byte-identical: $f"
done

# (c) Page count == slide count, pages in slide order, manifest pdf key.
python3 - <<'PY'
import json, glob
from PIL import Image
for mf in glob.glob('/tmp/s4a/fmt-*/render/manifest.json'):
    m = json.load(open(mf)); d = mf.rsplit('/',1)[0]
    fs = [s for s in m["surfaces"] if s["role"]=="format-slide"]
    assert m["schema_version"]=="2", mf
    assert m.get("pdf")=="carousel.pdf", ("missing/wrong pdf key", mf, m.get("pdf"))
    pdf = Image.open(d + '/carousel.pdf')
    pages = getattr(pdf, "n_frames", 1)
    assert pages == len(fs), ("page count != slide count", mf, pages, len(fs))
    # order: each page is 1080x1350 (all format-slides are)
    for i in range(pages):
        pdf.seek(i); assert pdf.size == (1080,1350), (mf, i, pdf.size)
    print("pages OK:", d.split('/')[-2], pages)
PY

# (d) Multi-page proof (fmt-multi has 3 slides -> 3 PDF pages).
python3 - <<'PY'
from PIL import Image
p = Image.open('/tmp/s4a/fmt-multi/render/carousel.pdf')
assert getattr(p,"n_frames",1)==3, p.n_frames
print("fmt-multi pages:", p.n_frames)
PY

# (e) No per-run metadata in the PDF bytes (CreationDate/ModDate suppressed).
python3 - <<'PY'
b = open('/tmp/s4a/fmt-multi/render/carousel.pdf','rb').read()
assert b"CreationDate" not in b, "CreationDate leaked (non-deterministic)"
assert b"ModDate" not in b, "ModDate leaked (non-deterministic)"
assert b"/ID" not in b, "run-varying document /ID present"
assert b"%PDF" in b[:8], "not a PDF"
print("no per-run metadata OK; has fixed Pillow producer comment:", b"created by Pillow" in b)
PY

# (f) v1 FREEZE: hyd + tgrera emit NO carousel.pdf, NO pdf key, byte-identical after re-render.
python3 tools/marketing-render/render.py content/2026-07-03-hyd-premium-vs-budget >/dev/null
python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave >/dev/null
test ! -e content/2026-07-03-hyd-premium-vs-budget/render/carousel.pdf && echo "hyd: no PDF OK"
test ! -e content/2026-07-03-tgrera-enforcement-wave/render/carousel.pdf && echo "tgrera: no PDF OK"
python3 - <<'PY'
import json
for slug in ("2026-07-03-hyd-premium-vs-budget","2026-07-03-tgrera-enforcement-wave"):
    m = json.load(open(f'content/{slug}/render/manifest.json'))
    assert m["schema_version"]=="1" and "pdf" not in m, (slug, m.get("pdf"))
print("v1 manifests schema 1, no pdf key OK")
PY
git -C /Users/prithviputta/Downloads/terrem-marketing-loops status --porcelain content/   # expect empty (no diff)

# (g) validate.py on a v2 asset (now with pdf key) -> clean exit 2, cited, no traceback.
python3 tools/marketing-render/validate.py /tmp/s4a/fmt-multi; echo "exit=$?"   # expect exit 2, cited msg

# (h) Atomic: an 11-slide formats.md fails loud, leaves NO render/ dir (no partial PDF).
mkdir -p /tmp/s4over/asset
python3 - <<'PY'
lines=[]
for i in range(1,12):
    lines += [f"**F{i} BIG-NUMBER**","Dominant: 42","Body: ctx","So-what: x","Wordmark",""]
open('/tmp/s4over/asset/formats.md','w').write("\n".join(lines))
PY
python3 tools/marketing-render/render.py /tmp/s4over/asset; echo "exit=$?"   # expect exit 1
test ! -e /tmp/s4over/asset/render && echo "no partial render/ dir OK"

# (i) Full suites — render count MUST rise above 252 and stay OK; loop stays 254 OK.
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"
python3 -m unittest discover -s tools/marketing-loops/tests   2>&1 | grep -E "^(Ran|OK|FAILED)"

# (j) No-network import sanity.
python3 -c "import sys; sys.path.insert(0,'tools/marketing-render'); import render, validate, measure; print('import-ok')"
```

**Baseline (re-confirmed in generator_trace.log BEFORE code):** render `Ran 252 … OK`; loop `Ran 254 … OK`. After this sprint: render count **> 252** and `OK`; loop **254 … OK**.

---

## 8. Adversarial matrix (replaces Playwright click paths)

Each row is a distinct, isolable attack; the Generator ships each as a unit test too.

| # | Attack | Expected result |
|---|---|---|
| 1 | Render any v2 fixture; look for `render/carousel.pdf` | file exists, starts `%PDF` |
| 2 | Render `fmt-multi` (3 slides); count PDF pages (`n_frames`) | **3** pages |
| 3 | PDF page count vs format-slide count for every v2 fixture | equal |
| 4 | PDF page order | page *i* == `format-0(i+1).png` slide order; every page 1080×1350 |
| 5 | Cross-process re-render (`s4a` vs `s4b`), `cmp carousel.pdf` | **byte-identical** (R16) — same env |
| 6 | Same-input single-process re-render | byte-identical (encoder determinism, subset of #5) |
| 7 | grep PDF bytes for `CreationDate` / `ModDate` | **absent** (per-run metadata suppressed) |
| 8 | grep PDF bytes for `/ID` | **absent** (no run-varying document ID) |
| 9 | grep PDF bytes for fixed producer comment | `created by Pillow …` present (fixed per env) |
| 10 | manifest top-level `pdf` on a v2 asset | `== "carousel.pdf"` |
| 11 | manifest top-level `pdf` on hyd/tgrera/v1 fixtures | **absent** (`"pdf" not in manifest`) |
| 12 | hyd + tgrera re-render → `render/carousel.pdf` | **not created** (v1 emits no PDF) |
| 13 | hyd + tgrera `manifest.json` + PNG bytes after re-render | **byte-identical** (`git status --porcelain content/` empty) — freeze holds |
| 14 | `_validate_manifest_schema` / `validate.py` on a v2 asset carrying the `pdf` key | tolerated → clean **exit 2** cited, no traceback (`test_top_level_pdf_tolerated` unchanged) |
| 15 | 11-slide `formats.md` | fail-loud `ValueError`, exit 1, **no `render/` dir**, no partial PDF (R14/R19) |
| 16 | Mixed carousel.md + formats.md folder | PDF pages = format-slide surfaces only (no carousel-slide page); `pdf` key present |
| 17 | The two re-pointed `test_no_pdf_key_this_sprint` | now assert positive `pdf` presence on v2 + preserved absence on v1 (conscious flip, §0) |
| 18 | Render suite / loop suite | render `Ran N>252 … OK`; loop `Ran 254 … OK` |
| 19 | `import render, validate, measure` network-off | `import-ok` |
| 20 | `render.py` imports — no new third-party dep | only stdlib + already-vendored Pillow (PDF driver in-Pillow); no `reportlab`/`fpdf` |

**Freeze invariant (must hold):** rows 11–14 + 18 prove v1 renderer/validator behavior is byte-for-byte preserved and batch-A/B PNG behavior unchanged; the only previously-passing assertions that change are the two consciously re-pointed `test_no_pdf_key_this_sprint` tests (row 17), which preserve the "v1 manifests carry no pdf key" guarantee.

---

## 9. Explicit non-goals (Sprint 004)

- **No V13–V19 QA wiring.** No `_check_v*` added; validate.py's F-001 exit-2 guard still fires on v2 assets.
- **No `measure.py` change** — frozen; not even called by the PDF path.
- **No `validate.py` change** — schema already tolerates the top-level `pdf` key (`test_top_level_pdf_tolerated`); F-001 guard unchanged.
- **No `acceptance.py` change**, no `fixtures/*` change, no `make_fixtures.py` change, no TGRERA/hyd content edit (TGRERA carousel + PDF + its acceptance baseline are Sprint 006).
- **No new dependency** — PDF via already-vendored Pillow only; no `reportlab`/`fpdf`/`weasyprint`.
- **No PDF for v1 assets** — carousel-slide/chart-card assets emit no `carousel.pdf` and gain no `pdf` key (freeze).
- **No cross-machine / cross-Pillow-version PDF byte-equality claim** — R16 is same-environment (§0 note).
- **No 360px thumbnail (V15) / contrast (V4) gating**, no publisher, no network, no writes outside `tools/marketing-render/` + the target `content/<slug>/render/`.
- **No re-layout / re-encode of PDF pages** — pages are the exact rendered 1080×1350 slide rasters, not re-scaled or re-flowed.

---

## 10. Definition of done (Evaluator-verifiable on disk)

1. Rendering a v2 (`formats.md`) asset emits `content/<slug>/render/carousel.pdf` — one page per format-slide, in slide order, each page 1080×1350 — plus a top-level `"pdf": "carousel.pdf"` manifest key (§7 b/c/d, rows 1–4, 10).
2. `carousel.pdf` is **byte-identical across two independent `render.py` process runs** of the same input on the same env; PDF bytes contain **no** `CreationDate`/`ModDate`/`/ID` and a fixed Producer/Title (§7 b/e, rows 5–9). Proof is cross-process on-disk `cmp`, not same-process BytesIO.
3. `fmt-multi` (new 3-slide fixture) yields a 3-page PDF, proving page-count == slide-count on >1 page (§7 d, row 2).
4. **v1 freeze:** hyd + tgrera + 12 fixtures emit **no** `carousel.pdf` and **no** `pdf` key; hyd/tgrera `manifest.json` + PNGs re-render byte-identical (`git status --porcelain content/` empty) (§7 f, rows 11–13).
5. Atomic: an 11-slide `formats.md` fails loud (exit 1) leaving **no `render/` dir** and no partial PDF (§7 h, row 15).
6. `validate.py` on a v2 asset carrying the `pdf` key exits **2** cited, **no traceback** — no validate.py edit; `test_top_level_pdf_tolerated` unchanged (§7 g, row 14).
7. The conscious regression change is exactly the two re-pointed `test_no_pdf_key_this_sprint` tests (batch-A `:84`, batch-B `:454`) → positive `pdf`-present on v2 + preserved `pdf`-absent on v1; no other assertion weakened (§0, row 17).
8. Render suite `Ran N>252 … OK`; loop suite `Ran 254 … OK`; no new third-party dependency; no-network import ok (§7 i/j, rows 18–20).
9. `generator_trace.log` records: the 252/254 baseline re-confirmed **before** code, files changed, new-test count, the two-test conscious re-point justification, the freeze evidence (hyd/tgrera no-PDF + byte-identical), the cross-process PDF byte-equality evidence path, and disclosed risks (env-pinned Pillow producer comment; Title pinned independent of save path; mixed-asset page-set rule).

This contract is testable end-to-end by running §7 commands and the §8 matrix. If any row cannot be executed against the shipped code, the contract is not met.
