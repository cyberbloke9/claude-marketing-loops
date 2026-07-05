# Sprint 002 Contract — Carousel Renderer + Manifest

Status: PROPOSED
Sprint: 002
Depends on: Sprint 001 (`tools/marketing-render/measure.py`, PASSED).
Spec refs: §5.1 (R1, R3, R4, R7, R8, R9), §5.3 (manifest schema), §6 (states), §7 (design), §9 (tokens, fonts, no-network), §11 (Sprint 002), Risk 4 (glyph-size seam).

## 0. Purpose & boundary

This sprint builds the **carousel renderer**: it reads `content/<slug>/carousel.md`,
renders each declared slide to a `1080×1350` PNG using **vendored Inter** and the locked
brand tokens, and emits `content/<slug>/render/manifest.json` (§5.3 schema) describing every
text element it drew. It is a headless CLI raster tool — there is **no browser/web UI**, so
there is no Playwright click-path. The Evaluator attacks the CLI directly and inspects the
produced PNGs + manifest with the Python probes in §8/§9. This is intentional and stated so
the contract is fully testable.

**In scope (Sprint 002):** carousel text-slide rendering (roles: hook, headline, body,
source-stamp, wordmark), the `manifest.json` carousel surfaces, deterministic re-render,
vendored fonts, CLI + error states.

**Explicitly NOT in this sprint (see §11):** the `1080×1920` chart card (Sprint 003), the
validator / `qa-verdict.json` (Sprint 004), plotted charts inside carousel slides, the
`meta.md` verdict append, and any `qa-checklist.md` edit.

### Scope-honesty note (read before attacking the asset's content)
The demo asset `content/2026-07-03-hyd-premium-vs-budget/` is **KILLED on data provenance**
(its `meta.md` records the kill). Sprint 002 proves **rendering correctness only** — canvas
dimensions, manifest schema, brand-token fidelity, ink-present (anti-stub), and byte-for-byte
determinism. It does **not** claim the asset passes QA; a QA PASS is Sprint 004+ and the killed
asset would correctly FAIL the provenance check (V11) there. Do not score Sprint 002 on whether
the asset "should publish" — score it on whether the renderer faithfully rasterizes the authored
carousel.

## 1. Language / runtime decision

- **Python 3** (`/usr/bin/python3`, 3.9.6) + **Pillow 11.3.0** (already installed; `freetype2`
  available, confirmed). Pillow gives deterministic freetype raster at fixed pixel sizes — the
  right tool for R8 (pixel-identical re-render) and R4 (no network).
- **No new third-party dependency beyond Pillow.** No `pip install`, no network, no `matplotlib`
  (charts are Sprint 003). Imports allowed: Python stdlib + `PIL` + the local `measure` module.
- Reuses `tools/marketing-render/measure.py` for token validation (`is_brand_token`,
  `token_name`) — the renderer↔measure seam.

## 2. Files this sprint creates / modifies (and ONLY these)

Creates:
- `tools/marketing-render/render.py` — the carousel renderer CLI (all behavior in §4–§7).
- `tools/marketing-render/fonts/Inter-Regular.ttf` — vendored (weight 400).
- `tools/marketing-render/fonts/Inter-Medium.ttf` — vendored (weight 500).
- `tools/marketing-render/fonts/Inter-SemiBold.ttf` — vendored (weight 600, reserved).
- `tools/marketing-render/fonts/Inter-Bold.ttf` — vendored (weight 700).
- `tools/marketing-render/fonts/OFL.txt` — SIL Open Font License 1.1 for Inter.
- `tools/marketing-render/tests/test_render.py` — stdlib `unittest` tests (see §8).

Modifies (minimal, copy-preserving disambiguation — see §3.4):
- `content/2026-07-03-hyd-premium-vs-budget/carousel.md` — three small edits so the file is
  unambiguously parseable. **No rendered copy changes**; only authoring annotations are moved
  into HTML comments and one `Source:`/`Caption:` line is split. Diff enumerated in §3.4.

Writes at render time (created by the tool, not committed as source):
- `content/2026-07-03-hyd-premium-vs-budget/render/carousel-01.png` … `carousel-08.png`
- `content/2026-07-03-hyd-premium-vs-budget/render/manifest.json`

**No `__init__.py`** (same hyphenated-dir reason as Sprint 001). Tests put the tool dir on
`sys.path`. No writes anywhere else in the repo. No edits to `brand/`, other `content/` assets,
`measure.py`, or other tools.

### 2.1 Font vendoring (R4 — no network at render time)
- Source: copy the four static Inter TTFs from the machine-local path
  `/opt/homebrew/lib/node_modules/ruflo/src/ruvocal/src/lib/server/fonts/Inter-{Regular,Medium,SemiBold,Bold}.ttf`
  into `tools/marketing-render/fonts/`. This is a **local file copy, not a network fetch** — R4 is
  satisfied (the fonts live inside the repo after vendoring; the renderer never touches the source path).
- **Pin byte-identity:** the renderer loads fonts only from `tools/marketing-render/fonts/`
  (path computed from `__file__`). It must NEVER load a system font or the ruflo path. A test
  asserts the four files exist and records their SHA-256 (Inter rasterization is version-sensitive;
  determinism depends on the exact bytes). Reference SHA-256 (first 16 hex) at authoring time:
  `Inter-Regular 3127f0b873387ee3 · Inter-Medium a645f55492d1c8cd · Inter-SemiBold b0b540e69bf67170 · Inter-Bold 412c068eab6f36e6`.
- **License:** Inter is SIL OFL 1.1 (redistributable). `OFL.txt` is written with the standard
  SIL OFL 1.1 body text plus the Inter copyright line
  (`Copyright (c) 2016 The Inter Project Authors (https://github.com/rsms/inter)`). No network needed.
- **Glyph coverage confirmed** for every character in the hyd carousel copy (₹ · − ≠ — – “ ” ’ •
  all present in Inter). The renderer additionally guards against tofu (§4.4).

## 3. Input grammar — how `carousel.md` is parsed (deterministic)

The renderer reads `content/<slug>/carousel.md` as UTF-8 text and parses it with these rules,
applied line-by-line. The grammar matches the **existing authoring conventions**; §3.4 lists the
only three edits needed to make the current file unambiguous.

### 3.1 Preprocessing
1. Split into lines. Everything **before the first slide header** (title, the "All slides: …"
   preamble) is ignored.
2. On every line, strip HTML comments `<!--  … -->` (non-greedy) **before** role extraction, then
   strip trailing whitespace. (This lets authoring notes like `<!-- UTM per channel -->` live in
   the file without being rendered.)

### 3.2 Slide segmentation
- A slide **begins** at a line matching `^\*\*S(\d+)\b.*\*\*\s*$` (bold `**S<n> …**` marker).
  The captured integer is the slide number. The slide body is every line until the next such
  header, a bare `---` separator, or EOF.
- Slides are rendered in ascending slide-number order. Header parentheticals (e.g. `(9 words,
  biggest type)`) are used **only** for segmentation and are never rendered.

### 3.3 Element extraction (per slide, in file order)
Each recognized line yields exactly one manifest element. Unrecognized non-empty lines that are
not a chart placeholder raise a parse error naming the slide + line (fail loud, no silent drop).

| Line pattern | Element role | Font px | Weight | Color token | Notes |
|---|---|---|---|---|---|
| `^>\s*(.+)$` on **slide 1** | `hook` | 61 | 700 | `ink` `#1c1917` | primary; exactly one per slide 1 |
| `^>\s*(.+)$` on slides 2–8 | `headline` | 49 | 700 | `ink` `#1c1917` | primary |
| `^(Sub\|Body\|Caption)\b[^:]*:\s*(.+)$` | `body` | 25 | 400 | `ink-muted` `#57534e` | capture group 2 (drops any `(24px)`-style note before the colon) |
| `^Source:\s*(.+)$` | `source-stamp` | 20 | 400 | `ink-muted` `#57534e` | exempt from size floor |
| `^Link:\s*(.+)$` | `body` | 25 | 500 | `accent` `#0f766e` **unless** the slide contains a `wordmark` marker → `ink-muted` `#57534e` | one accent per surface: CTA slide link = accent, source slide link = muted |
| line containing `wordmark` (case-insensitive) | `wordmark` | 25 | 700 | `accent-deep` `#0d3d38` | literal rendered text is `TERREM`, bottom-right |
| `^\[.*\]$` (bracket-only, e.g. `[Diverging bar chart, …]`) | *(no element)* | — | — | — | recorded as informational `chart_ref` on the surface; NOT rendered (chart plotting is Sprint 003) |

Text is taken **verbatim** from the captured group (inner quotes, en-dashes, ₹, etc. preserved);
only the leading marker and surrounding whitespace are stripped. Every emitted `color` and `bg`
is validated with `measure.is_brand_token(...)`; a non-token color raises an error (defensive —
the table only ever assigns the five tokens `bg`/`ink`/`ink-muted`/`accent`/`accent-deep`).

### 3.4 The three disambiguation edits to `carousel.md` (copy-preserving)
1. **S3** — split the combined caption/source line and drop the trailing period after the date:
   - was: `Caption: 3-month price change, every tracked locality. Source: TERREM Intelligence · 302,156 Hyderabad transactions · as of 2026-03-08.`
   - now two lines:
     `Caption: 3-month price change, every tracked locality.`
     `Source: TERREM Intelligence · 302,156 Hyderabad transactions · as of 2026-03-08`
2. **S7** — move the UTM note into a comment so the rendered link is clean:
   - was: `Link: intel.terrem.in/markets (UTM per channel — see meta.md)`
   - now: `Link: intel.terrem.in/markets  <!-- UTM per channel — see meta.md -->`
3. **S8** — prefix the bare link line and comment-ize its inline note:
   - was: `intel.terrem.in/markets (small, --ink-muted)`
   - now: `Link: intel.terrem.in/markets  <!-- small, --ink-muted -->`

No other content changes. The `TERREM wordmark, --accent-deep #0d3d38` marker line is left as-is
(the parser detects the `wordmark` keyword).

## 4. Renderer behavior

### 4.1 CLI
```
python3 tools/marketing-render/render.py <asset-folder>
```
- `<asset-folder>` is a path to `content/<slug>/` (positional, required).
- On success: renders all carousel slides + writes `manifest.json`, prints one line per PNG
  written and the manifest path, exits **0**.
- Reads only: `<asset-folder>/carousel.md`, the vendored fonts, and (via `measure`)
  `brand/brand-kit.md` is NOT needed here (no blacklist scan this sprint). No network.

### 4.2 Canvas & tokens (R3)
- Every carousel PNG is exactly `1080×1350`, flat-filled with `bg` `#faf8f3`. No gradients,
  textures, or images under type (§7 anti-patterns).
- Only the five tokens in §3.3 appear as declared element colors. All are members of the nine
  locked tokens (`measure.TOKEN_HEXES`).

### 4.3 Layout (deterministic, integer math)
- `MARGIN_X = 90`, `CONTENT_W = 900` (text column x ∈ [90, 990], inside the carousel safe rect
  x ∈ [40, 1040]).
- **Wrap:** greedy word-wrap; a line holds as many space-separated words as fit within
  `CONTENT_W`, measured by `ImageFont.getlength` at the element's font+size (deterministic). A
  single word wider than `CONTENT_W` is placed alone (no mid-word break).
- **Line advance** = `round(font_px * 1.4)`. **Em height** (single-line visual height) =
  `round(font_px * 1.2)`.
- **Element bbox** `[x, y, w, h]`: `x = 90` (left-aligned) — except `wordmark`, right-aligned so
  `x = 990 - w`; `w = ceil(max line width)`; `h = (n_lines - 1) * line_advance + em_height`.
- **Vertical placement:** the slide's stacked elements (all roles except `wordmark`) are laid out
  top-to-bottom with an inter-element gap of `round(0.7 * preceding_font_px)`, and the whole stack
  is **vertically centered** inside the band y ∈ [160, 1180] (integer division; deterministic). If
  the stack is taller than the band, the renderer errors (fail loud) rather than overflowing the
  safe zone — the hyd asset fits comfortably.
- **Wordmark** (`TERREM`) is drawn bottom-right independent of the stack: baseline near y ≈ 1250,
  right edge at x = 990. (Wordmark and source-stamp are exempt from the safe-zone rule per spec V6;
  headline/body/hook are not, and by construction stay inside the band.)

### 4.4 Anti-tofu glyph guard
Before drawing any run, the renderer confirms every character has a real glyph in the chosen Inter
face (compare the rendered single-glyph raster against the font's `.notdef`). A missing glyph
raises `RuntimeError` naming the character, the slide, and the element role — the renderer never
silently rasterizes a `.notdef` box.

### 4.5 Manifest emission (§5.3 schema)
Writes `<asset-folder>/render/manifest.json`:
```json
{
  "schema_version": "1",
  "slug": "<slug>",
  "surfaces": [
    {
      "id": "carousel-01",
      "role": "carousel-slide",
      "png": "carousel-01.png",
      "canvas": { "w": 1080, "h": 1350 },
      "has_axis": false,
      "axis_min": null,
      "zero_based": null,
      "break_disclosed": null,
      "chart_ref": null,
      "elements": [
        { "text": "...", "role": "hook", "font_px": 61, "weight": 700,
          "color": "#1c1917", "bg": "#faf8f3", "bbox": [90, 214, 812, 148] }
      ]
    }
  ]
}
```
- One surface per rendered slide; `elements` in file order. `chart_ref` is `null` except on the
  S3 chart slide where it is `"chart-spec.md"` (informational; the slide still renders its caption
  + source-stamp text).
- `bbox` is the **visual** bounding box of the rendered run (used by the Sprint 004 safe-zone check
  directly). **Glyph-size seam (Risk 4):** `h` is built from `line_advance`/`em_height`, so a single
  line has `h ≈ 1.2·font_px` (inside the ±25% band) and a font-size lie is catchable in Sprint 004
  by recovering per-line height via the shared, deterministic wrap. No extra manifest field is added;
  Sprint 004 re-wraps with the same layout module to get `n_lines`. (This resolves the Sprint 001
  seam note that cap-height mapping would false-fail: `em_height = 1.2·font_px`, not `0.7·font_px`.)
- **Slide-1 carries exactly one `hook` element**; no other slide has a `hook` (§5.3 rule).
- **Serialization is deterministic:** `json.dumps(obj, ensure_ascii=False, indent=2,
  sort_keys=True)` + trailing newline. No timestamp/date field anywhere in the manifest.

### 4.6 Determinism (R8) & atomicity (R9)
- No timestamps, no run-varying metadata. Fonts fixed and vendored; layout is pure integer math;
  wrap is deterministic; PNGs saved with Pillow's default PNG writer (no `tIME` chunk). The
  normative determinism check is **decoded-RGBA SHA-256** (open each PNG, `convert("RGBA")`,
  hash `tobytes()`), which is immune to any PNG-container variance.
- **Atomic, no partial writes:** the renderer builds **all** slide images + the manifest in memory
  first; only after every slide renders successfully does it create `render/` and write the files.
  On any error (missing input, parse error, missing glyph, overflow) it writes nothing and exits
  non-zero. It writes **only** inside `<asset-folder>/render/`.

## 5. Exact expected output for the hyd asset (the renderer↔validator seam, enumerated)

Eight surfaces `carousel-01 … carousel-08`, each `1080×1350`, role `carousel-slide`. Element
lists (role · font_px · weight · color · text) — this is what the manifest MUST contain (bboxes
are layout-computed and verified by invariant, not pinned to exact pixels):

- **carousel-01** (hook slide):
  - `hook` · 61 · 700 · `#1c1917` · "Jubilee Hills just got cheaper. Medchal rose 19%."  *(8 words)*
  - `body` · 25 · 400 · `#57534e` · "Same city. Same 3 months."
- **carousel-02**:
  - `headline` · 49 · 700 · `#1c1917` · "\"Hyderabad prices are rising\" is a meaningless sentence."
  - `body` · 25 · 400 · `#57534e` · "The city moved in opposite directions by 28 points last quarter. Which direction did YOUR locality move?"
- **carousel-03** (chart reference slide; `chart_ref="chart-spec.md"`):
  - `body` · 25 · 400 · `#57534e` · "3-month price change, every tracked locality."
  - `source-stamp` · 20 · 400 · `#57534e` · "Source: TERREM Intelligence · 302,156 Hyderabad transactions · as of 2026-03-08"
- **carousel-04**:
  - `headline` · 49 · 700 · `#1c1917` · "The premium core blinked."
  - `body` · 25 · 400 · `#57534e` · "Banjara Hills −3.0% · Punjagutta −3.4% · Jubilee Hills −6.1% · Begumpet −8.0%. If you've been priced out of these localities, this is the first soft quarter in a while."
- **carousel-05**:
  - `headline` · 49 · 700 · `#1c1917` · "Meanwhile, the budget corridors ran."
  - `body` · 25 · 400 · `#57534e` · "Medchal +19.2% · Ameerpet +12.7% · Tarnaka +12.7% · Dilsukhnagar +11.3%. Waiting has been expensive at the entry level — ₹-per-sqft there is climbing fastest."
- **carousel-06**:
  - `headline` · 49 · 700 · `#1c1917` · "Before you panic-buy or panic-sell:"
  - `body` · 25 · 400 · `#57534e` · "Over 12 months most \"falling\" localities are still up (Gopanpally: −5.9% this quarter, +11.6% on the year). This is a 3-month turn, not a crash. Trends ≠ guarantees."
- **carousel-07** (CTA):
  - `headline` · 49 · 700 · `#1c1917` · "Check your locality before your next site visit."
  - `body` · 25 · 400 · `#57534e` · "Every locality, every trend, updated continuously. Free."
  - `body` · 25 · 500 · `#0f766e` · "intel.terrem.in/markets"  *(the one accent element)*
- **carousel-08** (source):
  - `source-stamp` · 20 · 400 · `#57534e` · "Source: TERREM Intelligence · 302,156 Hyderabad transactions · as of 2026-03-08"
  - `body` · 25 · 500 · `#57534e` · "intel.terrem.in/markets"
  - `wordmark` · 25 · 700 · `#0d3d38` · "TERREM"

All colors above are locked tokens; every text run's `bg` is `#faf8f3`. Contrast (verified in
Sprint 004, sanity-noted here): ink/bg ≈ 16.5:1, ink-muted/bg ≈ 6.5:1, accent/bg ≈ 5.15:1,
accent-deep/bg high — all ≥ 4.5:1. Type minimums: headline 49 ≥ 48, hook 61 ≥ 48, body 25 ≥ 24
(source-stamp/wordmark exempt).

## 6. States that must exist (mapped to spec §6)

- **Missing asset folder** → `error: asset folder not found: <path>`, exit non-zero, no writes.
- **Missing `carousel.md`** → `error: carousel.md not found in <path>`, exit non-zero, no writes.
- **Unparseable line / no slides found** → parse error naming slide+line, exit non-zero, no writes.
- **Missing vendored font** → error naming the missing font file, exit non-zero, no writes.
- **Missing glyph (tofu)** → `RuntimeError` naming char/slide/role, exit non-zero, no writes (§4.4).
- **Stack overflow (content too tall for safe band)** → error, exit non-zero, no writes.
- **Success** → eight `1080×1350` PNGs + `manifest.json` under `render/`, exit 0.
- **Deterministic re-render** → a second run over the same input yields byte-identical manifest
  and decoded-RGBA-identical PNGs (§8 command 2).
- **Anti-stub** → no blank PNGs: ink of the declared color is present inside every text bbox (§9).

## 7. Design fidelity (§7)

- Inter only (700 headlines/hook, 400 body, 500 links, 700 wordmark); locked tokens only; flat
  `bg` canvas; no gradients/textures/photos under type; no all-lowercase overlay headlines; no
  condensed/thin faces. One accent per surface (S7 link accent; S8 wordmark accent-deep; other
  slides neutral ink/ink-muted — zero accent is permitted, more than one is not). Left-aligned
  editorial text, generous 1.4 line advance. Chart plotting is deliberately absent (Sprint 003).

## 8. Commands the Evaluator runs

From repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`:

```bash
# (0) Unit tests — parse, layout, token, glyph-guard, error-state tests. Must pass, exit 0.
python3 -m unittest discover -s tools/marketing-render/tests -v

# (1) Render the demo asset — exit 0, writes render/ only
python3 tools/marketing-render/render.py content/2026-07-03-hyd-premium-vs-budget
ls content/2026-07-03-hyd-premium-vs-budget/render/

# (2) Determinism (R8): render twice, decoded-RGBA SHA-256 identical per PNG; manifest byte-identical
python3 - <<'PY'
import subprocess, hashlib, json, os
from PIL import Image
A="content/2026-07-03-hyd-premium-vs-budget"
def snap():
    r={}
    for f in sorted(os.listdir(f"{A}/render")):
        p=f"{A}/render/{f}"
        if f.endswith(".png"):
            r[f]=hashlib.sha256(Image.open(p).convert("RGBA").tobytes()).hexdigest()
        else:
            r[f]=hashlib.sha256(open(p,'rb').read()).hexdigest()
    return r
subprocess.run(["python3","tools/marketing-render/render.py",A],check=True)
s1=snap()
subprocess.run(["python3","tools/marketing-render/render.py",A],check=True)
s2=snap()
assert s1==s2, "NON-DETERMINISTIC: "+str([k for k in s1 if s1[k]!=s2.get(k)])
print("DETERMINISTIC — decoded-RGBA + manifest identical across re-render")
PY

# (3) Import purity: render.py imports only stdlib + PIL + local measure (no network libs)
python3 - <<'PY'
import ast, sys
src=open("tools/marketing-render/render.py").read()
mods=set()
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.Import): mods|={a.name.split('.')[0] for a in n.names}
    elif isinstance(n, ast.ImportFrom) and n.module: mods.add(n.module.split('.')[0])
allowed={"os","sys","re","json","math","hashlib","argparse","pathlib","typing","measure","PIL"}
extra=mods-allowed
print("imports:", sorted(mods)); sys.exit(1 if extra else 0)
PY

# (4) Fonts vendored + no system/ruflo font path referenced in source
python3 - <<'PY'
import os,sys
d="tools/marketing-render/fonts"
need=["Inter-Regular.ttf","Inter-Medium.ttf","Inter-SemiBold.ttf","Inter-Bold.ttf","OFL.txt"]
missing=[f for f in need if not os.path.exists(os.path.join(d,f))]
assert not missing, "missing vendored font/license: "+str(missing)
src=open("tools/marketing-render/render.py").read()
for bad in ("/System/Library/Fonts","/opt/homebrew","/Library/Fonts"):
    assert bad not in src, "renderer references non-vendored font path: "+bad
print("fonts vendored, OFL present, no external font path")
PY
```

## 9. Evaluator attack script (adversarial — dims, tokens, schema, safe-zone, anti-stub)

Run after §8 command (1). Every assertion must hold:

```bash
python3 - <<'PY'
import json, sys
from PIL import Image
sys.path.insert(0, "tools/marketing-render")
import measure as m
A="content/2026-07-03-hyd-premium-vs-budget"
mani=json.load(open(f"{A}/render/manifest.json"))

assert mani["schema_version"]=="1"
assert mani["slug"]=="2026-07-03-hyd-premium-vs-budget"
surfaces=mani["surfaces"]
assert len(surfaces)==8, len(surfaces)

BG="#faf8f3"
def near(px, hexcol, tol=24):
    r,g,b=int(hexcol[1:3],16),int(hexcol[3:5],16),int(hexcol[5:7],16)
    return abs(px[0]-r)<=tol and abs(px[1]-g)<=tol and abs(px[2]-b)<=tol

hooks=0
for s in surfaces:
    assert s["role"]=="carousel-slide"
    assert s["canvas"]=={"w":1080,"h":1350}
    img=Image.open(f"{A}/render/{s['png']}").convert("RGB")
    # (V2) real pixel dims from bytes
    assert img.size==(1080,1350), (s["id"], img.size)
    # (bg dominance) bg token must dominate the canvas — a wrong/omitted/gradient
    # fill would otherwise pass every other check (V3 only proves declared ink exists).
    # 2000 deterministic strided samples; text+elements occupy <10% of a slide, so
    # >=90% (1800/2000) of samples must land on the bg token.
    px=img.load(); W,H=img.size
    bgc=sum(1 for _ in range(2000) if near(px[(7*_)%W, (13*_)%H], BG))
    assert bgc >= 1800, (s["id"], "bg does not dominate canvas", bgc)
    for el in s["elements"]:
        # every color/bg is a locked brand token
        assert m.is_brand_token(el["color"]), el["color"]
        assert m.is_brand_token(el["bg"]) and el["bg"]==BG, el["bg"]
        role=el["role"]; fpx=el["font_px"]
        if role=="hook": hooks+=1
        # (V5 first-half) type-size minimums via measure
        assert m.type_min_ok("carousel-slide", role, fpx)["passes"], (s["id"],role,fpx)
        # (V6) safe zone for headline/body/hook (source-stamp/wordmark exempt)
        if role in ("headline","body","hook"):
            assert m.safe_zone_ok(1080,1350, el["bbox"])["passes"], (s["id"],role,el["bbox"])
        # (V3 anti-stub) declared-color ink actually present inside the bbox
        x,y,w,h=el["bbox"]
        crop=img.crop((x,y,x+w,y+h)); cpx=crop.load()
        cw,ch=crop.size
        ink=sum(1 for yy in range(0,ch,3) for xx in range(0,cw,3) if near(cpx[xx,yy], el["color"], 60))
        assert ink>0, ("BLANK/STUB PNG — no declared ink in bbox", s["id"], role, el["text"][:30])

# exactly one hook, on slide 1
assert hooks==1, hooks
s1=[s for s in surfaces if s["id"]=="carousel-01"][0]
hook_el=[e for e in s1["elements"] if e["role"]=="hook"][0]
assert len(hook_el["text"].split())<=10, ("hook >10 words", hook_el["text"])
# source-stamp present on the source slide (S8) and the chart slide (S3)
for sid in ("carousel-03","carousel-08"):
    s=[x for x in surfaces if x["id"]==sid][0]
    stamps=[e for e in s["elements"] if e["role"]=="source-stamp"]
    assert stamps, ("missing source-stamp", sid)
    txt=stamps[0]["text"]
    assert "Source" in txt and "as of" in txt, txt
# wordmark present on S8, accent-deep, literal TERREM
s8=[x for x in surfaces if x["id"]=="carousel-08"][0]
wm=[e for e in s8["elements"] if e["role"]=="wordmark"][0]
assert wm["text"]=="TERREM" and wm["color"]=="#0d3d38", wm

# (exact-text) every authored copy string from §5 MUST appear verbatim in the manifest,
# matched by (role, text) so slides with two body elements are handled. This closes the
# "silent omission / stale copy / mid-word corruption" loophole — the manifest cannot
# claim structure while dropping or mangling sentences.
expected = {
    "carousel-01": [
        ("hook", "Jubilee Hills just got cheaper. Medchal rose 19%."),
        ("body", "Same city. Same 3 months."),
    ],
    "carousel-02": [
        ("headline", "\"Hyderabad prices are rising\" is a meaningless sentence."),
        ("body", "The city moved in opposite directions by 28 points last quarter. Which direction did YOUR locality move?"),
    ],
    "carousel-03": [
        ("body", "3-month price change, every tracked locality."),
        ("source-stamp", "Source: TERREM Intelligence · 302,156 Hyderabad transactions · as of 2026-03-08"),
    ],
    "carousel-04": [
        ("headline", "The premium core blinked."),
        ("body", "Banjara Hills −3.0% · Punjagutta −3.4% · Jubilee Hills −6.1% · Begumpet −8.0%. If you've been priced out of these localities, this is the first soft quarter in a while."),
    ],
    "carousel-05": [
        ("headline", "Meanwhile, the budget corridors ran."),
        ("body", "Medchal +19.2% · Ameerpet +12.7% · Tarnaka +12.7% · Dilsukhnagar +11.3%. Waiting has been expensive at the entry level — ₹-per-sqft there is climbing fastest."),
    ],
    "carousel-06": [
        ("headline", "Before you panic-buy or panic-sell:"),
        ("body", "Over 12 months most \"falling\" localities are still up (Gopanpally: −5.9% this quarter, +11.6% on the year). This is a 3-month turn, not a crash. Trends ≠ guarantees."),
    ],
    "carousel-07": [
        ("headline", "Check your locality before your next site visit."),
        ("body", "Every locality, every trend, updated continuously. Free."),
        ("body", "intel.terrem.in/markets"),
    ],
    "carousel-08": [
        ("source-stamp", "Source: TERREM Intelligence · 302,156 Hyderabad transactions · as of 2026-03-08"),
        ("body", "intel.terrem.in/markets"),
        ("wordmark", "TERREM"),
    ],
}
for sid, pairs in expected.items():
    surf=[x for x in surfaces if x["id"]==sid][0]
    got={(e["role"], e["text"]) for e in surf["elements"]}
    for role, text in pairs:
        assert (role, text) in got, ("MISSING/CORRUPT COPY", sid, role, repr(text), "actual:", sorted(got))
    # no phantom text elements beyond what §5 enumerates (drop/dedupe exact matches)
    assert len(surf["elements"])==len(pairs), (sid, "element count", len(surf["elements"]), "!=", len(pairs), sorted(got))

print("OK — dims, tokens, schema, bg-dominance, exact-copy, one-hook, hook<=10 words, safe zones, ink-present all hold")
PY
```

(The `near`-sampling loop uses fixed strided indices — deterministic, no randomness in the check.)

## 10. Definition of done

- The seven created files in §2 exist; the three carousel.md edits in §3.4 are applied; nothing
  else is created or modified.
- `python3 -m unittest discover -s tools/marketing-render/tests -v` exits 0.
- `render.py` renders the hyd asset to eight `1080×1350` PNGs + `manifest.json` under `render/`,
  exit 0, writing nowhere else.
- §8 determinism, import-purity, and font-vendoring checks pass; §9 attack script prints `OK`.
- Error states in §6 each exit non-zero with a specific message and leave no partial output.
- `generator_trace.log` records commands run and their output.

## 11. Non-goals (this sprint)

- No `1080×1920` chart card; no plotted charts (bars/lines) inside carousel slides — Sprint 003.
- No validator, no `qa-verdict.json`, no `meta.md` verdict append, no contrast/axis/blacklist/
  provenance enforcement — Sprint 004 (Sprint 002 only *emits* the manifest those checks consume;
  it does not run them, beyond the token/dims/ink self-checks above).
- No `qa-checklist.md` "IBM Plex Sans → Inter" edit — Sprint 004.
- No claim that the (killed) hyd asset passes QA.
- No new third-party dependency beyond Pillow; no network at render time; no writes outside the
  repo or outside `<asset-folder>/render/`.
