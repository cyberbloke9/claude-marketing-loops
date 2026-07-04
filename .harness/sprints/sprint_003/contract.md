# Sprint 003 Contract — Chart-card renderer + TGRERA receipts spec

Status: PROPOSED
Sprint: 003
Depends on: Sprint 001 (`tools/marketing-render/measure.py`, PASSED), Sprint 002 (`tools/marketing-render/render.py` carousel renderer, PASSED).
Spec refs: §5.1 (R2, R3, R4, R5, R6, R7, R8, R9), §5.3 (manifest schema — chart-card surface), §6 (states), §7 (design), §9 (tokens/fonts/no-network), §11 (Sprint 003), Risk 2 (author TGRERA chart-spec as `has_axis:false` receipts card), Risk 3 (axis detection is flag-based, deferred), Risk 4 (glyph-size seam).

## 0. Purpose, boundary & why there is no Playwright path

This sprint builds the **vertical chart-card renderer** and authors the **TGRERA reference `chart-spec.md`**. It extends the existing `render.py` so that:

1. It reads `content/<slug>/chart-spec.md`, and **when that spec declares a chart card** (an explicit `Surface: chart-card` marker), renders one `1080×1920` vertical PNG using vendored Inter + locked tokens, with an on-graphic **source stamp** and the **TERREM wordmark** (R2, R6).
2. It emits a **chart-card surface** into `content/<slug>/render/manifest.json` (§5.3 schema), listing every text element drawn.
3. It authors `content/2026-07-03-tgrera-enforcement-wave/chart-spec.md` as a **receipts / data card** (`has_axis: false`) carrying the three public TGRERA orders (Risk 2), and renders + demonstrates it end-to-end at the render level.

It is a **headless CLI raster tool** (same as Sprint 002) — there is **no browser / web UI**, so **no Playwright click-path exists**. The Evaluator attacks the CLI directly and inspects the produced PNG + manifest with the Python probes in §8/§9. This is intentional and stated so the contract is fully testable.

**In scope (Sprint 003):** the `1080×1920` chart-card render for a `has_axis:false` receipts card (roles: `headline`, `body`, `source-stamp`, `wordmark`); the chart-card `manifest.json` surface merged alongside any carousel surfaces; the authored TGRERA `chart-spec.md`; deterministic re-render; error/atomicity states; **strict non-regression of the Sprint-002 hyd carousel output**.

**Explicitly NOT in this sprint** (declared, not silently omitted):
- **No plotted-axis / bar-chart engine.** Spec §11's "zero-based axis when `has_axis`" is a *conditional capability* (R5: "*when* it plots a numeric axis"). No required downstream test renders a plotted axis: the Sprint 003 test is the receipts card; Sprint 004 validates TGRERA which is `has_axis:false`; Sprint 005's "truncated axis → V10 FAIL" is **flag-based** (Risk 3 — a hand-crafted manifest with `axis_min≠0 && break_disclosed=false`, not a rendered plot). Building a matplotlib/Pillow bar engine would add real surface that jeopardizes **R8 (hard determinism)** for zero required payoff — the "widen scope because it's convenient" the harness forbids. A `chart-spec.md` that declares `has_axis: true` is **rejected with a fail-loud error** this sprint (§3.5). The plotted path is a Sprint 004+/future concern.
- No validator, `qa-verdict.json`, contrast/blacklist/provenance enforcement — Sprint 004. Sprint 003 only *emits* the chart-card manifest those checks will consume.
- **No edit to `content/2026-07-03-tgrera-enforcement-wave/meta.md`** (its provenance/verdict block is Sprint 004 / V11 territory). No `qa-checklist.md` "IBM Plex Sans → Inter" edit (Sprint 004).
- No TGRERA carousel (Risk 2 makes a full TGRERA carousel optional/out-of-scope); only the chart card is required for TGRERA.
- No LinkedIn 1200×627 / PDF carousel (§8 non-goals). No new third-party dependency beyond Pillow. No network at render time. No writes outside `<asset-folder>/render/`.

### Scope-honesty note
The TGRERA asset's `meta.md` records a specs-level QA PASS on provenance (public regulator orders only, no TERREM DB numbers). Sprint 003 proves **rendering correctness** of the chart card (dims, tokens, source-stamp + wordmark presence, safe-zone fit, anti-stub ink, determinism). A full QA verdict is Sprint 004 (V2–V12). Do not score Sprint 003 on whether the asset "should publish" — score it on whether the renderer faithfully rasterizes the authored receipts card and does not regress the hyd carousel.

## 1. Language / runtime decision

- **Python 3** (`/usr/bin/python3`, 3.9.6) + **Pillow** (already installed) — same runtime as Sprint 002. Pillow gives deterministic freetype raster at fixed pixel sizes (R8) with zero network (R4).
- **No new third-party dependency beyond Pillow.** No `pip install`, no `matplotlib`, no network. Imports allowed in `render.py`: Python stdlib + `PIL` + the local `measure` module (unchanged from Sprint 002's import set).
- Reuses `measure.py` (`TOKENS`, `is_brand_token`, `type_min_ok`, `safe_zone_ok`) and Sprint 002's font-loading / wrap / glyph-guard / determinism machinery verbatim.

## 2. Files this sprint creates / modifies (and ONLY these)

Creates:
- `content/2026-07-03-tgrera-enforcement-wave/chart-spec.md` — the authored `has_axis:false` receipts card (grammar in §3, exact content in §4).
- `tools/marketing-render/tests/test_chart_card.py` — stdlib `unittest` tests for the chart-card path (see §8.0). A **separate** test file so the Sprint-002 `test_render.py` suite is left byte-untouched (regression safety).

Modifies (additively — must not change existing carousel behavior):
- `tools/marketing-render/render.py` — adds: chart-spec parsing (§3), chart-card layout + render (§5), and a merged `main()`/`render_asset()` flow (§6) that renders a carousel **and/or** a chart card. The existing carousel functions, constants, style table, and CLI error messages are **preserved**; only the top-level orchestration is generalized so a missing `carousel.md` is no longer fatal when a chart-spec is present.

Writes at render time (created by the tool, not committed as source):
- `content/2026-07-03-tgrera-enforcement-wave/render/chart-card.png`
- `content/2026-07-03-tgrera-enforcement-wave/render/manifest.json`

Does **NOT** modify: `measure.py`, `test_render.py`, any `brand/` file, `qa-checklist.md`, the hyd asset (`content/2026-07-03-hyd-premium-vs-budget/**` — including its `chart-spec.md`), TGRERA's `meta.md` / `script.md`, or any file outside this repo.

## 3. Input grammar — how `chart-spec.md` is parsed (deterministic)

The renderer reads `content/<slug>/chart-spec.md` as UTF-8 and parses it line-by-line. The grammar is authored by this sprint (§4), so it is deterministic and unambiguous by construction.

### 3.1 Chart-card trigger (the hyd-safety seam)
A `chart-spec.md` is rendered as a chart card **only if** it contains a line matching `^Surface:\s*chart-card\s*$`. If no such marker is present, the file is **not a chart-card spec**: the renderer ignores it entirely (renders no chart card, raises no error). This is the mechanism that keeps the **hyd asset byte-identical**: hyd's existing `chart-spec.md` is the old free-form bar-chart format (`Chart type: diverging horizontal bar`, `Y-axis: …`) with **no** `Surface: chart-card` line, so it is skipped and hyd's manifest stays the 8 carousel surfaces of Sprint 002.

### 3.2 Preprocessing
1. Split into lines. Strip HTML comments `<!-- … -->` (non-greedy) then trailing whitespace (same rule as Sprint 002 §3.1).
2. Blank lines and bare `---` separators are skipped.
3. If the spec is inside a fenced ```` ``` ```` code block, the fence lines (```` ``` ````) are skipped; the directive lines inside are parsed normally.

### 3.3 Directive / element extraction (in file order)
Each recognized line yields either a **directive** (surface metadata, no element) or exactly **one manifest element**:

| Line pattern | Kind | Role | Font px | Weight | Color token | Notes |
|---|---|---|---|---|---|---|
| `^Surface:\s*chart-card\s*$` | directive | — | — | — | — | required trigger (§3.1) |
| `^Canvas:\s*(.+)$` | directive | — | — | — | — | must equal `1080x1920` (§3.5) |
| `^has_axis:\s*(true\|false)\s*$` | directive | — | — | — | — | must be `false` this sprint (§3.5) |
| `^Headline:\s*(.+)$` | element | `headline` | 44 | 700 | `ink` `#1c1917` | ≥1 per card |
| `^Order:\s*(.+)$` | element | `body` | 27 | 500 | `ink` `#1c1917` | the dated receipts |
| `^Source:\s*(.+)$` | element | `source-stamp` | 20 | 400 | `ink-muted` `#57534e` | rendered text **includes** the `Source:` prefix (verbatim whole line, matching Sprint 002 so V8 finds "Source" + "as of") |
| line containing `wordmark` (case-insensitive), e.g. `^Wordmark:\s*TERREM` | element | `wordmark` | 25 | 700 | `accent-deep` `#0d3d38` | literal rendered text is `TERREM`, bottom-right |

Text is taken **verbatim** from the captured group (₹, `—`, `·`, `%`, `/` preserved); only the leading marker + surrounding whitespace are stripped. Every emitted `color`/`bg` is validated with `measure.is_brand_token(...)`.

### 3.4 Element ordering & required elements
- Elements appear in the manifest in **file order**.
- A chart-card spec **must** produce: ≥1 `headline`, ≥1 `source-stamp`, and exactly one `wordmark`. Missing any → fail-loud `ValueError` (§3.5). (Source-stamp + wordmark presence is R6 and is what the Sprint-004 V8 gate will consume.)

### 3.5 Fail-loud rules (state §6)
- `has_axis: true` → `ValueError: "plotted-axis chart cards are not supported in Sprint 003 (non-goal); this card declares has_axis: true"`. (No silent skip, no half-rendered plot.)
- `Canvas:` value ≠ `1080x1920` → `ValueError` naming the offending value.
- A non-blank line that matches none of the §3.3 patterns → `ValueError` naming the offending line (fail loud, no silent drop).
- A chart-card spec missing a required element (§3.4) → `ValueError` naming which is missing.

## 4. The authored TGRERA `chart-spec.md` (exact content)

`content/2026-07-03-tgrera-enforcement-wave/chart-spec.md` is authored as a `has_axis:false` receipts card. **Every fact below traces to the existing public sources already in the asset** (`script.md`, `meta.md`, `signals/2026-07-03.md #3`: NewsMeter · Siasat · Deccan Chronicle; orders dated 2026-06-22/27/30) — **no TERREM DB numbers**, satisfying the provenance-safety constraint (§9, Risk 2). The file body (inside a fenced block) is:

```
Surface: chart-card
Canvas: 1080x1920
has_axis: false

Headline: Telangana's regulator hit three builders in nine days.
Order: Jun 22 — R Homes: ordered to refund Rs 14.95L + 10.7% interest for pre-registration collection; project sales frozen.
Order: Jun 27 — Maharshi's Estates: penalty proceedings for selling plots in a project that was never registered.
Order: Jun 30 — Jayatri Infrastructure: refund with interest on a delayed Gopanpally project; 45 days to pay.
Source: Source: NewsMeter · Siasat · Deccan Chronicle · TGRERA orders as of 2026-06-22 / 27 / 30
Wordmark: TERREM
```

Notes:
- The `Source:` line intentionally repeats the word (`Source: Source: …`) so the captured element text is the full `Source: NewsMeter · …` stamp (the parser renders the whole line after the first `Source:` marker). The rendered source-stamp text is `Source: NewsMeter · Siasat · Deccan Chronicle · TGRERA orders as of 2026-06-22 / 27 / 30` — contains "Source" **and** "as of" **and** the order dates (V8-ready).
- **Currency rendered as `Rs 14.95L`, not `₹`** — deliberate: this keeps the authored spec ASCII-safe and dodges any font-coverage risk on the rupee glyph in the receipts copy. (The hyd carousel proves `₹` renders; here we simply don't need it. The anti-tofu guard §5.4 still runs regardless.)
- All punctuation used (`—` em dash, `·` middot, `%`, `/`, `+`) is confirmed present in vendored Inter (Sprint 002).

## 5. Chart-card renderer behavior

### 5.1 CLI (unchanged surface)
```
python3 tools/marketing-render/render.py <asset-folder>
```
`<asset-folder>` = path to `content/<slug>/`. On success: renders whatever surfaces the folder declares (carousel and/or chart card), prints one line per PNG + the manifest path, exits **0**. Reads only the asset's `carousel.md` / `chart-spec.md` and the vendored fonts. No network.

### 5.2 Canvas & tokens (R2, R3)
- The chart-card PNG is exactly `1080×1920`, flat-filled with `bg` `#faf8f3`. No gradients, textures, or images under type (§7 anti-patterns).
- Only the tokens in §3.3 appear as declared element colors: `ink` `#1c1917`, `ink-muted` `#57534e`, `accent-deep` `#0d3d38` (wordmark). All are members of the nine locked tokens. **Zero content-accent** is used (permitted; §7 allows 0 or 1 accent, never >1) — the single `accent-deep` element is the wordmark.

### 5.3 Layout (deterministic integer math; vertical safe zone)
- Text column reuses `MARGIN_X = 90`, `CONTENT_W = 900` (x ∈ [90, 990], inside the vertical canvas [0, 1080]).
- **Critical stack** = the `headline` + all `body` (order) elements, laid out top-to-bottom with the same wrap (`getlength` greedy), line-advance `round(font_px*1.4)`, em-height `round(font_px*1.2)`, and inter-element gap `round(0.7*preceding_font_px)` as Sprint 002. The whole critical stack is **vertically centered** inside the band `y ∈ [280, 1300]`. Because `280 ≥ 250` and `1300 ≤ 1480`, every headline/body element is inside the vertical safe zone `y ∈ [250, 1480]` (`measure.SAFE_ZONES[(1080,1920)]`) **by construction**. If the stack is taller than the band (`1020px`), the renderer **errors (fail loud)** rather than overflowing.
- **Source-stamp** is drawn left-aligned at `x = 90`, top `y = 1380` (below the critical band, still `< 1480` so it sits inside the safe zone — extra-safe, though source-stamp is V6-exempt).
- **Wordmark** (`TERREM`) is drawn bottom-right: right edge `x = 990`, top `y = 1800` (in the bottom-440 zone — V6-exempt; bottom-right is the brand convention R6).

### 5.4 Anti-tofu glyph guard (reused)
Before drawing any run, the renderer confirms every non-whitespace char has a real glyph in the chosen Inter face (Sprint 002 `.notdef` comparison). A missing glyph raises `RuntimeError` naming the char, the surface, and the element role — never a silent `.notdef` box.

### 5.5 Manifest emission (§5.3 schema — chart-card surface)
The chart-card surface merged into `manifest.json`:
```json
{
  "id": "chart-card",
  "role": "chart-card",
  "png": "chart-card.png",
  "canvas": { "w": 1080, "h": 1920 },
  "has_axis": false,
  "axis_min": null,
  "zero_based": null,
  "break_disclosed": null,
  "chart_ref": null,
  "elements": [
    { "text": "Telangana's regulator hit three builders in nine days.",
      "role": "headline", "font_px": 44, "weight": 700,
      "color": "#1c1917", "bg": "#faf8f3", "bbox": [90, 0, 0, 0] }
  ]
}
```
- Axis-only fields are `null` because `has_axis=false` (schema §5.3 rule). `chart_ref` is `null` (the card *is* the receipts, not a reference to a plot) — included for surface-shape parity with the Sprint-002 carousel surfaces.
- `bbox` values are layout-computed; the enumerated exact values in §5.6 pin roles/text/size/color, while bboxes are verified by **invariant** (dims, safe-zone containment, ink-present), not by hard-coded pixels.
- **Serialization is byte-deterministic:** `json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)` + trailing newline. No timestamp/date field anywhere.

### 5.6 Exact expected chart-card manifest for TGRERA (the renderer↔validator seam)
One surface `chart-card`, `1080×1920`, role `chart-card`, `has_axis=false`. Elements (role · font_px · weight · color · text), **in this order**:
1. `headline` · 44 · 700 · `#1c1917` · `Telangana's regulator hit three builders in nine days.`
2. `body` · 27 · 500 · `#1c1917` · `Jun 22 — R Homes: ordered to refund Rs 14.95L + 10.7% interest for pre-registration collection; project sales frozen.`
3. `body` · 27 · 500 · `#1c1917` · `Jun 27 — Maharshi's Estates: penalty proceedings for selling plots in a project that was never registered.`
4. `body` · 27 · 500 · `#1c1917` · `Jun 30 — Jayatri Infrastructure: refund with interest on a delayed Gopanpally project; 45 days to pay.`
5. `source-stamp` · 20 · 400 · `#57534e` · `Source: NewsMeter · Siasat · Deccan Chronicle · TGRERA orders as of 2026-06-22 / 27 / 30`
6. `wordmark` · 25 · 700 · `#0d3d38` · `TERREM`

Element count = **6**. Contrast sanity (verified for real in Sprint 004, noted here): ink/bg ≈ 16.5:1, ink-muted/bg ≈ 6.5:1, accent-deep/bg high — all ≥ 4.5:1. Type minimums (chart-card): headline 44 ≥ 36 ✓; body 27 ≥ 24 ✓ (source-stamp/wordmark exempt).

### 5.7 Determinism (R8) & atomicity (R9) — reused verbatim
No timestamps, no run-varying metadata; fonts vendored + fixed; layout is pure integer math; PNG saved with Pillow's default writer. Determinism is asserted on **decoded-RGBA SHA-256**. The renderer builds every image + the manifest **in memory** and only writes after all surfaces render successfully; on any error it writes nothing and exits non-zero, writing **only** inside `<asset-folder>/render/`.

## 6. Merged render flow & states (mapped to spec §6)

`render_asset(folder)` now:
1. If neither `carousel.md` nor a chart-card `chart-spec.md` (with the §3.1 marker) is present → error `no renderable input (need carousel.md or a chart-spec.md with 'Surface: chart-card') in <path>`, exit non-zero, no writes.
2. If `carousel.md` present → render carousel surfaces (unchanged Sprint 002 path).
3. If `chart-spec.md` present **and** carries the §3.1 marker → render the chart-card surface.
4. Merge surfaces (carousel surfaces first, then chart-card) into one `manifest.json`. For TGRERA (no `carousel.md`) the manifest has exactly the one `chart-card` surface.

State matrix:
- **Missing asset folder** → `error: asset folder not found: <path>`, exit 1, no writes (unchanged).
- **Folder with neither input** → error as (1) above, exit 1, no writes. (Preserves the Sprint-002 `test_missing_carousel` behavior: an empty folder still exits 1 with no `render/`.)
- **`chart-spec.md` present without the marker** (e.g. hyd) → chart card skipped; if `carousel.md` also present, only the carousel renders (hyd stays 8 surfaces, byte-identical).
- **Unparseable chart-spec line / `has_axis:true` / bad `Canvas:` / missing required element** → `ValueError` (§3.5), exit 1, no writes.
- **Missing glyph (tofu)** → `RuntimeError` naming char/surface/role, exit 1, no writes.
- **Stack overflow (content too tall for the [280,1300] band)** → error, exit 1, no writes.
- **Success (TGRERA)** → one `1080×1920` `chart-card.png` + `manifest.json` under `render/`, exit 0.
- **Deterministic re-render** → second run yields byte-identical manifest + decoded-RGBA-identical PNG.
- **Anti-stub** → declared ink present inside every text bbox (no blank PNG).

## 7. Design fidelity (§7)

Inter only (700 headline, 500 body/receipts, 400 source-stamp, 700 wordmark); locked tokens only; flat `bg` canvas; no gradients/textures/photos under type; no all-lowercase headline; no condensed/thin faces. Zero content-accent + one `accent-deep` wordmark (≤1 accent honored). Tufte-clean by omission — the receipts card carries no chartjunk because it plots nothing (R5 vacuous for `has_axis:false`). Left-aligned editorial text, 1.4 line advance, on-graphic source + as-of date (R6), TERREM wordmark bottom-right (R6).

## 8. Commands the Evaluator runs

From repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`:

```bash
# (0) Unit tests — existing carousel suite MUST still pass + new chart-card suite. Exit 0.
python3 -m unittest discover -s tools/marketing-render/tests -v

# (1) Render the TGRERA asset — exit 0, writes render/ only
python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave
ls content/2026-07-03-tgrera-enforcement-wave/render/
# expect: chart-card.png  manifest.json   (and nothing else)

# (2) Determinism (R8): render twice; decoded-RGBA SHA-256 identical; manifest byte-identical
python3 - <<'PY'
import subprocess, hashlib, os
from PIL import Image
A="content/2026-07-03-tgrera-enforcement-wave"
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

# (3) HYD NON-REGRESSION: re-render hyd; it must still be 8 carousel surfaces, NO chart card
python3 - <<'PY'
import subprocess, json
A="content/2026-07-03-hyd-premium-vs-budget"
subprocess.run(["python3","tools/marketing-render/render.py",A],check=True)
m=json.load(open(f"{A}/render/manifest.json"))
roles=[s["role"] for s in m["surfaces"]]
assert roles==["carousel-slide"]*8, ("HYD REGRESSED", roles)
assert not any(s["role"]=="chart-card" for s in m["surfaces"]), "hyd's chart-spec.md was wrongly rendered as a chart card"
print("HYD intact — 8 carousel surfaces, no chart card (chart-spec.md correctly skipped)")
PY

# (4) Import purity: render.py still imports only stdlib + PIL + local measure
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
```

## 9. Evaluator attack script (adversarial — dims, tokens, schema, safe-zone, anti-stub, exact copy)

Run after §8 command (1). Every assertion must hold:

```bash
python3 - <<'PY'
import json, sys
from PIL import Image
sys.path.insert(0, "tools/marketing-render")
import measure as m
A="content/2026-07-03-tgrera-enforcement-wave"
mani=json.load(open(f"{A}/render/manifest.json"))

assert mani["schema_version"]=="1"
assert mani["slug"]=="2026-07-03-tgrera-enforcement-wave"
surfaces=mani["surfaces"]
assert len(surfaces)==1, len(surfaces)
s=surfaces[0]
assert s["id"]=="chart-card" and s["role"]=="chart-card"
assert s["canvas"]=={"w":1080,"h":1920}
assert s["has_axis"] is False
assert s["axis_min"] is None and s["zero_based"] is None and s["break_disclosed"] is None

BG="#faf8f3"
def near(px, hexcol, tol=24):
    r,g,b=int(hexcol[1:3],16),int(hexcol[3:5],16),int(hexcol[5:7],16)
    return abs(px[0]-r)<=tol and abs(px[1]-g)<=tol and abs(px[2]-b)<=tol

img=Image.open(f"{A}/render/{s['png']}").convert("RGB")
# (V2) real pixel dims from bytes
assert img.size==(1080,1920), img.size
# (bg dominance) bg token must dominate the canvas (text is sparse on a 1080x1920 card)
px=img.load(); W,H=img.size
bgc=sum(1 for i in range(2000) if near(px[(7*i)%W, (13*i)%H], BG))
assert bgc >= 1900, ("bg does not dominate canvas", bgc)

roles=[e["role"] for e in s["elements"]]
assert roles.count("headline")>=1 and roles.count("source-stamp")>=1 and roles.count("wordmark")==1, roles

for el in s["elements"]:
    assert m.is_brand_token(el["color"]), el["color"]
    assert m.is_brand_token(el["bg"]) and el["bg"]==BG, el["bg"]
    role=el["role"]; fpx=el["font_px"]
    # (V5) chart-card type minimums via measure (headline>=36, body>=24; stamp/wordmark exempt)
    assert m.type_min_ok("chart-card", role, fpx)["passes"], (role, fpx)
    # (V6) vertical safe zone for critical roles (source-stamp/wordmark exempt)
    if role in ("headline","body","hook"):
        assert m.safe_zone_ok(1080,1920, el["bbox"])["passes"], (role, el["bbox"])
    # (V3 anti-stub) declared-color ink actually present inside the bbox
    x,y,w,h=el["bbox"]
    assert w>0 and h>0, ("degenerate bbox", role, el["bbox"])
    crop=img.crop((x,y,x+w,y+h)); cpx=crop.load(); cw,ch=crop.size
    ink=sum(1 for yy in range(0,ch,3) for xx in range(0,cw,3) if near(cpx[xx,yy], el["color"], 60))
    assert ink>0, ("BLANK/STUB PNG — no declared ink in bbox", role, el["text"][:30])

# (V8) source-stamp carries source attribution + as-of date
stamp=[e for e in s["elements"] if e["role"]=="source-stamp"][0]
assert "Source" in stamp["text"] and "as of" in stamp["text"], stamp["text"]
assert "2026-06-22" in stamp["text"], stamp["text"]

# (R6) wordmark: literal TERREM, accent-deep, right-anchored (right edge near x=990)
wm=[e for e in s["elements"] if e["role"]=="wordmark"][0]
assert wm["text"]=="TERREM" and wm["color"]=="#0d3d38", wm
wx,wy,ww,wh=wm["bbox"]
assert wx+ww==990, ("wordmark not right-anchored", wm["bbox"])

# (exact copy) every authored element string must appear verbatim by (role,text); count == 6
expected=[
  ("headline","Telangana's regulator hit three builders in nine days."),
  ("body","Jun 22 — R Homes: ordered to refund Rs 14.95L + 10.7% interest for pre-registration collection; project sales frozen."),
  ("body","Jun 27 — Maharshi's Estates: penalty proceedings for selling plots in a project that was never registered."),
  ("body","Jun 30 — Jayatri Infrastructure: refund with interest on a delayed Gopanpally project; 45 days to pay."),
  ("source-stamp","Source: NewsMeter · Siasat · Deccan Chronicle · TGRERA orders as of 2026-06-22 / 27 / 30"),
  ("wordmark","TERREM"),
]
got=[(e["role"],e["text"]) for e in s["elements"]]
assert got==expected, ("COPY/ORDER MISMATCH", got)

print("OK — dims, tokens, schema, bg-dominance, type-min, vertical safe-zone, anti-stub ink, source-stamp+date, wordmark right-anchored, exact-copy all hold")
PY
```

(The `near`-sampling loop uses fixed strided indices — deterministic, no randomness.)

## 10. Definition of done

- The two created files in §2 exist (`chart-spec.md`, `test_chart_card.py`); `render.py` is modified additively; **nothing else** is created or modified (verify with `git status --porcelain` / `git diff --name-only` → only `render.py`, the two new files, and the TGRERA `render/` outputs).
- `python3 -m unittest discover -s tools/marketing-render/tests -v` exits 0 (existing carousel tests + new chart-card tests).
- `render.py` renders the TGRERA asset to one `1080×1920` `chart-card.png` + `manifest.json` under `render/`, exit 0, writing nowhere else.
- §8 determinism (2), hyd non-regression (3), and import-purity (4) checks pass; §9 attack script prints `OK`.
- Error states in §6 each exit non-zero with a specific message and leave no partial output.
- `generator_trace.log` records commands run and their output/evidence.

## 11. Non-goals (this sprint) — restated

- No plotted-axis / bar-chart rendering engine (§0 rationale + Risk 3); `has_axis:true` is rejected fail-loud.
- No validator, `qa-verdict.json`, `meta.md` verdict append, or contrast/axis/blacklist/provenance enforcement — Sprint 004.
- No edit to TGRERA `meta.md` / `script.md`, no `qa-checklist.md` edit, no change to the hyd asset or `measure.py` / `test_render.py`.
- No TGRERA carousel; no LinkedIn/PDF surfaces; no new third-party dependency beyond Pillow; no network at render time; no writes outside `<asset-folder>/render/`.
