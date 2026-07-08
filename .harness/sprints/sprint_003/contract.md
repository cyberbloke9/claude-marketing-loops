# Sprint 003 Contract — Format Templates Batch B (TIMELINE, VS-CONTRAST, LEADERBOARD, CHART) + manifest v2

Run 003 · Renderer V2 Format Library + QA Gate V2
Spec refs: §5.1 (R10, R11, R12, R13, R14, R18, R19 + the CHART/TIMELINE/VS-CONTRAST/LEADERBOARD grammar rows), §5.3 (manifest v2), §7 (Tufte-clean CHART / one-accent), §9 (tokens/fonts/no-network), §10 Risk 1/3/6/7, §11 Sprint-003 row.
Builds on: Sprint 001 (measure.py v2 pure fns + widened schema) and Sprint 002 (batch-A renderer + `formats.md` grammar + F-001 exit-2 guard), both evaluated PASS.

---

## 0. One-paragraph scope

This sprint makes the renderer **draw the remaining four v2 format-slide templates** — `TIMELINE`, `VS-CONTRAST`, `LEADERBOARD`, `CHART` — each at **1080×1350**, each with exactly one `dominant` element rendered at ≥3× the body reference, the raised v2 type floors, and an on-card `TERREM` wordmark, and emits them into the existing **schema_version "2"** `manifest.json` alongside the batch-A formats. It extends the `formats.md` grammar (Sprint-002 design, Risk 7) with three directives (`Event:`, `Row:`, `Bar:`) and one new element role (`chart-label`, already schema- and floor-accepted from Sprint 001). The **CHART** format draws genuine, zero-based, direct-labeled data bars (decorative primitives, like RECEIPTS chips — NOT manifest elements) so it is a real chart, not an inert text card (spec §7 "data becomes the picture / no inert text-only cards"). It renders **no PDF** (Sprint 004), wires **no** V13–V19 QA check (Sprint 005), and does **not** touch `acceptance.py`, `measure.py`, `fixtures/*`, or the TGRERA/hyd assets (Sprint 006). The v1 path stays **byte-frozen**.

**One conscious regression-budget change, stated up front (spec §9 regression budget; §10 Risk-1-style discipline):** Sprint 002 shipped `test_render_v2.py::test_unknown_format_tag_fail_loud`, which asserts `**F1 TIMELINE**` is rejected as an unknown tag. Enabling batch-B tags **legitimately flips that assertion** — TIMELINE now renders. Under the hard regression budget this test is **consciously re-pointed** at a genuinely bogus tag (e.g. `PIE-CHART`) that still fails loud, and a new positive assertion is added that TIMELINE/VS-CONTRAST/LEADERBOARD/CHART now render. This is a conscious extension (the "unknown tag fails loud" behavior is preserved and re-proven; only the example tag moves), **never a silent deletion**. No other existing assertion is weakened. `test_measure.py` / `test_validate.py` references to the batch-B tag names are unaffected (they test the meta-block parser and schema-tag acceptance, which already treated all 7 tags as valid).

**`has_axis:true` is an explicit non-goal this sprint (§9).** CHART renders **zero-based, direct-labeled proportional bars with `has_axis:false`**. The disclosed-axis-break / truncated-axis V10 path is attacked in Sprint 005 via **hand-authored static manifests** (exactly as the v1 `fx-truncated-axis` fixture is — the v1 renderer itself rejects `has_axis:true` fail-loud at render.py:343, yet the fixture exists as a committed manifest). So a plotted numeric axis is not needed here and is not built.

Playwright is **not applicable** — no browser UI. This is a CLI/raster sprint. The Evaluator attacks it by **rendering real PNGs, measuring pixels/canvas, hashing decoded-RGBA bytes, feeding violating `formats.md` fixtures, visually inspecting the rendered slides, and running both unittest suites** — not click paths.

---

## 1. Exact user-visible behaviors

The "user" is a content operator (or `/loop-create` agent) who authors `content/<slug>/formats.md` and runs one command to get 1080×1350 format PNGs + a v2 manifest. Batch B adds four new `<FORMAT>` values to the header grammar and three new directives.

### 1.1 `formats.md` grammar extensions (additive to Sprint 002 §1.1)

Header grammar unchanged: `**F<n> <FORMAT>**`. `<FORMAT>` now additionally accepts `{TIMELINE, VS-CONTRAST, LEADERBOARD, CHART}` (batch A `{BIG-NUMBER, RECEIPTS, CHECKLIST}` still render). A `<FORMAT>` outside the full seven-tag set → **fail-loud `ValueError`** naming slide + tag (unchanged behavior, new example).

**New directives (added to the directive map + directive regex; existing directives unchanged):**

| Directive | element `role` | style | rendered as | used by |
|---|---|---|---|---|
| `Event:` | `body` | chip (weight-700 in bordered chip) | a dated event chip (reuses the RECEIPTS chip primitive) | TIMELINE |
| `Row:` | `body` | body (30px, weight-500) | a ranked leaderboard row line | LEADERBOARD |
| `Bar:` | `chart-label` | chart-label (30px, weight-500, `ink`) | a direct data label **plus** a decorative proportional bar primitive | CHART |

All Sprint-002 directives (`Dominant:`, `Context:`, `Headline:`, `Body:`, `Chip:`, `Step:`, `So-what:`, `Source:`, bare `Wordmark`) keep their exact mapping. An unrecognized non-empty line → **fail-loud `ValueError`** naming slide + line (unchanged).

**`Bar:` value grammar (CHART only).** A `Bar:` line's full authored text is the `chart-label` element text (direct data-ink labeling — Tufte, no plotted axis). The bar's **length is driven by the last numeric run** in the line (regex `\d+(?:\.\d+)?`), parsed as a non-negative float. A `Bar:` line with **no numeric run** → **fail-loud `ValueError`** naming slide + line. Bars are **zero-based**: `bar_len = round(value / max_value * track_w)` (deterministic integer math); `max_value` = the largest bar value on the slide (its bar fills the track). Example: `Bar: Gachibowli · 72%` → label text "Gachibowli · 72%", value 72.

### 1.2 Per-format required-role rules (enforced at parse, fail-loud, no partial write)

Mirrors Sprint 002 §1.2. Every content format-slide MUST declare **exactly one** `dominant` and **exactly one** `wordmark`. Per-format minima:

- **TIMELINE:** exactly 1 `dominant` (anchor figure/span); **≥2** `Event:` chips; `headline` (`Context:`/`Headline:`) optional; exactly 1 `wordmark`. Fewer than 2 events → `ValueError` naming the minimum.
- **VS-CONTRAST:** exactly 1 `dominant` (side-A number, the single accent); **exactly 1** `headline` (the opposing side-B number — see §1.4 asymmetry note; authored via `Context:`/`Headline:`); **≥2** `body` labels (the two side names, via `Body:`); exactly 1 `wordmark`. 0 or ≥2 headlines, or <2 body labels → `ValueError`.
- **LEADERBOARD:** exactly 1 `dominant` (top value, the single accent); **≥2** `Row:` rows (`body`); `headline` optional; exactly 1 `wordmark`. Fewer than 2 rows → `ValueError`.
- **CHART:** exactly 1 `dominant` (peak/headline figure, the single accent); **≥2** `Bar:` chart-labels; **≥1** `source-stamp` (`Source:`); `headline` optional; exactly 1 `wordmark`. Fewer than 2 bars or 0 source → `ValueError`.

Violations (wrong dominant/wordmark count, per-format count out of range, `Bar:` with no numeric) are **fail-loud render errors with no partial write** (spec §6, R19 atomic emission).

### 1.3 v2 style constants (one new constant; all Sprint-002 v2 + all v1 constants untouched)

One new module-level constant in `render.py`; the batch-A `_FMT_*` constants and every v1 `_HOOK/_HEADLINE/_BODY/_SOURCE/_WORDMARK` / `_CC_*` constant stay **byte-unchanged** (spec §10 Risk 1):

| role | font_px | weight | color token | floor (V14) | check |
|---|---|---|---|---|---|
| `chart-label` (NEW `_FMT_CHART_LABEL`) | **30** | 500 | `ink` `#1c1917` | ≥26 | 30 ≥ 26 ✓ |

Reused Sprint-002 constants: `dominant` 132/700/`accent`, `headline` 52/700/`ink`, `body` 30/500/`ink-muted`, `chip` 30/700/`ink-muted`, `source-stamp` 26/400/`ink-muted`, `wordmark` 26/700/`accent-deep`.

**Ratio invariant (provable by inspection, per format):** all `body`-role elements render at exactly **30px** (`Event:`/`Row:`/`Body:` chips and rows), so `body_reference = max(body font_px) = 30` on TIMELINE / VS-CONTRAST / LEADERBOARD. CHART carries **no** `body` element (its data labels are `chart-label`, not `body`), so `body_reference` falls back to **26** (the raised body floor, per V13 / measure `dominant_ratio_ok`). In every case `dominant = 132`:

| format | body_reference | ratio | ≥3? |
|---|---|---|---|
| TIMELINE | 30 (Event chips) | 132/30 = 4.40 | ✓ |
| VS-CONTRAST | 30 (side labels) | 132/30 = 4.40 | ✓ |
| LEADERBOARD | 30 (rows) | 132/30 = 4.40 | ✓ |
| CHART | 26 (fallback, no body) | 132/26 = 5.08 | ✓ |

`chart-label` is **not** a `body` role, so it never enters `body_reference`; the CHART fallback-to-26 is intentional and gives CHART the strongest ratio.

### 1.4 Visual grammar per format (exact pixel coords are the Generator's, deterministic)

One-accent discipline (spec §7): the single `#0f766e` **accent** use per surface is the `dominant`. All supporting `headline` are `ink`, `body`/`chart-label`/`so-what`/`source-stamp` are `ink-muted`/`ink`, `wordmark` is `accent-deep`. Below, one clarification per format prevents mis-reading a supporting element as a second dominant/accent:

- **TIMELINE:** optional `headline` eyebrow at top; the `dominant` anchor figure (accent, dominant mass); **≥2 dated event chips** below — each chip **reuses the RECEIPTS bordered-chip primitive** (`--border #e0dbd3` 1px stroke on `--surface #ffffff` fill, chip text weight-700). **Chip borders/fills are decorative primitives — NOT manifest elements**; only the text inside each chip is a `body` element. `wordmark` bottom-right.
- **VS-CONTRAST — asymmetric-by-construction (V13 forces exactly one dominant).** Two opposing numbers **cannot both be dominant**: one is the `dominant` (132px accent), the other is a smaller `headline` (52px `ink`). The composition is a two-side split (side-A `body` label + `dominant` number; side-B `body` label + `headline` number), with the single accent on the dominant. The visible asymmetry (132 vs 52) IS the design; the Evaluator must not read the 52px headline as a second dominant. Deterministic split coords are the Generator's.
- **LEADERBOARD:** optional `headline` title; the `dominant` top value (accent) — **"accent on one row" = the dominant top value IS the single accent**; every other `Row:` renders `ink-muted` (no second accent). **≥2** ranked `Row:` body lines stacked below/around the dominant. `wordmark` bottom-right. Rank numbers are part of the authored `Row:` text (no separate numeral element).
- **CHART (Tufte-clean, real marks):** optional `headline` title; the `dominant` peak/headline figure (accent); **≥2 horizontal bars** — each bar is a **decorative `--chart-up #0d9488` filled rectangle**, **zero-based**, length ∝ authored value (`§1.1` integer math), drawn as a data-mark primitive (like RECEIPTS chips). **Bars are decorative primitives — NOT manifest elements.** Each bar carries a **direct `chart-label`** text element (≥26px, `ink`, drawn on the `bg #faf8f3` beside/above its bar — **not** on the colored bar, so contrast stays high for forward-compat V4). `source-stamp` and `wordmark` present. `has_axis:false` (zero-based, direct-labeled — no plotted numeric axis; §0). Direct labels over legends (spec §7). `--chart-up` is the token system's designated **chart-mark** color (§9), used here for data marks — it is not the branding "accent" (`#0f766e`), which remains the single dominant; this is the honest reading of the nine-token kit where `--chart-up`/`--chart-down` exist for chart marks.

All text uses vendored Inter only; the anti-tofu glyph guard (`_assert_glyphs`) runs on every element every render (R18); overflow beyond the safe band is a **fail-loud `ValueError`** (no silent clipping), reusing the batch-A band-overflow pattern.

### 1.5 R14 — ≤10 slides (inherited, unchanged)

The Sprint-002 R14 fail-loud (≥11 declared format-slides → `ValueError` naming the count, no partial write) already covers batch-B slides (they share `parse_formats`). No change; re-proven by a mixed batch-A/B fixture in tests.

### 1.6 manifest.json — schema v2 emission (unchanged seam; new format tags/role appear)

`render_asset` continues to emit `schema_version "2"` when ≥1 format-slide surface exists. Batch-B surfaces carry `role:"format-slide"`, their `format` tag ∈ {`TIMELINE`,`VS-CONTRAST`,`LEADERBOARD`,`CHART`}, `has_axis:false`, and elements each with all seven required fields (`text`, `role`, `font_px`, `weight`, `color`, `bg`, `bbox`). New in the emitted element stream: the `chart-label` role (CHART). Every `color`/`bg` is one of the nine §9 tokens; CHART chart-label `bg` is `#faf8f3` (drawn on background, not on the bar). Output PNGs named `format-01.png … format-NN.png` in slide order (R19), under `content/<slug>/render/` only, atomic. **No top-level `pdf` key** (Sprint 004). `_validate_manifest_schema` already accepts all seven tags and the `chart-label`/`format-slide` roles (Sprint 001) — **no validator change this sprint**.

### 1.7 validate.py — F-001 exit-2 guard (inherited, unchanged; now also covers batch-B)

The Sprint-002 exit-2 guard (any `format-slide` surface → clean exit 2 with cited "V13–V19 not yet wired" message, nothing written, no traceback) already fires on batch-B v2 assets identically. **No validate.py change this sprint.** Re-proven by running `validate.py` against a batch-B fixture (exit 2, cited, no traceback).

---

## 2. Routes / screens / components affected

No routes/screens (no UI). Files:

- `tools/marketing-render/render.py` — **add** the three directives (`Event:`/`Row:`/`Bar:`) to `_FMT_DIRECTIVE_RE` + `_FMT_DIRECTIVE_MAP`; **add** the `_FMT_CHART_LABEL` constant; **extend** the accepted-format set so `parse_formats` accepts all seven tags (batch-A frozenset extended/unioned — a genuinely unknown tag still fails loud); **add** per-format required-role rules for the four batch-B formats to `_validate_format_roles`; **add** the batch-B layout/draw logic (TIMELINE event chips reuse the chip machinery; LEADERBOARD/VS-CONTRAST use the stacked layout; CHART draws zero-based `--chart-up` bar primitives + direct chart-labels). **v1 code paths and all Sprint-002 batch-A behavior for the three existing formats stay unedited** except where the format set is widened; the batch-A `_FMT_*` constants are byte-unchanged.
- `tools/marketing-render/tests/test_render_v2.py` — **consciously re-point** `test_unknown_format_tag_fail_loud` to a bogus tag (`PIE-CHART`) + **add** a positive assertion that all four batch-B tags render; **add** batch-B render/determinism/floor/ratio/fail-loud test classes. No existing assertion weakened or deleted (only the one example tag moves, documented §0).
- `tools/marketing-render/tests/inputs/fmt-timeline/formats.md`, `…/fmt-vs-contrast/formats.md`, `…/fmt-leaderboard/formats.md`, `…/fmt-chart/formats.md` — **new** renderer-input fixtures (under the existing `tests/inputs/` dir, NOT `fixtures/`, so `acceptance.py`'s 12-fixture set is untouched). No committed PNGs — rendered to a temp dir in tests.

**Out of scope (do not touch):** `render.py`'s v1 functions/constants and the batch-A `_FMT_*` style constants; `measure.py` (frozen — call `dominant_ratio_ok`, `format_slide_type_min` only, add none — `chart-label` floor 26 already exists); `validate.py` (schema + F-001 guard already cover batch B — no edit); `acceptance.py`; any `fixtures/*` asset or `make_fixtures.py`; the TGRERA / hyd content assets; PDF emission; V13–V19 check wiring; the 360px thumbnail (V15) / contrast (V4) gating; any file outside `tools/marketing-render/`.

---

## 3. Data / state transitions

- Input: `content/<slug>/formats.md`. Output: `content/<slug>/render/format-NN.png` + `render/manifest.json`. No DB, no network, no state beyond files.
- `render_asset` builds all images + manifest **in memory**, then `write_outputs` writes; any parse/layout error raises **before** any file is written (atomic, R19).
- Determinism (R18): identical `formats.md` → **pixel-identical PNGs** (decoded-RGBA SHA-256) and **byte-identical `manifest.json`** across runs. Bar lengths via deterministic integer `round()`; fonts loaded only from vendored `fonts/`; zero network.

---

## 4. Empty / loading / success / error / invalid states

- **Missing asset folder** → `FileNotFoundError`, exit 1, nothing written.
- **No renderable input** → `FileNotFoundError` naming the requirement, exit 1.
- **Success** → `format-NN.png` + `manifest.json` (schema "2") under `render/`, exit 0, per-file "wrote …" lines.
- **Fail-loud invalid `formats.md`:** unknown/bogus format tag; unparseable line; content slide with 0 or ≥2 dominants; missing wordmark; TIMELINE <2 events; VS-CONTRAST 0/≥2 headline or <2 labels; LEADERBOARD <2 rows; CHART <2 bars or 0 source; `Bar:` with no numeric run; ≥11 slides; band overflow; tofu glyph → **`ValueError`/`RuntimeError`**, exit 1, **no partial write**.
- **validate.py on a v2 asset (incl. batch B)** → clean **exit 2** with the cited "V13–V19 not yet wired" message, nothing written (no traceback).
- **No loading state** (synchronous CLI).

---

## 5. Keyboard / focus / ARIA / contrast / responsive

- **UI a11y:** N/A — no DOM/viewport. Stated so the omission is not read as a gap.
- **Raster legibility (the real a11y surface):** raised type floors met by construction (§1.3). CHART chart-labels are drawn on `bg #faf8f3` in `ink #1c1917` (not on the `--chart-up` bars), keeping contrast high for forward-compat V4. Contrast/thumbnail (V4/V15) routing for format-slides is Sprint 005; not gated here, but colors are chosen to pass. A FAIL in a pre-measured `contrast_check`/thumbnail is a Sprint-005 concern, not a Sprint-003 gate.
- **Responsive proxy:** the 360px thumbnail legibility gate (V15) is Sprint 005; this sprint guarantees only the declared floors and the ≥3× dominant ratio.

---

## 6. Security / privacy assumptions

- No network at import- or render-time. Evaluator may run with network disabled.
- No secrets/tokens/credentials; no `.env`; no DB writes; no writes outside `content/<slug>/render/` (and, in tests, a temp dir).
- No new third-party dependency: stdlib + already-vendored Pillow only. `render.py` gains no import beyond what it already uses.
- Fixture copy is illustrative/public-style (RERA/portal/market-estimate generic guidance) — no TERREM DB numbers (spec §9 provenance-safety). The provenance-checked TGRERA asset is Sprint 006.

---

## 7. Commands to run (Evaluator)

From repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`:

```bash
# (a) Render the four batch-B fixtures (same-basename folder into two temp parents,
#     so slug is identical — CN-002 hygiene from Sprint 002 findings).
for f in fmt-timeline fmt-vs-contrast fmt-leaderboard fmt-chart; do
  mkdir -p /tmp/s3a/$f /tmp/s3b/$f && \
  cp tools/marketing-render/tests/inputs/$f/formats.md /tmp/s3a/$f/ && \
  cp tools/marketing-render/tests/inputs/$f/formats.md /tmp/s3b/$f/ && \
  python3 tools/marketing-render/render.py /tmp/s3a/$f && \
  python3 tools/marketing-render/render.py /tmp/s3b/$f
done

# (b) Canvas + schema: every format PNG is 1080x1350; manifest schema "2";
#     correct format tag; has_axis:false.
python3 - <<'PY'
import json, glob
from PIL import Image
seen=set()
for mf in glob.glob('/tmp/s3a/fmt-*/render/manifest.json'):
    m = json.load(open(mf))
    assert m["schema_version"] == "2", mf
    for s in m["surfaces"]:
        assert s["role"]=="format-slide" and s["canvas"]=={"w":1080,"h":1350}, s["id"]
        assert s["has_axis"] is False, s["id"]
        seen.add(s["format"])
        im = Image.open(mf.rsplit('/',1)[0] + '/' + s["png"])
        assert im.size == (1080,1350), s["id"]
assert {"TIMELINE","VS-CONTRAST","LEADERBOARD","CHART"} <= seen, seen
print("canvas+schema+tags OK")
PY

# (c) Determinism: decoded-RGBA PNGs + manifest bytes identical across the two runs.
python3 - <<'PY'
import hashlib, glob
from PIL import Image
def rgba(p): return hashlib.sha256(Image.open(p).convert("RGBA").tobytes()).hexdigest()
for a in glob.glob('/tmp/s3a/fmt-*'):
    b = a.replace('/s3a/','/s3b/')
    for pa in sorted(glob.glob(a + '/render/format-*.png')):
        pb = b + '/render/' + pa.rsplit('/',1)[1]
        assert rgba(pa) == rgba(pb), pa
    assert open(a+'/render/manifest.json','rb').read() == open(b+'/render/manifest.json','rb').read(), a
print("determinism OK")
PY

# (d) V13/V14 provable against the EMITTED manifest via Sprint-001 measure fns.
python3 - <<'PY'
import sys, json, glob
sys.path.insert(0,'tools/marketing-render'); import measure
for mf in glob.glob('/tmp/s3a/fmt-*/render/manifest.json'):
    for s in json.load(open(mf))["surfaces"]:
        els = s["elements"]
        r = measure.dominant_ratio_ok(els)
        assert r["passes"] and (r["exempt"] or r["ratio"] >= 3.0), (s["id"], r)
        assert sum(1 for e in els if e["role"]=="wordmark")==1, s["id"]
        assert sum(1 for e in els if e["role"]=="dominant")==1, s["id"]
        for e in els:
            if e["role"] != "wordmark":
                assert measure.format_slide_type_min(e["role"], e["font_px"])["passes"], (s["id"],e["role"],e["font_px"])
print("V13/V14 (measure) OK")
PY

# (e) Bars are DECORATIVE, not manifest elements: CHART manifest carries only
#     dominant + chart-labels + source-stamp + wordmark (+ optional headline) —
#     no phantom "bar" element rows.
python3 - <<'PY'
import json
m = json.load(open('/tmp/s3a/fmt-chart/render/manifest.json'))
s = [x for x in m["surfaces"] if x["format"]=="CHART"][0]
roles = sorted(e["role"] for e in s["elements"])
assert "chart-label" in roles and roles.count("dominant")==1, roles
assert all(r in {"headline","dominant","chart-label","source-stamp","wordmark"} for r in roles), roles
assert sum(1 for e in s["elements"] if e["role"]=="chart-label") >= 2, roles
print("CHART decorative-bars / chart-labels OK:", roles)
PY

# (f) validate.py on a batch-B v2 asset -> clean exit 2, cited, NO traceback.
python3 tools/marketing-render/render.py /tmp/s3a/fmt-timeline >/dev/null
python3 tools/marketing-render/validate.py /tmp/s3a/fmt-timeline; echo "exit=$?"

# (g) Regression: hyd + tgrera stay schema "1" and byte-identical after re-render.
python3 tools/marketing-render/render.py content/2026-07-03-hyd-premium-vs-budget
python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave
git -C /Users/prithviputta/Downloads/terrem-marketing-loops status --porcelain content/  # expect no diff

# (h) Full suites — render count MUST rise above 219 and stay OK; loop stays 254 OK.
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"
python3 -m unittest discover -s tools/marketing-loops/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"

# (i) No-network import sanity.
python3 -c "import sys; sys.path.insert(0,'tools/marketing-render'); import render, validate, measure; print('import-ok')"
```

**Baseline (from Sprint-002 findings, re-confirmed in generator_trace.log before code):** render suite `Ran 219 … OK`; loop suite `Ran 254 … OK`. After this sprint: render count **> 219** and `OK`; loop **254 … OK**.

---

## 8. Adversarial matrix the Evaluator should run (replaces Playwright click paths)

Each row is a distinct, isolable attack; the Generator ships each as a unit test too.

| # | Attack | Expected result |
|---|---|---|
| 1 | Render `fmt-timeline` | 1080×1350; `format=TIMELINE`; ≥2 event body-chips; anchor dominant; chip pixels drawn with `--border`/`--surface` (NOT manifest elements) |
| 2 | Render `fmt-vs-contrast` | 1080×1350; `format=VS-CONTRAST`; **exactly one** dominant (132) + one headline second-number (52) + ≥2 body labels |
| 3 | Render `fmt-leaderboard` | 1080×1350; `format=LEADERBOARD`; one dominant top value; ≥2 body rows; single accent = dominant |
| 4 | Render `fmt-chart` | 1080×1350; `format=CHART`; `has_axis:false`; ≥2 `chart-label`s; `--chart-up` bar pixels present (decorative, NOT manifest elements); source-stamp present |
| 5 | `measure.dominant_ratio_ok(elements)` per slide | `passes True`; TIMELINE/VS/LEADER 132/30=4.40; CHART 132/26=5.08 (no-body fallback); exactly one dominant |
| 6 | `measure.format_slide_type_min(role,font_px)` per non-wordmark element | `passes True` (headline 52, body/chart-label 30, source 26) |
| 7 | Count `wordmark` + `dominant` per format-slide | exactly **1** each |
| 8 | `_validate_manifest_schema` on an emitted batch-B v2 manifest | **no raise** (structurally valid; tags + `chart-label` accepted) |
| 9 | Re-render each fixture (same-basename folder); compare decoded-RGBA PNG + manifest bytes | **identical** (R18) |
| 10 | CHART `Bar:` line with **no numeric run** | fail-loud `ValueError` naming slide + line; no partial write |
| 11 | CHART with **1** bar | `ValueError` naming bar minimum (≥2) |
| 12 | CHART missing `Source:` | `ValueError` naming source requirement |
| 13 | TIMELINE with **1** event | `ValueError` naming event minimum (≥2) |
| 14 | LEADERBOARD with **1** row | `ValueError` naming row minimum (≥2) |
| 15 | VS-CONTRAST with **0** or **2** headlines (second numbers) | `ValueError` naming the exactly-one-headline rule |
| 16 | VS-CONTRAST with **1** body label | `ValueError` naming the ≥2-label rule |
| 17 | Any batch-B slide with 0 / 2 `Dominant:` | `ValueError` ("exactly one dominant"), no partial write |
| 18 | Any batch-B slide missing `Wordmark` | `ValueError` ("exactly one wordmark") |
| 19 | Header `**F1 PIE-CHART**` (genuinely bogus tag) | `ValueError` ("unknown/unsupported format tag") — the re-pointed Sprint-002 assertion |
| 20 | Header `**F1 TIMELINE**` (now valid) | renders (the conscious flip: batch-B tag now accepted) |
| 21 | `validate.py <batch-B v2 asset>` | **exit 2**, cited "format-slide … V13–V19 … Sprint 005" message, **no traceback**, nothing written (F-001, inherited) |
| 22 | `validate.py` on the 12 v1 fixtures + hyd + tgrera | **unchanged verdicts** — guard does not fire |
| 23 | Re-render hyd + tgrera | `manifest.json` stays `schema_version "1"`, **byte-identical**; PNGs decoded-RGBA identical |
| 24 | Every emitted `color`/`bg` (incl. CHART chart-label bg `#faf8f3`, dominant `#0f766e`) | is one of the nine §9 tokens |
| 25 | Mixed A+B `formats.md` with **11** slides | fail-loud `ValueError` naming count; no `render/` written (R14, inherited) |
| 26 | Anti-tofu: a batch-B element with a real glyph | renders (no false tofu); guard runs every render |
| 27 | Visual: read `fmt-chart.png` / `fmt-vs-contrast.png` PNGs | real zero-based bars with direct labels (not inert text); one accent = dominant; no second accent, no chartjunk |
| 28 | Render suite / loop suite | render `Ran N>219 … OK`; loop `Ran 254 … OK` |
| 29 | `import render, validate, measure` with network off | `import-ok` |

**Freeze invariant (must hold):** rows 22–23 + 28 prove the v1 renderer/validator behavior is byte-for-byte preserved and the batch-A behavior unchanged; no previously-passing artifact changes except the one consciously re-pointed test assertion (rows 19–20), which preserves the "unknown tag fails loud" guarantee.

---

## 9. Explicit non-goals (Sprint 003)

- **No PDF.** `carousel.pdf` and the top-level `pdf` manifest key are Sprint 004.
- **No V13–V19 QA wiring.** No `_check_v*` added; only the inherited F-001 exit-2 guard runs on v2 assets.
- **No `has_axis:true` / plotted numeric axis on CHART.** CHART renders zero-based, direct-labeled bars only; the truncated/disclosed-break V10 path is Sprint 005 via hand-authored manifests (§0).
- **No `measure.py` change** — frozen; this sprint only *calls* its functions (`chart-label` floor 26 already present).
- **No `validate.py` change** — schema + F-001 guard already cover batch B.
- **No `acceptance.py` change**, no `fixtures/*` change, no `make_fixtures.py` change, no TGRERA/hyd content edit.
- **No v1 renderer edits** and **no batch-A `_FMT_*` constant edits** — byte-unchanged (only the accepted-format set is widened + new directives/role/layout added).
- **No 360px thumbnail (V15) or contrast (V4) gating** on format-slides — Sprint 005.
- **No new dependency, no network, no writes outside `tools/marketing-render/` + the target `content/<slug>/render/`.**

---

## 10. Definition of done (what the Evaluator can verify on disk)

1. `render.py` renders `TIMELINE`, `VS-CONTRAST`, `LEADERBOARD`, `CHART` format-slides to **1080×1350** PNGs, each with exactly one `dominant` at **132px** (ratio ≥3 over its body_reference), raised floors met, exactly one wordmark, from an authored `formats.md`.
2. CHART draws **genuine zero-based `--chart-up` bars with direct `chart-label`s** (bars decorative — not manifest elements); `has_axis:false`; ≥2 chart-labels + ≥1 source-stamp. VS-CONTRAST is asymmetric-by-construction (one 132 dominant + one 52 headline). LEADERBOARD/TIMELINE use one accent = dominant, event chips reuse the RECEIPTS primitive.
3. `render_asset` emits `schema_version "2"` manifests (batch-B `format` tags, `chart-label` role, `has_axis:false`, no `pdf` key) that `_validate_manifest_schema` accepts and Sprint-001 `measure` functions confirm V13/V14-clean.
4. Determinism: re-render (same-basename folder) → decoded-RGBA-identical PNGs + byte-identical manifest (§7c/row 9).
5. Every fail-loud state (§4, rows 10–18, 25) raises with **no partial write**.
6. The conscious regression change is exactly one: `test_unknown_format_tag_fail_loud` re-pointed to a bogus tag + a new positive batch-B assertion (rows 19–20). No other assertion weakened; the "unknown tag fails loud" guarantee preserved.
7. `validate.py` on a batch-B v2 asset exits **2** with the cited message, **no traceback** (row 21); on all v1 assets its verdicts are **unchanged** (row 22).
8. v1 freeze: hyd + tgrera re-render to `schema_version "1"`, byte-identical manifests + decoded-RGBA-identical PNGs (row 23).
9. Render suite `Ran N>219 … OK`; loop suite `Ran 254 … OK`; no-network import ok.
10. `generator_trace.log` records the 219/254 baseline re-confirmed **before** code, the files changed, the new-test count, the conscious test re-point justification, the freeze evidence, and any disclosed risk (bar-length rounding, VS-CONTRAST asymmetry, chart-up-as-data-mark rationale).

This contract is testable end-to-end by running §7 commands and the §8 matrix. If any row cannot be executed against the shipped code, the contract is not met.
