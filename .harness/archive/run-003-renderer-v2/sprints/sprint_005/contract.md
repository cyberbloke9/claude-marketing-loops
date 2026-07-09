# Sprint 005 Contract — QA Gate V2 checks (V13–V19) + adversarial fixtures

Run 003 · Renderer V2 Format Library + QA Gate V2
Spec refs: §5.2 (V13–V19), §5.3 (manifest v2 seam), §5.4 (meta blocks), §6 (states), §9 (tokens/no-network), §10 Risks 1/2/3/4/5/6, §11 Sprint-005 row.
Builds on: Sprint 001 (pure `measure.py` V13–V19 functions + widened schema — all present), Sprints 002/003 (format-slide renderer), Sprint 004 (PDF + R14 fail-loud already implemented).

---

## 0. One-paragraph scope

This sprint **wires the QA Gate V2 checks V13–V19 into `validate.py`**, scoped by **surface role** to `format-slide` surfaces, calling the pure `measure.py` functions Sprint 001 already shipped (`dominant_ratio_ok`, `format_slide_type_min`, `thumbnail_ink_ok`, `parse_cover_pattern_block`, `cover_pattern_valid`, `one_dataset_present`). It **removes the Sprint-002 exit-2 guard** (`validate.py:728–733`, "format-slide surfaces require QA Gate V2 … not yet wired") and replaces it with real check execution. It emits the new checks into `qa-verdict.json` (§5.4) and the `meta.md` verdict block, on the same schema. It ships a **v2 adversarial fixture suite** — one positive control plus one fixture per new failure mode, each caught on the **RIGHT check id with the RIGHT rule cite** (one-fixture-one-check discipline) — and **extends `acceptance.py`'s expectation table** with those rows. It does **NOT** re-render TGRERA, does **NOT** touch the 12 v1 fixtures, and does **NOT** regress any V1 behavior: the 12 fixtures + hyd (`carousel-slide`) + TGRERA (`chart-card`, still v1 this sprint) reach their existing verdicts unchanged, because V13–V19 **only run when the asset carries ≥1 `format-slide` surface**.

**Playwright is not applicable** — this project has no browser UI. This is a CLI/raster sprint. The Evaluator attacks it with `python3 -m unittest`, the `acceptance.py` runner, and a shell-driven adversarial fixture matrix (§6), not click paths. Every claim below is reproducible by rendering/validating real PNGs and byte/pixel-inspecting the emitted JSON.

---

## 1. Exact behaviors — the V13–V19 checks (validator, `format-slide`-scoped)

### 1.0 Routing invariant (the spine of this sprint)

- The new checks are routed by **surface role**, not by `schema_version`. A surface with `role == "format-slide"` is a v2 content surface; `carousel-slide` and `chart-card` are frozen v1 surfaces.
- **Load-bearing crash-avoidance:** `measure.type_min_ok("format-slide", …)` **raises `ValueError`** (its `_SURFACE_ROLES` = `{carousel-slide, chart-card}` only, verified `measure.py:129,150`). Therefore, on a `format-slide` surface, `_check_element` MUST **not** call `type_min_ok`; it routes the size floor through **V14** (`measure.format_slide_type_min`, keyed on element role only) instead. V5-floor is emitted as `skipped` on format-slides (V14 owns the v2 floor). **V5-crosscheck still runs** on format-slides (it uses `size_consistent`, which is surface-role-agnostic and safe).
- **Asset-scope gate:** V16, V17, V18, V19 (asset-level checks) run **only when the manifest contains ≥1 `format-slide` surface**. On a pure-v1 asset they emit **zero records** (not `skipped`, not `PASS`, not `FAIL` — they simply do not run). This is what keeps the 12 v1 fixtures + hyd + TGRERA byte-for-byte unchanged. Verify: a v1 asset's `qa-verdict.json` `checks[]` contains **no** id starting `V13`–`V19`.
- On a **mixed** asset (both `format-slide` and v1 surfaces — e.g. a format carousel plus a reactive chart-card), per-surface checks apply per surface role; asset-level V16–V19 run because ≥1 format-slide is present.

### 1.1 Per-surface checks on `format-slide` surfaces

**V13 — dominant-element ratio.** For each `format-slide` surface, call `measure.dominant_ratio_ok(elements)`.
- Utility slide (`is_utility_slide` True — elements ⊆ `{so-what, source-stamp, wordmark}`) → **exempt**, emit `PASS` (`"utility slide … V13 exempt"`).
- Content slide: exactly one `dominant` with `dominant.font_px / body_reference ≥ 3.0` → `PASS`; zero/≥2 dominants or ratio `< 3` → `FAIL`, detail carries the `measure` reason string.
- **Check id:** `V13-dominant-ratio` · **rule:** `PIPELINE-V2.md §4`.

**V14 — raised type floors + wordmark presence.** Two teeth, two distinct ids:
- **V14-type-floor** (per element): call `measure.format_slide_type_min(element_role, font_px)`. `minimum None` (wordmark) → `skipped`. `passes` → `PASS`. Else `FAIL` naming role/`font_px`/minimum. Floors: `headline`/`hook`/`dominant` ≥48, `body`/`chart-label`/`so-what` ≥26, `source-stamp` ≥24, `wordmark` exempt.
- **V14-wordmark** (per surface): the surface must carry **exactly one** element with `role == "wordmark"`. Zero → `FAIL` ("no wordmark on format-slide"); ≥2 → `FAIL` ("N wordmarks; exactly one required"); one → `PASS`.
- **Check ids:** `V14-type-floor`, `V14-wordmark` · **rule (both):** `qa-checklist.md §Typography`.

**V15 — thumbnail gate (360px, measured).** For each **content** format-slide (utility slides exempt — skip, no record or `skipped`), measure the rendered ink legibility of the slide's `headline`/`hook` (if present) and its `dominant` element after a real downscale:
- **Downscale mechanics (pinned, deterministic — BUILD and Evaluator MUST agree bit-for-bit):** downscale the **whole** PNG `1080×1350 → 360×450` with `Image.LANCZOS` (whole-image resize, then crop the ×(1/3)-scaled bbox — NOT crop-then-downscale, which antialiases edges differently). Scale each element bbox `[x,y,w,h]` by `360/1080 = 1/3` (round each component). Measure the ink-band height in the scaled crop using the **existing `_crop_rows_ink` + `_median_band_height`** machinery against the element's declared color (INK_TOL/BAND_GAP reused verbatim). The measured band height **in the 360px image is the `effective_px`** (do NOT re-apply `thumbnail_scale_band` — that pure predictor is unit-test-only; V15 measures the downscaled image directly).
- Call `measure.thumbnail_ink_ok(role, effective_px)`: `headline`/`hook` floor **13**, `dominant` floor **21**. `effective_px ≥ floor` → `PASS`; below → `FAIL`. A content slide whose `headline`/`dominant` yields **no measurable band** (band `None`) → `effective_px = 0` → `FAIL` (illegible).
- The transient 360px preview is **never written to disk** — it does not touch PNG/PDF byte-determinism.
- **Check id:** `V15-thumbnail` · **rule:** `PIPELINE-V2.md §4`.
- **Threshold provenance + empirical de-risk (see §9 Risk A):** the 13/21 floors are Sprint-001-pinned from the `K_INTER≈0.83` calibration. BUILD MUST **empirically confirm** (probe recorded in `generator_trace.log`) that the v2 positive control clears 13/21 with margin AND the illegible fixture fails — not trust arithmetic. Sprint-001's escape hatch (adjust a threshold **down**, never below where the illegible fixture still fails, justified in trace) is the only fallback.

### 1.2 Asset-level checks (run only when ≥1 `format-slide` present)

**V16 — so-what presence.** The asset must carry ≥1 element with `role == "so-what"` across its format-slides. Absent → `FAIL`. · id `V16-so-what` · rule `PIPELINE-V2.md §4`.

**V17 — cover-pattern recorded.** `meta.md` must contain the `<!-- cover-pattern:start -->…<!-- cover-pattern:end -->` block (`measure.parse_cover_pattern_block`) with `pattern ∈ {BIG-NUMBER, CHART-FIRST}` (`measure.cover_pattern_valid`). Missing block or invalid value → `FAIL`. · id `V17-cover-pattern` · rule `PIPELINE-V2.md §4`.

**V18 — slide-count cap.** The count of `format-slide` surfaces must be **≤10**. 11+ → `FAIL` naming the count. · id `V18-slide-count` · rule `PIPELINE-V2.md §4`.

**V19 — one-dataset attestation (presence, not semantic — Risk 5).** The cover-pattern block must carry a non-empty `one_dataset:` line (`measure.one_dataset_present`). Missing/empty → `FAIL`. · id `V19-one-dataset` · rule `PIPELINE-V2.md §4`.

### 1.3 Existing checks on format-slides (applicability, unchanged semantics)

- **V2-canvas:** add `"format-slide": (1080, 1350)` to `_FORMAT_BY_ROLE` so V2 enforces the R10 canvas on format-slides (conscious extension; v1 entries untouched → no regression). PNG≠manifest canvas, or canvas ≠ 1080×1350 → `FAIL`.
- **V3-ink, V4-contrast:** run per element as today (role-agnostic).
- **V5-floor:** `skipped` on format-slides (V14 owns the floor). **V5-crosscheck:** runs (measured-vs-declared ±25%).
- **V6-safezone:** runs for `_SAFEZONE_ROLES = {headline, body, hook}`; `dominant`/`so-what`/`source-stamp`/`wordmark` exempt (skipped), as today. Format-slide safe zone `(1080,1350)` already in `measure.SAFE_ZONES`.
- **V7-hook:** asset-level; format-slides use `headline` not `hook`, so typically `skipped` (N/A) — unchanged.
- **V8-source-stamp:** **stays skipped** on format-slides (existing applicability excludes format-slide; §5.2: "per existing applicability"). Gating a format-slide *source slide* through V8 is **deferred to Sprint 006** (TGRERA). See §8 non-goals — this is a deliberate scope boundary, not a gap; Risk-6's "source slide satisfies V8" is a Sprint-006 obligation.
- **V9-blacklist:** asset-level, runs on all surfaces (v2 copy must be blacklist-clean).
- **V10-chart-integrity:** `skipped` unless `chart-card` — unchanged (a format `CHART` slide with `has_axis` is out of Sprint-005 fixture scope; V10 stays chart-card-only this sprint).
- **V11-provenance:** asset-level; every v2 asset's `meta.md` still needs the `<!-- provenance:start -->` block (Risk B below).
- **V12 (verdict writer):** unchanged; V13–V19 records flow through `build_verdict`/`failed_checks`/`_verdict_block` on the existing schema (`qa-verdict.json` `schema_version` stays `"1"` — it is the verdict-doc schema, distinct from the manifest schema).

### 1.4 Generation order (deterministic)

Per surface (manifest order): V2 → per element (V3/V4/V5-floor|skip/V5-crosscheck/V6) → then per format-slide surface V13 → V14-wordmark → V15; then surface-level V8/V10. Then asset-wide V7, V9, V11, and (if ≥1 format-slide) V16, V17, V18, V19. Same input → identical `checks[]` order and content.

---

## 2. Files affected

- `tools/marketing-render/validate.py` — **remove** the exit-2 format-slide guard (`run()`); **add** `_check_v13`…`_check_v19` and route them in `run_checks`/`_check_element` by surface role; add `format-slide` to `_FORMAT_BY_ROLE`; import already-present `measure` functions. No v1 check logic edited; no `measure.py` edit.
- `tools/marketing-render/acceptance.py` — **extend** `EXPECTATIONS` with the v2 fixture rows (§6.2). No v1 row edited or removed. `run_tgrera` unchanged (TGRERA is still v1 chart-card this sprint).
- `tools/marketing-render/fixtures/make_v2_fixtures.py` — **new** deterministic generator for the v2 fixtures (mirrors `make_fixtures.py` discipline: hand-craft manifest + real PNG, inject exactly one defect).
- `tools/marketing-render/fixtures/fx-v2-*/` — **new** fixture dirs (§6.1), generated on disk (mirrors the 12 v1 fixture dirs that live on disk).
- `tools/marketing-render/tests/test_validate.py` — **rewrite** `TestFormatSlideGuard` (the guard is gone) into a class asserting v2 assets now flow through V13–V19 and reach a real verdict; **preserve** `test_guard_does_not_fire_on_v1_asset` (v1 → exit 0) as a regression check. Add V13–V19 wiring tests.
- `tools/marketing-render/tests/test_acceptance.py` — extend for the new expectation rows if it asserts table coverage.

**Out of scope (do not touch):** `render.py` (R14 fail-loud already shipped Sprint 004), `measure.py` (V13–V19 pure functions already shipped Sprint 001 — call them, do not edit), the 12 v1 fixtures, `content/2026-07-03-tgrera-enforcement-wave/` (Sprint 006), any file outside `tools/marketing-render/`.

---

## 3. Data / state transitions

Validator reads `content/<slug>/render/manifest.json` + PNG bytes + `meta.md`; writes `render/qa-verdict.json` + an idempotent `meta.md` verdict block (unchanged seams). No new file I/O beyond the transient in-memory 360px downscale (never persisted). No network, no DB, deterministic outputs for identical inputs. Fixtures are generated once by `make_v2_fixtures.py` and read at validate time.

---

## 4. Empty / loading / success / error / invalid states (§6)

- **No render yet / missing manifest or PNG** → `PreconditionError`, exit 2, "manifest/PNG not found; run render first" (unchanged).
- **Success (PASS)** — v2 positive control: all applicable checks pass → `verdict=PASS`, exit 0, `failed_checks: []`, verdict block written.
- **V2-rule failures (each a distinct FAIL, right id cited):** V13 (ratio<3 / 0 / ≥2 dominants), V14-type-floor (body 24px), V14-wordmark (0 wordmarks), V15 (thumbnail-illegible headline/dominant), V16 (missing so-what), V17 (missing/invalid cover-pattern), V18 (11 format-slides), V19 (missing one_dataset). Each fixture fires **exactly one** target id (nothing else in `failed_checks`).
- **11-slide at render (R14)** — an 11-slide `formats.md` → `render.py` exits 1 ("cap is 10 (R14…)"), no partial write (already implemented Sprint 004; regression-tested this sprint). V18 is the QA-time twin on a hand-crafted 11-surface manifest.
- **Invalid input** — malformed manifest / unknown format tag / non-token color → `PreconditionError` naming the field, exit 2 (unchanged).
- **Frozen v1 path** — the 12 fixtures + hyd + TGRERA reach their existing verdicts; their `qa-verdict.json` gains **no** V13–V19 records.

---

## 5. Keyboard / focus / ARIA / contrast / responsive

Not applicable — no UI, no DOM, no viewport. Stated explicitly so the omission is not read as a gap. (WCAG contrast is enforced mechanically by the pre-existing V4 on every element, including format-slide elements.)

---

## 6. Commands + adversarial fixture matrix (replaces Playwright click paths)

### 6.1 The v2 fixtures (each trips exactly one check; all else valid)

Each fixture is a `content/`-shaped folder with a hand-crafted `manifest.json` + real vendored-Inter PNG(s) + a `meta.md` carrying **valid provenance AND valid cover-pattern blocks** (except where the fixture intentionally breaks one). "Otherwise valid" = passes V2/V3/V4/V6/V9/V11 + all non-target V13–V19.

| Fixture | Target FAIL id | Rule cite | Injected defect (everything else valid) |
|---|---|---|---|
| `fx-v2-good` | *(PASS, exit 0)* | — | Valid ≤10-slide carousel: content slide(s) with one `dominant ≥3×body` + wordmark; ≥1 `so-what`; cover-pattern (valid) + one_dataset + provenance in `meta.md`. **Headline rendered ≥56px, dominant ≥100px** (§9 Risk A margin). |
| `fx-v2-dominant-small` | `V13-dominant-ratio` | `PIPELINE-V2.md §4` | Content slide: `body` 30px, `dominant` 80px → ratio 2.67 < 3. Body ≥26 (V14 ok); dominant 80 honest-rendered clears V15. |
| `fx-v2-body-24` | `V14-type-floor` | `qa-checklist.md §Typography` | `body` at **24px** (< 26 floor). `dominant` 78px → 78/24 = 3.25 ≥ 3 (V13 ok). Honest render. |
| `fx-v2-no-wordmark` | `V14-wordmark` | `qa-checklist.md §Typography` | Content slide with **zero** `wordmark` element. All else valid. |
| `fx-v2-thumb-illegible` | `V15-thumbnail` | `PIPELINE-V2.md §4` | `headline` **declared 48** (passes V14 floor) but **degrade-rendered** so its 360px band < 13 while full-res band stays in V5-crosscheck's ±25% window `[~30, ~50]`. Degrade **only** the headline; leave `dominant` honest (V15 fires on exactly one element). V13 ok. |
| `fx-v2-no-so-what` | `V16-so-what` | `PIPELINE-V2.md §4` | Valid content slide(s), **no `so-what` anywhere**. cover-pattern + one_dataset + provenance present. |
| `fx-v2-bad-cover` | `V17-cover-pattern` | `PIPELINE-V2.md §4` | cover-pattern block present with `pattern: TIMELINE` (**invalid value**) but `one_dataset:` **present** (isolates V17 from V19 — a *missing* block would fail both). |
| `fx-v2-no-dataset` | `V19-one-dataset` | `PIPELINE-V2.md §4` | cover-pattern block present, `pattern: BIG-NUMBER` (valid → V17 ok), **no `one_dataset:` line**. |
| `fx-v2-11-slides` | `V18-slide-count` | `PIPELINE-V2.md §4` | Manifest with **11** `format-slide` surfaces (11 identical valid slides; one carries a `so-what` so V16 is satisfied). cover-pattern + one_dataset + provenance present. |

BUILD may reuse one rendered valid PNG across the 11 surfaces of `fx-v2-11-slides` (identical bytes, distinct `id`/`png` names) to keep generation cheap; each must still pass V2/V3/V4/V13/V14/V15.

### 6.2 `acceptance.py` expectation-table rows (added; v1 rows unchanged)

The 12 v1 rows stay byte-identical. Add exactly these 9 rows (exact-id equality, rule-substring match — the runner already enforces the NAMED check, not "some FAIL"):

```
fx-v2-good            exit 0  (positive control, clean PASS)
fx-v2-dominant-small  exit 1  V13-dominant-ratio   PIPELINE-V2.md §4
fx-v2-body-24         exit 1  V14-type-floor        qa-checklist.md §Typography
fx-v2-no-wordmark     exit 1  V14-wordmark          qa-checklist.md §Typography
fx-v2-thumb-illegible exit 1  V15-thumbnail         PIPELINE-V2.md §4
fx-v2-no-so-what      exit 1  V16-so-what           PIPELINE-V2.md §4
fx-v2-bad-cover       exit 1  V17-cover-pattern     PIPELINE-V2.md §4
fx-v2-no-dataset      exit 1  V19-one-dataset       PIPELINE-V2.md §4
fx-v2-11-slides       exit 1  V18-slide-count       PIPELINE-V2.md §4
```

`table_coverage_error` requires the table to cover **exactly** the committed `fx-*` dirs — so every new `fx-v2-*` dir MUST have a table row and vice versa.

### 6.3 Commands the Evaluator runs (repo root)

```bash
# (a) Full render suite — MUST stay green; count rises (new tests), never falls
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"

# (b) Full loop suite — MUST stay 254 … OK (does not import validate/measure)
python3 -m unittest discover -s tools/marketing-loops/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"

# (c) Acceptance — 12 v1 fixtures unchanged + TGRERA PASS + 9 v2 rows met
python3 tools/marketing-render/acceptance.py            # exit 0
python3 tools/marketing-render/acceptance.py --verbose  # per-check lines

# (d) Regenerate v2 fixtures deterministically, then diff (no drift)
python3 tools/marketing-render/fixtures/make_v2_fixtures.py

# (e) Adversarial: each v2 fixture fires its ONE named check, nothing else
for fx in dominant-small body-24 no-wordmark thumb-illegible no-so-what bad-cover no-dataset no-dataset 11-slides; do
  python3 tools/marketing-render/validate.py tools/marketing-render/fixtures/fx-v2-$fx --checked-on 2026-07-04
  python3 -c "import json;d=json.load(open('tools/marketing-render/fixtures/fx-v2-$fx/render/qa-verdict.json'));print(fx,[f['id'] for f in d['failed_checks']])"
done
python3 tools/marketing-render/validate.py tools/marketing-render/fixtures/fx-v2-good  # exit 0, PASS

# (f) No-regression: a v1 asset's verdict carries NO V13–V19 records
python3 -c "import json;d=json.load(open('tools/marketing-render/fixtures/fx-good-min/render/qa-verdict.json'));print([c['id'] for c in d['checks'] if c['id'][:3] in ('V13','V14','V15','V16','V17','V18','V19')])"  # -> []

# (g) R14 render fail-loud twin (11-slide formats.md → exit 1, no partial write)
python3 tools/marketing-render/render.py <11-slide formats.md folder>  # exit 1, "cap is 10 (R14…)"
```

### 6.4 Adversarial matrix (each row a distinct, isolable attack)

| # | Attack | Expected |
|---|---|---|
| 1 | `fx-v2-good` validate | exit 0, verdict PASS, `failed_checks: []` |
| 2 | `fx-v2-dominant-small` | exit 1; `failed_checks` == `[V13-dominant-ratio]` only |
| 3 | `fx-v2-body-24` | exit 1; `[V14-type-floor]` only |
| 4 | `fx-v2-no-wordmark` | exit 1; `[V14-wordmark]` only |
| 5 | `fx-v2-thumb-illegible` | exit 1; `[V15-thumbnail]` only (NOT also V5-crosscheck) |
| 6 | `fx-v2-no-so-what` | exit 1; `[V16-so-what]` only |
| 7 | `fx-v2-bad-cover` | exit 1; `[V17-cover-pattern]` only (NOT also V19) |
| 8 | `fx-v2-no-dataset` | exit 1; `[V19-one-dataset]` only (NOT also V17) |
| 9 | `fx-v2-11-slides` | exit 1; `[V18-slide-count]` only |
| 10 | 11-slide `formats.md` → `render.py` | exit 1, no `render/` dir written (R14) |
| 11 | v1 `fx-good-min` re-validate | exit 0; `checks[]` has zero V13–V19 ids |
| 12 | all 12 v1 fixtures via acceptance | each reaches its existing verdict, unchanged |
| 13 | TGRERA (chart-card) via acceptance | determinism + validate exit 0, unchanged |
| 14 | mixed asset (format-slide + chart-card) | V13–V19 run (format-slide present); v1 surface still gated by v1 checks |
| 15 | `fx-v2-good` re-generate then re-validate | byte-identical PNG + same verdict (determinism) |

---

## 7. Determinism / security / no-network

- **Determinism:** `make_v2_fixtures.py` re-run → byte-identical PNGs + manifests (decoded-RGBA SHA / byte-equality). V15's LANCZOS downscale is deterministic; the pinned whole-image-resize-then-crop order is fixed so BUILD and Evaluator measure identical bands. Same asset → identical `qa-verdict.json` `checks[]`.
- **No network** at import or call time (Evaluator may run with network disabled). No new third-party dependency — stdlib + already-vendored Pillow + local `measure` only.
- **Secrets/git hygiene:** no secrets introduced; `.gitignore` already covers `.env`/DB. Fixtures are deterministic render artifacts (no secrets). Provenance-safety: v2 fixtures use public-style/illustrative copy only, **no TERREM DB numbers** (the provenance-checked TGRERA asset is Sprint 006).

---

## 8. Explicit non-goals (Sprint 005)

- **No TGRERA re-render** — the reference carousel + PDF + acceptance re-point is Sprint 006 (§10 Risk 2). `acceptance.py`'s `run_tgrera` stays on the v1 chart-card baseline this sprint.
- **No V8 extension to format-slides** — V8 stays skipped on format-slide surfaces (existing applicability); gating a format-slide *source slide* is Sprint 006. Deliberate scope boundary.
- **No V10 extension** — V10 stays chart-card-only; a format `CHART` slide with `has_axis` is not exercised this sprint.
- **No `measure.py` edit** — the V13–V19 pure functions already exist (Sprint 001); this sprint only *calls* them. No mutation of `_TYPE_MINIMUMS`, `type_min_ok`, `_V2_TYPE_MINIMUMS`, or any pinned threshold (except the Risk-A escape hatch, if forced, justified in trace).
- **No `render.py` edit** — R14 fail-loud + R10–R19 rendering already shipped Sprints 002–004.
- **No semantic "one dataset" / "is the so-what useful" judgment** — V19/V16 are presence-only (Risk 5).
- **No PDF-fidelity work** — Sprint-004 F-001 (DCTDecode lossy pages) is a Sprint-006 decision, out of scope here.
- **No new brand colors/fonts, no scope widening, no stub/placeholder/dead check.**

---

## 9. Risks and mitigations

- **Risk A — V15 margin (load-bearing).** The 13/21 floors are thin at the 48/78 declared minima. Empirical probe on a real honest render (recorded pre-contract): headline 52px → 360px band **17** (floor 13, +4), dominant 132px → band **32** (floor 21, +11). Bands run *higher* than the pure `0.83·font/3` arithmetic because `_crop_rows_ink` counts any-ink rows on the antialiased downscale. **Mitigation:** the positive control and every non-V15 fixture render **headline ≥56px, dominant ≥100px** so measured bands clear 13/21 with ≥3px margin; the illegible fixture declares headline 48 but degrade-renders to a ~30–35px full band (passes V5-crosscheck ±25%, fails V15). BUILD MUST record the actual measured bands for the positive control AND the illegible fixture in `generator_trace.log` and confirm the invariant "positive clears, illegible fails." Sprint-001's downward-adjust escape hatch is the only fallback, never below where the illegible fixture still fails.
- **Risk B — silent co-firing (breaks one-fixture-one-check).** Every v2 fixture's `meta.md` MUST carry valid provenance (V11) AND valid cover-pattern (V17) + one_dataset (V19) blocks, except the fixture intentionally breaking one. Any adversarial fixture that co-fires V11/V17/V19 with its target is a defect. Mitigation: `make_v2_fixtures.py` writes both blocks by default; the acceptance runner + matrix row 2–9 assert `failed_checks` is a **singleton** of the target id.
- **Risk C — guard removal is a conscious extension, not a weakening.** `TestFormatSlideGuard` asserted v2 → exit 2; that behavior is intentionally superseded (this sprint's entire purpose). Rewrite it to assert the new gated behavior; **preserve** the v1-exit-0 regression assertion. Note `_write_v2_asset` saves a **blank** canvas — with the guard gone it now fails V3-ink, so the rewritten assertion is "reaches a real verdict / fires the expected check," not "PASSes."
- **Risk D — regression budget.** Render suite (263 at Sprint-004 end) must stay `OK` and rise with new tests; loop suite must stay `254 … OK`. Acceptance must stay `PASS` with the 12 v1 rows + TGRERA byte-unchanged. Any frozen assertion touched must be justified in the contract/trace as a conscious extension (only `TestFormatSlideGuard` qualifies).

---

## 10. Definition of done (Evaluator-verifiable on disk)

1. `validate.py` runs V13–V19 on `format-slide` surfaces with the exact ids/rules in §1; the Sprint-002 exit-2 guard is removed; `format-slide` added to `_FORMAT_BY_ROLE`.
2. V13–V19 emit **zero records** on pure-v1 assets; the 12 v1 fixtures + hyd + TGRERA reach their existing verdicts unchanged (acceptance `PASS`, TGRERA byte-identical).
3. Nine `fx-v2-*` fixtures on disk, deterministically regenerable by `make_v2_fixtures.py`; each adversarial fixture's `failed_checks` is a **singleton** of its target id with the cited rule; `fx-v2-good` is a clean PASS (exit 0).
4. `acceptance.py` `EXPECTATIONS` extended with the 9 v2 rows; `python3 acceptance.py` exits 0 (all v1 + TGRERA + v2 rows met).
5. Render suite `Ran N … OK` (N > 263). Loop suite `Ran 254 … OK`.
6. R14 render fail-loud twin re-proven (11-slide `formats.md` → exit 1, no partial write).
7. `generator_trace.log` records: baselines re-confirmed before code; files changed; V15 measured-band probe for the positive control AND illegible fixture (Risk A); the conscious `TestFormatSlideGuard` rewrite (Risk C); the one-fixture-one-check singleton evidence; disclosed risks.

This contract is testable end-to-end via §6.3 commands + the §6.4 matrix. If any matrix row cannot be executed against the shipped code, or any adversarial fixture fires more than its one target id, the contract is not met.
