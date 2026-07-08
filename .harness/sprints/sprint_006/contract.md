# Sprint 006 Contract — TGRERA v2 carousel + PDF + full end-to-end, no regression

Run 003 · Renderer V2 Format Library + QA Gate V2 — **final integration sprint**
Spec refs: §4 Story 4 (ship reference asset), §5.1 R10–R19, §5.2 V13–V19, §5.3 (manifest v2 seam), §5.4 (meta blocks), §5.5 §5 PIPELINE-V2 (TGRERA redesign), §6 (states), §9 (tokens/no-network/regression budget), §10 Risk 1/2/6, §11 Sprint-006 row.
Builds on: Sprints 001–004 (format-slide renderer + PDF + measure/schema), Sprint 005 (QA Gate V2 V13–V19 wired + 9 adversarial fixtures, all singletons, acceptance 23/23).

---

## 0. One-paragraph scope

This sprint **authors the TGRERA reference carousel as schema-v2 format-slides**, renders its PNGs + `carousel.pdf`, and drives it through the **full V2 QA gate to a clean PASS end-to-end**. It **re-points `acceptance.py`'s `run_tgrera`** (Risk 2) from the frozen v1 chart-card baseline (hard-coded `chart-card.png` + its SHA + exit-0) to the new v2 baseline: **carousel PNGs pixel-identical on re-render (R8), `carousel.pdf` byte-identical on re-render (R16), and `validate.py` exit 0 (PASS)**. It is a **Path-A** implementation — the TGRERA carousel is authored entirely as **dominant-bearing content slides** with the required `so-what` and `source-stamp` as **inline elements** (proven to render+validate clean, §7 probe). It **does NOT** add utility (dominant-less) slides, **does NOT** edit `render.py`, `validate.py`, or `measure.py`, and **does NOT** extend V8 to format-slide surfaces — all frozen v1/v2 code paths stay byte-for-byte unchanged (Risk 1). The only code touched is `acceptance.py` (`run_tgrera` re-point + no v1/v2 fixture row changed). TGRERA's `chart-spec.md` is **superseded** by a `formats.md` so `render_asset` emits a pure carousel (not a mixed asset); chart-card reactive-single coverage is preserved via the frozen `fx-good-min` fixture (Risk 2).

**Playwright is not applicable** — no browser UI. This is a CLI/raster sprint. The Evaluator attacks it by rendering real PNGs/PDF, byte/pixel-inspecting them and the emitted `qa-verdict.json`, running both unittest suites and `acceptance.py`, and re-authoring/mutating the TGRERA input to confirm the gate has teeth — not click paths.

### 0.1 Path-A justification (why no render.py / validate.py / V8 change)

- **No HARD spec clause requires a standalone utility slide or V8-on-format-slides.** R13/V16 require the `so-what` and `source-stamp` elements to be **present on the carousel**, not on dedicated slides. §5.2 states V8 "runs per existing applicability" = `chart-card` + `carousel-slide` only; format-slides **skip** V8 (a `skipped` record, not a FAIL). Extending V8 applicability would mutate frozen v1 check behavior — exactly what §10 Risk 1 forbids.
- **Risk 6 is labeled `[ASSUMPTION]` and grants layout latitude verbatim:** "Exact count/layout is the Generator's within these required elements; every slide MUST be either dominant-bearing or utility-exempt — no content slide without a dominant." A dominant-bearing content slide carrying an **inline** `so-what` / `source-stamp` is dominant-bearing and V13-valid. Every TGRERA slide is dominant-bearing; the utility-exempt branch is simply not used.
- **Story-4 elements all present:** RECEIPTS cover, order chips, so-what, source (§1.1). The reference asset passes the full V2 gate end-to-end without touching any frozen code path — the correct final-sprint shape (regression is the dominant risk; zero frozen-code edits spend zero regression budget).
- **F-001 (lossy DCTDecode PDF pages) does NOT block this sprint** (§8). The HARD PDF rule is R16 byte-determinism (met) + R15 page-order/count (met). The contract makes **no** "pixel-identical PDF pages" claim.

---

## 1. Exact behaviors — the TGRERA v2 carousel

### 1.1 Slide plan (Path-A, all dominant-bearing, ≤10 slides)

Author `content/2026-07-03-tgrera-enforcement-wave/formats.md` as a **2-slide** carousel (well under the 10 cap; every fact identical to the v1 script/chart-spec — only the hierarchy changes):

- **F1 — RECEIPTS (cover).** `Headline:` "3 builders. 9 days." (renders headline role, 52px); `Dominant:` the lead consequence ("SALES FROZEN") at 132px (≥3× body); three order `Chip:`s each led by its amount/consequence with builder + date at body size (₹14.95L refund +10.7% · R Homes · Jun 22 / PENALTY · Maharshi's Estates · Jun 27 / 45 DAYS TO PAY · Jayatri Infra · Jun 30); `Wordmark`. Satisfies R11 (one dominant), R13 (wordmark), the RECEIPTS grammar (2–4 chips).
- **F2 — CHECKLIST (utility + evidence).** `Dominant:` big index numeral "3" at 132px; ≥2 numbered `Step:`s ("Find the project's RERA number" / "Match the promoter name on the TGRERA order" / "Confirm the registration status before you pay"); **inline** `So-what:` "Check the RERA number before you pay — free → intel.terrem.in" (satisfies R13/V16); **inline** `Source:` "NewsMeter · Siasat · Deccan Chronicle · orders 2026-06-22/27/30" (satisfies R13 source-stamp presence, carries source-cue + date tokens); `Wordmark`. One dominant (the index numeral), V13-valid.

Both slides carry exactly one `dominant` and exactly one `wordmark` (renderer `_validate_format_roles` enforced). Copy uses **only public news-reported regulator orders** already in TGRERA's `meta.md`/`script.md` — **no TERREM DB numbers** (§9 provenance-safety).

> The Generator may adjust exact chip/step count and copy within these required elements, provided: every slide is dominant-bearing and V13-valid; ≥1 `so-what` and ≥1 `source-stamp` are present across the carousel; ≤10 slides; wordmark on every slide; every fact traceable to the cited public orders.

### 1.2 `meta.md` structured blocks

`content/2026-07-03-tgrera-enforcement-wave/meta.md` must carry, alongside the **existing** `<!-- provenance:start -->…<!-- provenance:end -->` block (kept intact — V11):

```md
<!-- cover-pattern:start -->
pattern: BIG-NUMBER
one_dataset: TGRERA enforcement orders, Jun 2026 (NewsMeter / Siasat / Deccan Chronicle, dated 2026-06-22/27/30)
<!-- cover-pattern:end -->
```

`pattern: BIG-NUMBER` because the RECEIPTS cover leads with the dominant consequence figure (V17 valid ∈ {BIG-NUMBER, CHART-FIRST}). `one_dataset:` non-empty (V19). The `<!-- qa-verdict:start -->` block is (re)written idempotently by the validator on PASS (V12).

### 1.3 Superseding `chart-spec.md`

`render_asset` emits a `chart-card` surface iff a `chart-spec.md` (with a `Surface: chart-card` marker) is present, and format-slides iff a `formats.md` is present. To ship a **pure** carousel (not a mixed asset that also emits a 1080×1920 chart-card), TGRERA's `chart-spec.md` must be **superseded** so the rendered asset is format-slides only. The Generator MUST verify (BUILD) that `render_asset` on the TGRERA folder produces **only** `format-01.png … format-NN.png` + `carousel.pdf` + `manifest.json` (schema_version "2"), and **no** `chart-card.png`. Reactive-single (chart-card) coverage is preserved via the frozen `fx-good-min` fixture (Risk 2) — it is not lost.

### 1.4 Full-gate PASS (end-to-end)

`validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on <date>` → **exit 0, verdict PASS, `failed_checks: []`**. Applicable checks and expected dispositions:

- **V2-canvas** PASS (1080×1350 per format-slide).
- **V3-ink / V4-contrast** PASS on every element (tokens only, contrast ≥4.5:1 / ≥3:1 large).
- **V5-floor** `skipped` on format-slides (V14 owns the v2 floor); **V5-crosscheck** PASS (measured ≈ declared ±25%).
- **V6-safezone** PASS for `{headline, body, hook}`; `dominant`/`so-what`/`source-stamp`/`wordmark` exempt.
- **V7-hook** `skipped` (format-slides use `headline`, not `hook`).
- **V8-source-stamp** `skipped` on format-slides (existing applicability — NOT a FAIL; the inline source-stamp is still gated by V3/V4/V14).
- **V9-blacklist** PASS (copy blacklist-clean).
- **V10-chart-integrity** `skipped` (no `chart-card`, no `has_axis`).
- **V11-provenance** PASS (provenance block intact).
- **V13-dominant-ratio** PASS on both content slides (132/30 = 4.4 ≥ 3, or 132/26 fallback ≥ 3).
- **V14-type-floor** PASS (headline 52 ≥48, dominant 132 ≥48, body 30 ≥26, so-what 30 ≥26, source-stamp 26 ≥24, wordmark exempt); **V14-wordmark** PASS (exactly one per slide).
- **V15-thumbnail** PASS (§9 Risk A — measured 360px bands clear 13/21; the actual bands MUST be recorded in the trace).
- **V16-so-what** PASS (inline so-what present).
- **V17-cover-pattern** PASS (`pattern: BIG-NUMBER`).
- **V18-slide-count** PASS (2 ≤ 10).
- **V19-one-dataset** PASS (`one_dataset:` present).

### 1.5 Determinism (R8 / R16 / R18)

Re-rendering the TGRERA folder twice → **decoded-RGBA SHA-256 pixel-identical** PNGs AND **byte-identical** `carousel.pdf`. Fonts loaded only from vendored `fonts/`; zero network at render time. (These are inherited renderer guarantees — this sprint proves them on the shipped TGRERA asset.)

---

## 2. Files affected

- `content/2026-07-03-tgrera-enforcement-wave/formats.md` — **new** (the v2 carousel input, §1.1).
- `content/2026-07-03-tgrera-enforcement-wave/meta.md` — **edit**: add the `<!-- cover-pattern:start -->` block (§1.2); **keep** the provenance block intact. The `Format:`/`QA:` narrative lines may be updated to reflect the carousel; provenance facts unchanged.
- `content/2026-07-03-tgrera-enforcement-wave/chart-spec.md` — **superseded** (§1.3) so the asset renders as a pure carousel. It may be renamed (e.g. `chart-spec.md.v1` / moved to an archive note) or emptied of its `Surface: chart-card` marker — the Generator's choice, provided `render_asset` emits **no** chart-card. Preferred: rename to a non-active name so the historical spec is retained but inert.
- `content/2026-07-03-tgrera-enforcement-wave/render/` — regenerated: `format-01.png … format-NN.png`, `carousel.pdf`, `manifest.json` (schema "2"), `qa-verdict.json` (PASS). The old `chart-card.png` + its v1 manifest/verdict are replaced by the carousel outputs.
- `tools/marketing-render/acceptance.py` — **edit `run_tgrera`** (Risk 2): new baseline (carousel PNGs pixel-identical + `carousel.pdf` byte-identical + validate exit 0). No v1 fixture row, no v2 fixture row, and no other function touched. Update the `tgrera_expectations` count/labels honestly to match the new PASS-line set.
- `tools/marketing-render/tests/` — **optional additive**: a regression test asserting the TGRERA asset renders as schema-v2 format-slides + validates PASS (additive only; no existing assertion weakened). If added, it must not depend on network and must be deterministic.

**Out of scope (do NOT touch):** `render.py`, `validate.py`, `measure.py`, the 12 v1 fixtures, the 9 `fx-v2-*` fixtures, `make_fixtures.py`, `make_v2_fixtures.py`, the hyd carousel, any file outside this repo, any V8/V10/V13–V19 check logic.

---

## 3. Data / state transitions

Renderer reads `content/2026-07-03-tgrera-enforcement-wave/formats.md`, writes `render/format-*.png` + `carousel.pdf` + `manifest.json` atomically (partial-write-free). Validator reads that manifest + PNG bytes + `meta.md`, writes `render/qa-verdict.json` + an idempotent `meta.md` verdict block. No network, no DB, deterministic outputs for identical input. `acceptance.py` `run_tgrera` renders once to establish a baseline hash-set (PNG decoded-RGBA SHA + PDF bytes), re-renders, compares, then validates.

---

## 4. Empty / loading / success / error / invalid states (§6)

- **Missing `formats.md`** → renderer errors (existing "no format-slides found" / missing-input path), writes nothing partial, exit ≠ 0.
- **No render yet** (validator before renderer) → `PreconditionError` exit 2, "manifest/PNG not found; run render first".
- **Success (PASS)** — the full V2 gate passes (§1.4): exit 0, `failed_checks: []`, verdict block written, PNGs + `carousel.pdf` + `manifest.json` present, `manifest.schema_version == "2"`, top-level `pdf` key present.
- **Invalid TGRERA input** (e.g. an 11th slide, a chip count out of 2–4, a missing dominant/wordmark) → renderer **fail-loud** (R14 / `_validate_format_roles`), no partial write. This is inherited behavior; the shipped TGRERA input is valid.
- **Determinism** — second render → pixel-identical PNGs AND byte-identical `carousel.pdf`.
- **Frozen paths** — the 12 v1 fixtures + hyd (`carousel-slide`) reach their existing verdicts unchanged; the 9 `fx-v2-*` fixtures still fire their singleton target ids; `fx-good-min` (chart-card) still validates exit 0 with **zero** V13–V19 records.

---

## 5. Keyboard / focus / ARIA / contrast / responsive

Not applicable — no UI, no DOM, no viewport. Stated so the omission is not read as a gap. WCAG contrast is enforced mechanically by the pre-existing V4 on every TGRERA element.

---

## 6. Commands + adversarial matrix (replaces Playwright click paths)

### 6.1 Commands the Evaluator runs (repo root)

```bash
# (a) Render the TGRERA carousel — emits format-*.png + carousel.pdf + manifest (schema "2"), NO chart-card.png
python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave
ls content/2026-07-03-tgrera-enforcement-wave/render/   # format-01.png…, carousel.pdf, manifest.json (no chart-card.png)
python3 -c "import json;d=json.load(open('content/2026-07-03-tgrera-enforcement-wave/render/manifest.json'));print(d['schema_version'], d.get('pdf'), [s['role'] for s in d['surfaces']])"  # 2 carousel.pdf ['format-slide',...]

# (b) Validate the full V2 gate → exit 0, PASS, no failed checks
python3 tools/marketing-render/validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on 2026-07-08
python3 -c "import json;d=json.load(open('content/2026-07-03-tgrera-enforcement-wave/render/qa-verdict.json'));print(d['verdict'],[f['id'] for f in d['failed_checks']])"  # PASS []

# (c) Determinism — re-render, compare PNG decoded-RGBA SHA + PDF bytes
#     (two independent renders → pixel-identical PNGs, byte-identical carousel.pdf)

# (d) Acceptance — 12 v1 fixtures unchanged + 9 v2 singletons + TGRERA on the NEW v2 baseline
python3 tools/marketing-render/acceptance.py            # exit 0, ACCEPTANCE: PASS (N/N)
python3 tools/marketing-render/acceptance.py --verbose  # per-check lines; TGRERA lines show carousel PNG determinism + PDF byte-identity + validate exit 0

# (e) Full render suite — MUST stay green; count rises with any new test, never falls
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"   # >= 266, OK

# (f) Full loop suite — MUST stay 254 … OK (does not import validate/measure)
python3 -m unittest discover -s tools/marketing-loops/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"

# (g) No-regression — a v1 asset's verdict still carries NO V13–V19 records
python3 -c "import json;d=json.load(open('tools/marketing-render/fixtures/fx-good-min/render/qa-verdict.json'));print([c['id'] for c in d['checks'] if c['id'][:3] in ('V13','V14','V15','V16','V17','V18','V19')])"  # []
```

### 6.2 Adversarial matrix (each row a distinct, isolable attack)

| # | Attack | Expected |
|---|---|---|
| 1 | Render TGRERA folder | `format-01.png…` + `carousel.pdf` + `manifest.json` (schema "2", `pdf` key), **no** `chart-card.png` |
| 2 | Validate TGRERA | exit 0, verdict PASS, `failed_checks: []` |
| 3 | Re-render TGRERA, compare PNGs | decoded-RGBA SHA-256 identical (R8) |
| 4 | Re-render TGRERA, compare PDF | `carousel.pdf` byte-identical (R16) |
| 5 | `acceptance.py` | exit 0, `ACCEPTANCE: PASS (N/N)`; TGRERA rows on the new v2 baseline |
| 6 | Mutate TGRERA: drop the inline `So-what:` line, re-render+validate | `failed_checks == [V16-so-what]` only |
| 7 | Mutate TGRERA: shrink a body below 26 (hand-edit manifest), validate | V14-type-floor FAIL (gate has teeth on the real asset) |
| 8 | Mutate `meta.md`: invalid `pattern:` value, validate | `[V17-cover-pattern]` fires |
| 9 | Mutate TGRERA: declare an 11th slide in `formats.md`, render | exit ≠ 0, "cap is 10 (R14…)", **no** `render/` written (no partial write) |
| 10 | Render suite | `Ran N … OK`, N ≥ 266 (never falls) |
| 11 | Loop suite | `Ran 254 … OK` |
| 12 | 12 v1 fixtures via acceptance | each reaches its existing verdict, unchanged |
| 13 | 9 `fx-v2-*` fixtures via acceptance | each still fires its singleton target id |
| 14 | `fx-good-min` (chart-card) re-validate | exit 0; `checks[]` has zero V13–V19 ids (frozen v1 path intact) |
| 15 | TGRERA V15 bands probe | headline + dominant 360px bands ≥ 13/21 (recorded in trace) |

---

## 7. Determinism / security / no-network / probe evidence

- **Determinism:** TGRERA re-render → identical PNGs (decoded-RGBA SHA) + byte-identical `carousel.pdf`. Same asset → identical `qa-verdict.json` `checks[]`.
- **No network** at render or validate time (Evaluator may run with network disabled). No new third-party dependency — stdlib + already-vendored Pillow + local `measure`/`render`/`validate`.
- **Secrets/git hygiene:** no secrets introduced; `.gitignore` covers `.env*`/DB. The rendered PNGs/PDF are deterministic artifacts. Provenance-safety: TGRERA copy is **public news-reported regulator orders only, no TERREM DB numbers** (§9).
- **Pre-contract probe (recorded, reproducible):** the exact Path-A plan (RECEIPTS cover + CHECKLIST with inline `So-what:` + `Source:`) was rendered and validated during contract authoring: `render.py` exit 0 (2 format-slides, no chart-card); `validate.py` → **PASS (98 checks, 0 failed)**, exit 0; V15 measured bands **headline 52px → 360px band 16 (floor 13, +3)**, **dominant 132px → band 32 (floor 21, +11)** — both clear. The headline margin (+3) is **thin** because the renderer fixes the headline style at 52px (Risk A below); it PASSES but BUILD MUST re-record the shipped asset's actual bands and confirm the invariant.

---

## 8. Explicit non-goals (Sprint 006)

- **No render.py / validate.py / measure.py edit.** The renderer + gate already implement R10–R19 and V2–V19; this sprint authors an asset and re-points the acceptance TGRERA path only.
- **No utility (dominant-less) slides, no V8 extension to format-slides.** Path A authors so-what/source inline on dominant-bearing content slides (§0.1). V8 stays `skipped` on format-slides (frozen applicability, Risk 1).
- **No PDF-fidelity rework (F-001).** DCTDecode-lossy PDF pages are **consciously accepted**: the HARD PDF rules (R16 byte-determinism, R15 page order/count) are met; the contract makes no pixel-identical-PDF-page claim. Chasing lossless PDF encoding is out of scope unless trivial and determinism-preserving.
- **No change to the 12 v1 fixtures, the 9 v2 fixtures, hyd, or any check semantics.**
- **No semantic "one dataset / is the so-what useful" judgment** — V16/V19 are presence-only (Risk 5).
- **No new brand colors/fonts, no scope widening, no stub/placeholder/dead copy, no console warnings.**
- **No publisher / posting / URL plumbing** (§8 spec non-goals — deferred to a later run).

---

## 9. Risks and mitigations

- **Risk A — V15 headline margin (load-bearing, thin).** The RECEIPTS cover headline renders at the renderer's fixed 52px → measured 360px band **16** vs floor **13** (+3 only). It PASSES, but the margin is small. **Mitigation:** BUILD MUST (1) empirically record the shipped TGRERA cover headline AND dominant 360px bands in `generator_trace.log` and confirm ≥ 13/21; (2) keep the dominant at 132px (band 32, +11, ample). BUILD MUST NOT lower any V15 threshold to make TGRERA pass (Sprint-005's downward escape hatch is for the fixtures, and never below where the illegible fixture still fails — not a tool for the reference asset). If the shipped headline band ever measures < 13, the asset copy/format must change (author-side) — not the threshold.
- **Risk B — mixed-asset leak (chart-spec.md).** If `chart-spec.md` is left active, `render_asset` emits BOTH a chart-card and format-slides → a mixed asset whose acceptance baseline (chart-card SHA) collides with the re-point. **Mitigation:** supersede `chart-spec.md` (§1.3); BUILD MUST verify the render output contains **no** `chart-card.png` and `manifest.surfaces` are all `format-slide`.
- **Risk C — acceptance re-point is a conscious extension, not a weakening (Risk 2).** `run_tgrera` currently hard-codes `chart-card.png` + its SHA + exit-0. Re-pointing to the carousel baseline (PNG pixel-identity + PDF byte-identity + validate exit 0) is the intended supersession. BUILD MUST update the `tgrera_expectations` count/labels honestly (no phantom PASS lines) and keep every v1/v2 **fixture** row byte-identical. Chart-card render/validate coverage is retained via `fx-good-min` (Risk 2) — reactive-single coverage is not lost.
- **Risk D — regression budget (hard).** Render suite (266 at Sprint-005 end) must stay `OK` and only rise with any additive test; loop suite must stay `254 … OK`; `acceptance.py` must stay `PASS` with the 12 v1 rows + 9 v2 rows unchanged and the TGRERA rows on the new baseline. Any frozen assertion touched must be justified in the trace as a conscious extension (only `run_tgrera` qualifies this sprint).
- **Risk E — provenance drift.** TGRERA copy must remain public-order-only; the provenance block stays intact (V11). BUILD MUST NOT introduce any TERREM DB number into the carousel copy.

---

## 10. Definition of done (Evaluator-verifiable on disk)

1. `content/2026-07-03-tgrera-enforcement-wave/formats.md` exists; rendering the folder emits `format-*.png` + `carousel.pdf` + `manifest.json` (`schema_version "2"`, top-level `pdf` key, all surfaces `format-slide`) and **no** `chart-card.png`.
2. `meta.md` carries the intact provenance block AND a valid `<!-- cover-pattern:start -->` block (`pattern: BIG-NUMBER`, non-empty `one_dataset:`).
3. `validate.py` on TGRERA → exit 0, verdict PASS, `failed_checks: []`, with V13–V19 all applicable-and-passing per §1.4 (V8/V5-floor/V7/V10 `skipped` as specified).
4. TGRERA re-render → PNG decoded-RGBA SHA-256 identical AND `carousel.pdf` byte-identical (R8/R16).
5. `acceptance.py` → exit 0, `ACCEPTANCE: PASS (N/N)`; `run_tgrera` on the new v2 baseline; all 12 v1 + 9 v2 fixture rows unchanged.
6. Render suite `Ran N … OK` (N ≥ 266). Loop suite `Ran 254 … OK`.
7. Frozen v1 path intact: `fx-good-min` validates exit 0 with zero V13–V19 records; the 9 `fx-v2-*` fixtures still fire their singleton target ids; hyd unchanged.
8. `generator_trace.log` records: baselines re-confirmed BEFORE code (render 266 / loop 254 / acceptance PASS); files changed; the shipped TGRERA V15 measured headline+dominant 360px bands with the "≥ 13/21" confirmation (Risk A); the conscious `run_tgrera` re-point (Risk C); confirmation that no chart-card is emitted (Risk B); provenance intact (Risk E); disclosed risks.

This contract is testable end-to-end via §6.1 commands + the §6.2 matrix. If TGRERA does not reach a clean PASS on the full V2 gate, if any frozen fixture/suite regresses, or if the render emits a chart-card, the contract is not met.
