# Sprint 001 Contract — Measurement Core (pure, unit-tested, no rendering)

Status: PROPOSED
Sprint: 001
Depends on: none (foundation)
Spec refs: §5.2 (V4, V5, V6, V9), §5.3 (token rule), §9 (locked tokens), §11 (Sprint 001), Risk 1, Risk 4.

## 0. Purpose & boundary

This sprint builds the **pure measurement library** that later sprints (renderer, validator)
call. It renders nothing, opens no PNG, reads no manifest, and performs no I/O except:
(a) reading `brand/brand-kit.md` to parse the blacklist (V9, single-source rule).

Everything is deterministic pure computation over numbers, hex strings, and bounding boxes.
There is **no UI** in this sprint, so there is no Playwright click-path — the Evaluator
attacks the library directly via a Python script / REPL. This is intentional and stated so
the contract remains fully testable.

## 1. Language / runtime decision

- **Python 3** (the repo's `/usr/bin/python3`, currently 3.9.6). Chosen because later sprints
  render with Pillow (deterministic raster) and this keeps one toolchain.
- **Standard library only** in Sprint 001. No third-party packages, no `pip install`, no network.
- Tests use stdlib **`unittest`** (run via `python3 -m unittest`), so the Evaluator needs zero setup.

## 2. Files this sprint creates (and ONLY these)

- `tools/marketing-render/measure.py` — the pure measurement library (all functions in §4).
- `tools/marketing-render/tests/test_measure.py` — unit tests (stdlib `unittest`).

**No `__init__.py` files.** The parent directory name `marketing-render` contains a hyphen,
which is illegal in a Python module name; adding `__init__.py` would make `unittest discover`
try to compute a package name from the hyphenated dir and fail during collection. Instead,
`test_measure.py` puts the tool dir on `sys.path` at the top of the file before importing:

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import measure  # noqa: E402
```

This is the same path trick the §6 attack script uses, and it makes
`python3 -m unittest discover -s tools/marketing-render/tests` work without package markers.

No writes anywhere else in the repo. No edits to `brand/`, `content/`, or other tools this sprint.
(The `qa-checklist.md` "IBM Plex Sans" correction from Risk 1 is deferred to the validator sprint
where the Inter precedence rule is actually enforced — noted here so it is not forgotten.)

## 3. Locked constants (must appear in `measure.py`)

`TOKENS` — dict mapping token name → lowercase hex, exactly these nine and no others
(source of truth: `brand-kit.md §3` / spec §9):

```
bg          #faf8f3
surface     #ffffff
ink         #1c1917
ink-muted   #57534e
accent      #0f766e
accent-deep #0d3d38
chart-up    #0d9488
chart-down  #dc2626
border      #e0dbd3
```

`TOKEN_HEXES` — the set of those nine hex strings (lowercase).

## 4. Public functions (exact signatures & behavior)

Each function is pure (same input → same output), raises `ValueError` on malformed input
with a message naming the offending value, and never touches the network.

### 4.1 Color / contrast (V4)

- `normalize_hex(value: str) -> str`
  Accepts `#RRGGBB` or `RRGGBB`, any case; returns canonical lowercase `#rrggbb`.
  Raises `ValueError("invalid hex color: <value>")` for anything else (wrong length,
  non-hex chars, 3-digit shorthand is **rejected** — full 6-digit only, since all brand
  tokens are 6-digit).

- `relative_luminance(hex_color: str) -> float`
  WCAG 2.x relative luminance. For each channel c in {R,G,B}: `cs = c/255`;
  `lin = cs/12.92 if cs <= 0.03928 else ((cs+0.055)/1.055) ** 2.4`;
  `L = 0.2126*R_lin + 0.7152*G_lin + 0.0722*B_lin`. Returns a float in [0,1].

- `contrast_ratio(hex_a: str, hex_b: str) -> float`
  `(Llighter + 0.05) / (Ldarker + 0.05)`. Symmetric: `contrast_ratio(a,b) == contrast_ratio(b,a)`.
  Result in [1.0, 21.0].

- `is_large_text(font_px: float, weight: int) -> bool`
  Returns `True` if `font_px >= 24` **or** (`font_px >= 18.5` **and** `weight >= 700`).
  Otherwise `False`. (Matches spec V4 "large" definition; bold = weight ≥ 700.)

- `contrast_check(fg_hex: str, bg_hex: str, font_px: float, weight: int) -> dict`
  Returns `{"ratio": float, "threshold": 4.5 | 3.0, "large": bool, "passes": bool}`.
  `threshold = 3.0` when `is_large_text(...)` else `4.5`.
  **`passes` is computed on the raw full-precision ratio** (`raw_ratio >= threshold`), NOT on the
  rounded value — so a `4.497` cannot round up to `4.50` and falsely pass. The `ratio` field
  returned in the dict is that raw ratio rounded to 2 decimals **for display only**.

**Normative note on the brand-kit's stated ratios.** `brand-kit.md §3` annotates ink as
"~13:1" and accent as "~5:1". The correct WCAG 2.x computation yields `#1c1917`/`#faf8f3`
≈ **16.5:1** and `#0f766e`/`#faf8f3` ≈ **5.15:1**. This library implements the **WCAG formula**,
which is the spec's requirement (V4 says "computes WCAG 2.x relative-luminance contrast ratio").
The "~13:1" annotation is an approximation in the brand doc and is **not** the acceptance target.
The Evaluator must judge against the WCAG formula, not the brand-kit's rounded annotations.

### 4.2 Token validation (§5.3 token rule)

- `is_brand_token(hex_color: str) -> bool`
  `True` iff `normalize_hex(hex_color)` is in `TOKEN_HEXES`. Non-token hex → `False`
  (does not raise, so callers can report "color outside token set" themselves).

- `token_name(hex_color: str) -> str | None`
  Returns the token name (e.g. `"ink"`) for a token hex, else `None`.

### 4.3 Type-size minimums (V5, first half)

- `type_min_ok(surface_role: str, element_role: str, font_px: float) -> dict`
  `surface_role` ∈ {`"carousel-slide"`, `"chart-card"`}; `element_role` ∈
  {`"headline"`, `"hook"`, `"body"`, `"source-stamp"`, `"wordmark"`, `"chart-label"`}.
  Minimum table (px):

  | element_role | carousel-slide | chart-card |
  |---|---|---|
  | headline | 48 | 36 |
  | hook | 48 | 36 |
  | body | 24 | 24 |
  | source-stamp | exempt (None) | exempt (None) |
  | wordmark | exempt (None) | exempt (None) |
  | chart-label | exempt (None) | exempt (None) |

  Returns `{"minimum": <int or None>, "passes": <bool>}`. When minimum is `None` (exempt roles),
  `passes = True` always. Unknown `surface_role` or `element_role` → `ValueError` naming it.
  Rationale: `hook` is "biggest type on the slide" (brand-kit §6) so it takes the headline
  minimum; `chart-label`, `source-stamp`, `wordmark` are intentionally small and exempt from
  the size floor (but not from contrast — that is V4's job).

### 4.4 Glyph-size consistency cross-check (V5, second half; Risk 4)

- `SIZE_TOLERANCE = 0.25` (module constant).
- `size_consistent(declared_font_px: float, measured_px: float, tol: float = SIZE_TOLERANCE) -> bool`
  Returns `True` iff `declared_font_px * (1 - tol) <= measured_px <= declared_font_px * (1 + tol)`.
  This is a **generic band primitive**: it only fixes the tolerance (±25%, per Risk 4) and the
  band math. It does NOT define what `measured_px` means — that is deferred to Sprint 004.
  **Important seam note:** Sprint 004 will derive `measured_px` as an **em-scale** quantity
  (the ascent+descent line/em box that Pillow reports for the glyph run), NOT cap-height, and
  will be calibrated so a truthfully-declared Inter render lands inside ±25% of `declared_font_px`.
  (Cap-height ≈ 0.7×em would fall below the band and false-fail a correct render — that mapping
  is explicitly rejected.) In this sprint the function is validated purely as band math:
  a truthful value inside the band → `True`; a 2× lie (declared 48, measured 24 → `24 < 36`) → `False`.

### 4.5 Safe-zone containment (V6)

- `SAFE_ZONES` — dict keyed by `(canvas_w, canvas_h)`:
  - `(1080, 1350)` → `{"x_min":40, "y_min":40, "x_max":1040, "y_max":1310}` (carousel center rect).
  - `(1080, 1920)` → `{"x_min":0, "y_min":250, "x_max":1080, "y_max":1480}` (vertical; clear of
    top 250px and bottom 440px; x unconstrained per spec V6 which only bounds y for vertical).

- `safe_zone_ok(canvas_w: int, canvas_h: int, bbox: list[int]) -> dict`
  `bbox = [x, y, w, h]`. Element occupies `x..x+w` horizontally, `y..y+h` vertically.
  Returns `{"passes": bool, "reason": str}`.
  `passes = True` iff `x >= x_min and y >= y_min and x+w <= x_max and y+h <= y_max`.
  On failure `reason` names which edge violated (e.g. `"bottom edge 1330 > y_max 1310"`).
  Unknown canvas size → `ValueError("no safe zone for canvas <w>x<h>")`.
  Negative w/h or non-4-length bbox → `ValueError`.
  Note: the caller decides which roles are subject to V6 (headline/body/hook are; source-stamp/
  wordmark are exempt per spec V6) — this function only does the geometry.

### 4.6 Blacklist parser + scan (V9, single-source)

- `parse_blacklist(brand_kit_path: str) -> list[str]`
  Opens `brand/brand-kit.md`, locates the `## 8. Blacklist` section, and extracts every
  double-quoted phrase in that section. Returns the phrases **verbatim** (original casing,
  original characters incl. the en-dash in "Fri 3–4pm"). Must return exactly these five for
  the current file (order as written):
  1. `90% of recall in first 6 seconds`
  2. `TikTok-native ads drive 3.3x actions`
  3. `hooked ads 2x engagement / +43% purchase intent`
  4. `best slots are Wed 4pm / Fri 3–4pm`
  5. `professionals scroll LinkedIn on the evening commute`
  Raises `ValueError` if the `## 8` section is not found (so a moved/renamed section fails loud
  rather than silently returning `[]`). It does **not** hardcode the phrases — a test proves
  this by parsing the real file.

- `normalize_for_scan(text: str) -> str`
  Lowercases, replaces unicode dashes (`–`, `—`) with `-`, and collapses runs of whitespace
  to a single space. Deterministic.

- `scan_blacklist(text: str, phrases: list[str]) -> list[str]`
  Returns the sublist of `phrases` whose `normalize_for_scan(phrase)` appears as a substring of
  `normalize_for_scan(text)`. Empty list = clean. Case/dash/whitespace-insensitive.

## 5. Commands the Evaluator runs

From repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`:

```bash
# (1) Unit tests — must pass, exit 0
python3 -m unittest discover -s tools/marketing-render/tests -v

# (2) No network / no third-party import: static check that measure.py imports only stdlib
python3 - <<'PY'
import ast, sys
src = open("tools/marketing-render/measure.py").read()
tree = ast.parse(src)
mods = set()
for n in ast.walk(tree):
    if isinstance(n, ast.Import):
        mods |= {a.name.split('.')[0] for a in n.names}
    elif isinstance(n, ast.ImportFrom) and n.module:
        mods.add(n.module.split('.')[0])
allowed = {"re","math","os","sys","json","pathlib","typing","dataclasses","string"}
extra = mods - allowed
print("imports:", sorted(mods))
sys.exit(1 if extra else 0)
PY

# (3) Determinism: run the test suite twice, outputs identical (no randomness/timestamps)
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | tail -1
```

## 6. Evaluator attack script (adversarial, independent of my tests)

The Evaluator should paste this and confirm every assertion holds (all `assert`s pass, prints OK):

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "tools/marketing-render")
import measure as m

# --- contrast: WCAG formula, not brand-kit approximations ---
r = m.contrast_ratio("#1c1917", "#faf8f3")
assert 16.0 <= r <= 17.0, r                      # ~16.5:1 (NOT 13:1)
assert m.contrast_ratio("#1c1917","#faf8f3") == m.contrast_ratio("#faf8f3","#1c1917")  # symmetric
assert abs(m.contrast_ratio("#111111","#111111") - 1.0) < 1e-9   # identical -> 1:1

# accent passes normal; chart-up is the large/normal boundary
assert m.contrast_check("#0f766e","#faf8f3", 24, 400)["passes"] is True     # ~5.15 >= 4.5
cu = m.contrast_check("#0d9488","#faf8f3", 20, 400)                          # ~3.5, small
assert cu["passes"] is False and cu["threshold"] == 4.5                       # fails as normal
cu_large = m.contrast_check("#0d9488","#faf8f3", 30, 400)                     # same colors, large
assert cu_large["passes"] is True and cu_large["threshold"] == 3.0            # passes as large

# --- is_large_text boundary ---
assert m.is_large_text(24, 400) is True
assert m.is_large_text(23.9, 400) is False
assert m.is_large_text(18.5, 700) is True
assert m.is_large_text(18.5, 400) is False

# --- token validation ---
assert m.is_brand_token("#FAF8F3") is True and m.is_brand_token("#123456") is False
assert m.token_name("#0f766e") == "accent"

# --- type-size minimums (V5) ---
assert m.type_min_ok("carousel-slide","headline", 48)["passes"] is True
assert m.type_min_ok("carousel-slide","headline", 47)["passes"] is False
assert m.type_min_ok("chart-card","headline", 36)["passes"] is True
assert m.type_min_ok("chart-card","headline", 35)["passes"] is False
assert m.type_min_ok("carousel-slide","body", 24)["passes"] is True
assert m.type_min_ok("carousel-slide","source-stamp", 12)["passes"] is True   # exempt

# --- glyph-size consistency (Risk 4): truthful passes, 2x lie fails ---
assert m.size_consistent(48, 45) is True
assert m.size_consistent(48, 24) is False

# --- safe zones (V6) ---
assert m.safe_zone_ok(1080,1350,[40,40,1000,1270])["passes"] is True          # exactly fits
assert m.safe_zone_ok(1080,1350,[40,40,1000,1271])["passes"] is False         # 1px over bottom
assert m.safe_zone_ok(1080,1350,[39,40,10,10])["passes"] is False             # left of x_min
assert m.safe_zone_ok(1080,1920,[100,250,800,1230])["passes"] is True         # vertical fits
assert m.safe_zone_ok(1080,1920,[100,249,800,10])["passes"] is False          # above y_min 250
assert m.safe_zone_ok(1080,1920,[100,300,800,1181])["passes"] is False        # below y_max 1480

# --- blacklist parser: single-source, exactly 5 phrases ---
ph = m.parse_blacklist("brand/brand-kit.md")
assert len(ph) == 5, ph
assert any("90% of recall" in p for p in ph)
hits = m.scan_blacklist("Our data shows 90% of recall in first 6 seconds, allegedly.", ph)
assert hits and "90% of recall in first 6 seconds" in hits
assert m.scan_blacklist("Clean copy: RERA Karnataka orders as of 2026-06-30.", ph) == []
# dash/case-insensitive: 'Fri 3-4pm' (ascii dash, lowercased) still matches the en-dash phrase
assert m.scan_blacklist("the BEST slots are wed 4pm / fri 3-4pm they said", ph)

# --- error handling ---
for bad in ("#12", " zzz", "#1234567", "12g4f6"):
    try:
        m.normalize_hex(bad); assert False, bad
    except ValueError:
        pass

print("OK — all measurement-core assertions passed")
PY
```

## 7. States that must exist (mapped to spec §6)

- **Invalid input:** malformed hex, unknown role, unknown canvas, non-4-length/negative bbox,
  missing `## 8` section → `ValueError` naming the offending value (not a bare crash / not silent).
- **Success:** valid inputs return the documented dicts/values.
- **Determinism:** no `random`, no time, no set-ordering leaks into outputs; tests pass identically
  on repeat (§5 command 3).
- **Blacklist clean vs hit:** clean copy → `[]`; violating copy → non-empty naming the phrase.

## 8. Non-goals (this sprint)

- No PNG rendering, no Pillow, no fonts (Sprints 002–003).
- No manifest read/write, no `qa-verdict.json`, no `meta.md` append (Sprint 004).
- No PNG pixel/ink sampling (V2/V3), no axis-integrity flags (V10), no provenance block check
  (V11), no CLI entrypoints, no README (Sprints 004–005).
- No edit to `qa-checklist.md` (the Inter/IBM-Plex correction lands in the validator sprint).
- No third-party dependency, no `requirements.txt`, no network access.

## 9. Definition of done

- The four files in §2 exist; no other files created or modified.
- `python3 -m unittest discover -s tools/marketing-render/tests -v` exits 0 with all tests passing.
- The §5 import-purity check exits 0 (stdlib-only).
- The §6 Evaluator attack script prints `OK` with every assertion passing.
- `generator_trace.log` records commands run and their output.
