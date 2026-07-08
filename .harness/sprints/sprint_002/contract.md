# Sprint 002 Contract — Format Templates Batch A (BIG-NUMBER, RECEIPTS, CHECKLIST) + manifest v2 emission

Run 003 · Renderer V2 Format Library + QA Gate V2
Spec refs: §5.1 (R10, R11, R12, R13, R14, R18, R19), §5.3 (manifest v2), §9 (tokens/fonts/no-network), §10 Risk 1/3/6/7, §11 Sprint-002 row.
Builds on: Sprint 001 (measure.py v2 pure functions + widened `_validate_manifest_schema`), evaluated PASS (findings.md, incl. F-001 forward-carry).

---

## 0. One-paragraph scope

This sprint makes the renderer **draw the first three v2 format-slide templates** — `BIG-NUMBER`, `RECEIPTS`, `CHECKLIST` — each at **1080×1350**, each with exactly one `dominant` element rendered at ≥3× the body reference, raised type floors, and an on-card `TERREM` wordmark, and emits a **schema_version "2"** `manifest.json` describing them (spec §5.3). It adds a new human-authorable input grammar `formats.md` (Risk 7: the Generator's to design; the manifest is the normative seam). It renders **no PDF** (Sprint 004), wires **no** V13–V19 QA check into `run_checks` (Sprint 005), and does **not** touch `acceptance.py` or the TGRERA asset (Sprint 006). The v1 path (`carousel.md` 1080×1350 carousel-slides, `chart-spec.md` 1080×1920 chart-card) stays **byte-frozen**: an asset with no `formats.md` produces exactly the bytes it does today.

**One contract-forced deviation from the §11 sprint plan, stated up front (discharges Sprint-001 F-001):** the moment this sprint writes a `schema_version "2"` manifest to disk, F-001's "unreachable" premise dies — a hostile Evaluator can now run `validate.py` against a v2 asset and, with V13–V19 unwired, hit an uncaught `ValueError` (spec §6 "invalid input → no crash" violation). F-001's own required-fix pre-authorises the remedy: **"add an early exit-2 guard."** This sprint therefore adds a **minimal, additive** guard in `validate.py` so that encountering a `format-slide` surface produces a **clean exit-2 with a cited message**, never a traceback. The guard **cannot fire** on any v1 fixture or on hyd/tgrera (they carry no format-slide surface). Sprint 005 supersedes it with the real V13–V19 verdict. This is conscious seam management, not scope creep.

Playwright is **not applicable** — no browser UI. This is a CLI/raster sprint. The Evaluator attacks it by **rendering real PNGs, measuring pixels/canvas, hashing decoded-RGBA bytes, feeding violating `formats.md` fixtures, and running the full unittest suites** (§7–§8), not click paths.

---

## 1. Exact user-visible behaviors

The "user" is a content operator (or `/loop-create` agent) who authors `content/<slug>/formats.md` and runs one command to get 1080×1350 format PNGs + a v2 manifest.

### 1.1 New input grammar — `formats.md` (Generator's design, Risk 7)

Modeled on the existing `carousel.md` `**S<n> …**` header grammar. One block per format-slide, in file order:

```
**F1 BIG-NUMBER**
Context: Premium resale, Gachibowli
Dominant: ₹14.95L
So-what: Check the RERA number before you pay → intel.terrem.in
Wordmark

**F2 RECEIPTS**
Headline: Three projects, one freeze
Dominant: SALES FROZEN
Chip: ₹14.95L · R Homes · Jun 22
Chip: +10.7% · Sky Villas · Jun 27
Wordmark

**F3 CHECKLIST**
Dominant: 3
Context: checks before you pay
Step: 1 · RERA registration number is live on the state portal
Step: 2 · Approved plan matches the built floors
Step: 3 · No pending regulator order against the builder
So-what: Verify free → intel.terrem.in
Wordmark
```

**Header:** `**F<n> <FORMAT>**` where `<FORMAT> ∈ {BIG-NUMBER, RECEIPTS, CHECKLIST}` for this sprint (the other four are Sprint 003). An unknown format tag in the header → **fail-loud `ValueError`** naming the slide + tag.

**Directive → element-role mapping (fixed):**

| Directive | element `role` | rendered as |
|---|---|---|
| `Dominant:` | `dominant` | the single hook figure (accent), one per content slide |
| `Context:` | `headline` | one-line context/eyebrow above/below the dominant |
| `Headline:` | `headline` | eyebrow/title line |
| `Body:` | `body` | supporting line |
| `Chip:` | `body` | body text drawn inside a bordered chip (RECEIPTS) |
| `Step:` | `body` | numbered utility step (CHECKLIST) |
| `So-what:` | `so-what` | stand-alone utility line (typically a TERREM link) |
| `Source:` | `source-stamp` | source line (full text) |
| `Wordmark` (bare) | `wordmark` | literal `TERREM`, bottom-right |

An unrecognized non-empty line → **fail-loud `ValueError`** naming slide + line (matches `carousel.md` behavior).

### 1.2 Per-format required-role rules (enforced at parse/render, fail-loud)

Every **content** format-slide MUST declare **exactly one** `dominant` and **exactly one** `wordmark`. Per-format minima:

- **BIG-NUMBER:** exactly 1 `dominant`; ≥1 `headline` (context); `so-what` optional; exactly 1 `wordmark`.
- **RECEIPTS:** exactly 1 `dominant`; **2–4** `Chip:` (body) elements; `headline` optional; exactly 1 `wordmark`. Fewer than 2 or more than 4 chips → `ValueError`.
- **CHECKLIST:** exactly 1 `dominant` (the index numeral); **≥2** `Step:` (body) elements; `context`/`so-what` optional; exactly 1 `wordmark`.

Violations (0 or ≥2 dominants, 0 wordmarks, chip/step counts out of range) are **fail-loud render errors with no partial write** (spec §6, R19 atomic emission).

### 1.3 Locked v2 style constants (new — v1 constants untouched)

New module-level constants in `render.py` (the v1 `_HOOK/_HEADLINE/_BODY/_SOURCE/_WORDMARK` and all `_CC_*` constants stay **byte-unchanged**, spec §10 Risk 1):

| role | font_px | weight | color token | floor (V14) | check |
|---|---|---|---|---|---|
| `dominant` | **132** | 700 | `accent` `#0f766e` | ≥48 (V14) / ≥3×body (V13) | 132/30 = **4.40 ≥ 3** ✓ |
| `headline` | **52** | 700 | `ink` `#1c1917` | ≥48 | 52 ≥ 48 ✓ |
| `body` | **30** | 500 | `ink-muted` `#57534e` | ≥26 | 30 ≥ 26 ✓ |
| `so-what` | **30** | 500 | `ink-muted` `#57534e` | ≥26 | 30 ≥ 26 ✓ |
| `source-stamp` | **26** | 400 | `ink-muted` `#57534e` | ≥24 | 26 ≥ 24 ✓ |
| `wordmark` | **26** | 700 | `accent-deep` `#0d3d38` | exempt | — |

**Ratio invariant (provable by inspection):** all `body`-role elements (incl. `Chip:` and `Step:`, which emphasize by **weight**, not size) render at exactly **30px**, so `body_reference = max(body font_px) = 30` on every content slide. `dominant = 132` → `dominant_ratio_ok` returns `ratio = 132/30 = 4.4 ≥ 3.0` → **pass** for all three formats. The RECEIPTS chip amounts are visually stronger via weight-700 rendering **inside the bordered chip**, never via a larger `font_px`, so `body_reference` is fixed at 30 by construction.

**One-accent discipline (spec §7):** the single `accent` (`#0f766e`) use per surface is the `dominant`. `headline` is `ink`, `body`/`so-what`/`source-stamp` are `ink-muted`. `wordmark` is `accent-deep` — the brand-locked wordmark color (R13), matching the frozen v1 wordmark; not a second "accent" use.

### 1.4 Visual grammar per format (exact pixel coords are the Generator's, deterministic)

- **BIG-NUMBER:** vertical stack centered in the content band — context (`headline`) line, the `dominant` number (dominant visual mass), optional `so-what` line below; `wordmark` bottom-right. No decorative marks.
- **RECEIPTS:** optional `headline` eyebrow at top; the `dominant` lead consequence; **2–4 bordered chips** below — each chip is a **decorative rounded/plain rectangle drawn with the `--border` token `#e0dbd3` (1px stroke) filled with `--surface` `#ffffff`**, containing its `Chip:` body text (weight 700). **Chip borders/fills are decorative primitives only — they are NOT manifest elements** (no fake element rows); only the text inside each chip is a `body` element in the manifest. `wordmark` bottom-right.
- **CHECKLIST:** the `dominant` index numeral (e.g. `3`) with an optional `context` line beside/under it; the numbered `Step:` body lines stacked; optional `so-what`; `wordmark` bottom-right. Step numbers are part of the authored `Step:` text (no separate numeral element).

All text uses vendored Inter only, the anti-tofu glyph guard runs on every element every render (R18, reused from v1 `_assert_glyphs`), and overflow beyond the safe band is a **fail-loud** `ValueError` (no silent clipping), reusing the v1 band-overflow pattern.

### 1.5 R14 — ≤10 slides (fail-loud at render)

A `formats.md` declaring **≥11** format-slides is a **fail-loud render error naming the count**, with **no partial write** (spec §5.1 R14, §6). (The QA-time V18 twin is Sprint 005; the render-time fail-loud lives here because this sprint owns the format-slide renderer.)

### 1.6 manifest.json — schema v2 emission (spec §5.3)

When an asset carries a `formats.md`, `render_asset` emits `schema_version "2"`. Each format-slide surface:

```json
{
  "id": "format-01",
  "role": "format-slide",
  "format": "BIG-NUMBER",
  "png": "format-01.png",
  "canvas": { "w": 1080, "h": 1350 },
  "has_axis": false,
  "elements": [
    { "text": "₹14.95L", "role": "dominant", "font_px": 132, "weight": 700,
      "color": "#0f766e", "bg": "#faf8f3", "bbox": [x, y, w, h] },
    { "text": "Premium resale, Gachibowli", "role": "headline", "font_px": 52, "weight": 700,
      "color": "#1c1917", "bg": "#faf8f3", "bbox": [x, y, w, h] },
    { "text": "TERREM", "role": "wordmark", "font_px": 26, "weight": 700,
      "color": "#0d3d38", "bg": "#faf8f3", "bbox": [x, y, w, h] }
  ]
}
```

- Every element carries **all** schema-required fields: `text`, `role`, `font_px`, `weight`, `color`, `bg`, `bbox`. `bg` is the token behind the drawn glyphs (`bg` `#faf8f3`, or `surface` `#ffffff` for text drawn inside a RECEIPTS chip). Both `color` and `bg` are §9 tokens.
- Output PNGs are named `format-01.png … format-NN.png` in slide order (R19); all outputs land under `content/<slug>/render/` only, atomic (no partial write on error).
- `has_axis: false` is emitted on every batch-A format-slide (forward-compat with V10 routing in Sprint 005).
- **No top-level `pdf` key this sprint** (Sprint 004). The Sprint-001 schema tolerates its absence.
- **`schema_version` rule (pinned):** the manifest is `"2"` **iff** it contains ≥1 `format-slide` surface; otherwise `"1"`. Consequence: hyd (`carousel.md`) and tgrera (`chart-spec.md`) — which have no `formats.md` — keep `"1"` and stay **byte-identical**.

### 1.7 validate.py — F-001 exit-2 guard (minimal, additive)

`validate.py` gains a **single guard**: after `_validate_manifest_schema` succeeds, before `run_checks` routes surfaces through the v1 checks, if **any** surface has `role == "format-slide"`, raise `PreconditionError` with a cited message, e.g.:

```
format-slide surfaces require QA Gate V2 (checks V13–V19), not yet wired
(Sprint 005). Re-run validate after the V2 checks land. [PIPELINE-V2.md §4]
```

`main` already maps `PreconditionError` → **exit 2, nothing written**. This turns validate-on-a-v2-asset into a clean, cited exit-2 instead of a traceback (spec §6). The guard:
- **Cannot fire** on any v1 manifest (no format-slide surface) — the 12 fixtures + hyd + tgrera are untouched.
- Lives **downstream** of `_validate_manifest_schema`, so Sprint-001's schema-acceptance tests (which call `_validate_manifest_schema` directly and assert no-raise on a v2 manifest) still pass unchanged.
- Is superseded by real V13–V19 wiring in Sprint 005.

---

## 2. Routes / screens / components affected

No routes/screens (no UI). Files:

- `tools/marketing-render/render.py` — **add** `formats.md` parsing (`parse_formats`), the three format layout+render functions (or a parameterized format renderer), v2 style constants, and schema-v2 manifest emission via a new/extended path in `render_asset`. **v1 code paths unedited** (`parse_carousel`, `render_slide`, `parse_chart_spec`, `render_chart_card`, all v1 style constants).
- `tools/marketing-render/validate.py` — **add** the single §1.7 exit-2 guard. No check logic (`_check_v*`) edited; schema function unedited.
- `tools/marketing-render/tests/test_render_v2.py` — **new** test file for the v2 renderer + determinism + fail-loud states + regression (v1 byte-freeze). Existing test files untouched.
- `tools/marketing-render/tests/test_validate.py` — **add** one test class for the exit-2 guard (existing tests untouched).
- `tools/marketing-render/tests/inputs/fmt-big-number/formats.md`, `…/fmt-receipts/formats.md`, `…/fmt-checklist/formats.md` — **new** renderer-input fixtures (a NEW `tests/inputs/` dir, deliberately **not** under `fixtures/`, so `acceptance.py`'s hard-coded 12-fixture set and `make_fixtures.py` are not perturbed). No committed PNGs — rendered to a temp dir in tests.

**Out of scope (do not touch):** `render.py`'s v1 functions/constants; `measure.py` (Sprint 001 is complete and frozen — call its functions, add none); `acceptance.py`; any `fixtures/*` asset or `make_fixtures.py`; the TGRERA / hyd content assets; PDF emission; V13–V19 check wiring; any file outside `tools/marketing-render/`.

---

## 3. Data / state transitions

- Input: `content/<slug>/formats.md` (authored text). Output: `content/<slug>/render/format-NN.png` + `render/manifest.json`. No DB, no network, no state beyond files.
- `render_asset` builds all images + manifest **in memory**, then `write_outputs` writes them; any parse/layout error raises **before** any file is written (atomic, R19).
- Determinism (R18): identical `formats.md` → **pixel-identical PNGs** (decoded-RGBA SHA-256) and **byte-identical `manifest.json`** across runs. Fonts loaded only from vendored `fonts/` (resolved from `__file__`). Zero network.

---

## 4. Empty / loading / success / error / invalid states

- **Missing asset folder** → `render_asset` raises `FileNotFoundError`, exit 1, nothing written.
- **No renderable input** (no `formats.md`, no `carousel.md`, no chart-card marker) → `FileNotFoundError` naming the requirement, exit 1.
- **Success** → `format-NN.png` + `manifest.json` (schema "2") under `render/`, exit 0, per-file "wrote …" lines.
- **Fail-loud invalid `formats.md`:** unknown format tag, unparseable line, content slide with 0 or ≥2 dominants, missing wordmark, RECEIPTS chip count ∉ [2,4], CHECKLIST steps < 2, ≥11 slides, band overflow, tofu glyph → **`ValueError`/`RuntimeError`**, exit 1, **no partial write**.
- **validate.py on a v2 asset** → clean **exit 2** with the §1.7 cited message, nothing written (no traceback).
- **No loading state** (synchronous CLI).

---

## 5. Keyboard / focus / ARIA / contrast / responsive

- **UI a11y:** N/A — no DOM/viewport. Stated so the omission is not read as a gap.
- **Raster legibility (the real a11y surface here):** raised type floors are met by construction (§1.3 table). Contrast is not *gated* this sprint (V4 routing for format-slides is Sprint 005), but colors are chosen to pass WCAG for forward-compat: `dominant` accent `#0f766e` (large) and all `ink`/`ink-muted` text on `bg #faf8f3` / `surface #ffffff` clear their ratios. The Evaluator may pre-measure with the existing `contrast_check` but a FAIL there is a Sprint-005 concern, not a Sprint-002 gate.
- **Responsive proxy:** the 360px thumbnail legibility gate (V15) is Sprint 005; not asserted here. This sprint only guarantees the declared floors and the ≥3× dominant ratio.

---

## 6. Security / privacy assumptions

- No network at import-time or render-time. Evaluator may run with network disabled.
- No secrets/tokens/credentials; no `.env`; no DB writes; no writes outside `content/<slug>/render/` (and, in tests, a temp dir).
- No new third-party dependency: stdlib + already-vendored Pillow only. `render.py` gains no import beyond what it already uses.
- Fixture copy is illustrative/public-style (RERA/portal generic guidance) — no TERREM DB numbers (spec §9 provenance-safety). The real TGRERA provenance-checked asset is Sprint 006.

---

## 7. Commands to run (Evaluator)

From repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`:

```bash
# (a) Render the three batch-A format fixtures to a temp dir and inspect.
for f in fmt-big-number fmt-receipts fmt-checklist; do
  cp -R tools/marketing-render/tests/inputs/$f /tmp/$f-a && \
  cp -R tools/marketing-render/tests/inputs/$f /tmp/$f-b && \
  python3 tools/marketing-render/render.py /tmp/$f-a && \
  python3 tools/marketing-render/render.py /tmp/$f-b
done

# (b) Canvas + schema check: every format PNG is 1080x1350; manifest is schema "2".
python3 - <<'PY'
import json, glob
from PIL import Image
for mf in glob.glob('/tmp/fmt-*-a/render/manifest.json'):
    m = json.load(open(mf))
    assert m["schema_version"] == "2", mf
    for s in m["surfaces"]:
        assert s["role"] == "format-slide" and s["canvas"] == {"w":1080,"h":1350}, s["id"]
        im = Image.open(mf.rsplit('/',1)[0] + '/' + s["png"])
        assert im.size == (1080,1350), s["id"]
print("canvas+schema OK")
PY

# (c) Determinism: decoded-RGBA PNGs + manifest bytes identical across the two runs.
python3 - <<'PY'
import hashlib, glob, json
from PIL import Image
def rgba_sha(p):
    return hashlib.sha256(Image.open(p).convert("RGBA").tobytes()).hexdigest()
for a in glob.glob('/tmp/fmt-*-a'):
    b = a[:-2] + '-b'
    for pa in sorted(glob.glob(a + '/render/format-*.png')):
        pb = b + '/render/' + pa.rsplit('/',1)[1]
        assert rgba_sha(pa) == rgba_sha(pb), pa
    assert open(a+'/render/manifest.json','rb').read() == open(b+'/render/manifest.json','rb').read()
print("determinism OK")
PY

# (d) V13/V14 provable against the EMITTED manifest via Sprint-001 measure fns.
python3 - <<'PY'
import sys, json, glob
sys.path.insert(0,'tools/marketing-render'); import measure
for mf in glob.glob('/tmp/fmt-*-a/render/manifest.json'):
    for s in json.load(open(mf))["surfaces"]:
        els = s["elements"]
        r = measure.dominant_ratio_ok(els)
        assert r["passes"] and (r["exempt"] or r["ratio"] >= 3.0), (s["id"], r)
        assert sum(1 for e in els if e["role"]=="wordmark") == 1, s["id"]
        for e in els:
            if e["role"] != "wordmark":
                assert measure.format_slide_type_min(e["role"], e["font_px"])["passes"], (s["id"], e["role"], e["font_px"])
print("V13/V14 (measure) OK")
PY

# (e) validate.py on a v2 asset -> clean exit 2, cited message, NO traceback (F-001 discharge).
python3 tools/marketing-render/validate.py /tmp/fmt-big-number-a; echo "exit=$?"

# (f) Regression: hyd + tgrera stay schema "1" and byte-identical after re-render.
python3 tools/marketing-render/render.py content/2026-07-03-hyd-premium-vs-budget
python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave
git -C /Users/prithviputta/Downloads/terrem-marketing-loops status --porcelain content/  # expect no diff to committed renders

# (g) Full suites — render count MUST rise above 182 and stay OK; loop stays 254 OK.
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"
python3 -m unittest discover -s tools/marketing-loops/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"

# (h) No-network import sanity.
python3 -c "import sys; sys.path.insert(0,'tools/marketing-render'); import render, validate, measure; print('import-ok')"
```

**Baseline (from Sprint-001 findings, confirmed before this sprint in generator_trace.log):** render suite `Ran 182 … OK`; loop suite `Ran 254 … OK`. After this sprint: render count **> 182** and `OK`; loop **254 … OK** (loop suite does not import render/validate/measure).

---

## 8. Adversarial matrix the Evaluator should run (replaces Playwright click paths)

Each row is a distinct, isolable attack; the Generator ships each as a unit test too.

| # | Attack | Expected result |
|---|---|---|
| 1 | Render `fmt-big-number` | PNG **1080×1350**; surface `role=format-slide`, `format=BIG-NUMBER`, `schema_version="2"` |
| 2 | Render `fmt-receipts` | 1080×1350; `format=RECEIPTS`; 2–4 body chips present; bordered-chip pixels drawn with `--border`/`--surface` (NOT manifest elements) |
| 3 | Render `fmt-checklist` | 1080×1350; `format=CHECKLIST`; ≥2 step body elements; one dominant numeral |
| 4 | `measure.dominant_ratio_ok(surface.elements)` on every content slide | `passes True`, `ratio = 132/30 = 4.4 ≥ 3.0`, exactly one dominant |
| 5 | `measure.format_slide_type_min(role,font_px)` for every non-wordmark element | `passes True` (body 30, so-what 30, source 26, headline 52) |
| 6 | Count `wordmark` elements per format-slide | exactly **1** each (R13) |
| 7 | `_validate_manifest_schema` on an emitted v2 manifest | **no raise** (structurally valid) |
| 8 | Re-render each fixture; compare decoded-RGBA PNG bytes + manifest bytes | **identical** (R18) |
| 9 | `formats.md` with **11** slides | fail-loud `ValueError` naming count; **no `render/` written** (R14) |
| 10 | Content slide with **no** `Dominant:` | `ValueError` ("exactly one dominant"), no partial write |
| 11 | Content slide with **two** `Dominant:` | `ValueError` ("exactly one dominant") |
| 12 | Content slide missing `Wordmark` | `ValueError` ("exactly one wordmark") |
| 13 | RECEIPTS with 1 chip / with 5 chips | `ValueError` naming chip-count range [2,4] |
| 14 | CHECKLIST with 1 step | `ValueError` naming step minimum (≥2) |
| 15 | Header `**F1 TIMELINE**` (a Sprint-003 format) | `ValueError` ("unknown/unsupported format tag") — batch A only |
| 16 | Unparseable line inside a block | `ValueError` naming slide + line |
| 17 | `validate.py <v2-asset>` | **exit 2**, cited `format-slide … Sprint 005` message, **no traceback**, nothing written (F-001) |
| 18 | `validate.py` on any of the 12 v1 fixtures + hyd + tgrera | **unchanged verdicts** — guard does not fire |
| 19 | Re-render hyd + tgrera | `manifest.json` stays `schema_version "1"`, **byte-identical**; PNGs decoded-RGBA identical |
| 20 | Every emitted `color`/`bg` | is one of the nine §9 tokens |
| 21 | Anti-tofu: a format element with a real glyph | renders (no false tofu); guard runs every render |
| 22 | Render suite / loop suite | render `Ran N>182 … OK`; loop `Ran 254 … OK` |
| 23 | `import render, validate, measure` with network off | `import-ok` |

**Freeze invariant (must hold):** rows 18–19 + 22 prove the v1 renderer/validator behavior is byte-for-byte preserved; no previously-passing artifact changes.

---

## 9. Explicit non-goals (Sprint 002)

- **No PDF.** `carousel.pdf` and the top-level `pdf` manifest key are Sprint 004.
- **No V13–V19 QA wiring.** No `_check_v*` added; format-slides are not scored — only the §1.7 exit-2 guard is added so validate-on-v2 does not crash.
- **No batch-B formats** (TIMELINE, VS-CONTRAST, LEADERBOARD, CHART) — Sprint 003. Their header tags are rejected (row 15).
- **No `acceptance.py` change**, no `fixtures/*` change, no `make_fixtures.py` change, no TGRERA/hyd content edit (the reference asset is Sprint 006).
- **No `measure.py` change** — Sprint 001 is frozen; this sprint only *calls* its functions.
- **No v1 renderer edits** — `parse_carousel`, `render_slide`, `parse_chart_spec`, `render_chart_card`, and all v1 style constants are byte-unchanged.
- **No 360px thumbnail (V15) or contrast (V4) gating** on format-slides — Sprint 005.
- **No new dependency, no network, no writes outside `tools/marketing-render/` + the target `content/<slug>/render/`.**

---

## 10. Definition of done (what the Evaluator can verify on disk)

1. `render.py` renders `BIG-NUMBER`, `RECEIPTS`, `CHECKLIST` format-slides to **1080×1350** PNGs, each with exactly one `dominant` at **132px** (ratio 4.4 ≥ 3 over 30px body), raised floors met, exactly one wordmark, from an authored `formats.md`.
2. `render_asset` emits a `schema_version "2"` `manifest.json` (format-slide surfaces, `format` tag, `dominant`/`so-what` roles, `has_axis:false`, no `pdf` key) that `_validate_manifest_schema` accepts and Sprint-001 `measure` functions confirm V13/V14-clean.
3. Determinism: re-render → decoded-RGBA-identical PNGs + byte-identical manifest (§7c/row 8).
4. Every fail-loud state (§4, rows 9–16) raises with **no partial write**.
5. `validate.py` on a v2 asset exits **2** with a cited message, **no traceback** (F-001 discharged); on all v1 assets its verdicts are **unchanged** (rows 17–18).
6. v1 freeze: hyd + tgrera re-render to `schema_version "1"`, byte-identical manifests + decoded-RGBA-identical PNGs (row 19).
7. Render suite `Ran N>182 … OK`; loop suite `Ran 254 … OK`; no-network import ok.
8. `generator_trace.log` records the 182/254 baseline confirmed **before** code, the files changed, the new-test count, the passing suite output, the v1-freeze evidence, and any disclosed risk (e.g. font-size choices, chip-render approach).

This contract is testable end-to-end by running §7 commands and the §8 matrix. If any row cannot be executed against the shipped code, the contract is not met.
