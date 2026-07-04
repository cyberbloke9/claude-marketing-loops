# Sprint 004 Contract — Validator CLI + verdict

Status: PROPOSED
Sprint: 004
Depends on: Sprint 001 (`tools/marketing-render/measure.py`, PASSED), Sprint 002 (carousel renderer, PASSED), Sprint 003 (chart-card renderer + authored TGRERA `chart-spec.md` + TGRERA `render/{chart-card.png, manifest.json}`, PASSED).
Spec refs: §5.2 (V1–V12), §5.3 (manifest schema — consumed), §5.4 (`qa-verdict.json` schema — produced), §6 (states), §7 (tone of tooling output), §9 (tokens/fonts/no-network/verdict-consumption), §11 (Sprint 004), Risk 1 (Inter precedence), Risk 3 (flag-based axis), Risk 4 (glyph-size cross-check ±25%), Risk 5 (provenance presence-based), Risk 6 (source stamp on chart-card + carousel source slide).

## 0. Purpose, boundary & why there is no Playwright path

This sprint builds the **validator CLI** (`tools/marketing-render/validate.py`) that consumes the renderer↔validator seam (manifest.json + PNGs + asset `*.md` specs), runs checks **V2–V12**, and emits the two validator→consumer seams: a machine-readable `render/qa-verdict.json` (§5.4) and a human-readable **verdict block** appended into the asset's `meta.md`. It enforces the **Inter precedence rule** (Risk 1) and corrects the stale `qa-checklist.md` line. The end-to-end demonstration for this sprint is: run the validator against the **already-rendered TGRERA chart card** and get a structured **PASS** verdict with exit 0.

It is a **headless Python/Pillow CLI tool** — same as Sprints 002/003. There is **no browser / no web UI**, therefore **no Playwright click-path exists**. The Evaluator attacks the CLI directly, feeds it crafted-manifest fixtures + tiny PNGs (shipped this sprint, §7), and probes `qa-verdict.json` / `meta.md` with the Python probes in §9/§10. This is intentional and stated so the contract is fully testable.

### In scope (Sprint 004)
- `tools/marketing-render/validate.py` — the validator CLI (§3 interface, §4 checks V2–V12, §5 outputs, §6 states).
- Checks **V2–V12** implemented per §4, each with an explicit **applicability predicate** (a check that does not apply to a surface is recorded `status:"skipped"`, never silently dropped and never a false FAIL).
- `render/qa-verdict.json` written to the §5.4 schema exactly; verdict block written into `meta.md` **idempotently** (§5.3).
- **Inter precedence (Risk 1):** correct `brand/qa-checklist.md` Typography line "Headings IBM Plex Sans 600" → "Headings Inter 600". The validator does **not** check font family (§4.13).
- **TGRERA provenance block** authored/augmented into `content/2026-07-03-tgrera-enforcement-wave/meta.md` so V11 has a structured attestation block to find (grammar §4.11). This is the meta edit S003 explicitly deferred here.
- **Fail-path unit tests** feeding crafted manifest dicts + tiny generated PNGs to each check, proving each of V2–V12 both PASSes on good input and FAILs on the specific violation it guards (§8).
- Crafted-manifest **fixtures + CLI commands** (§7) so the Evaluator can watch each V-check FAIL from the shell — proving the gate is not a pass-everything stub.
- The **TGRERA chart card validates PASS**, exit 0 (§9 acceptance).
- Non-network at validate time (import-purity, §4.14).

### Explicitly NOT in this sprint (declared, not silently omitted) — Sprint 005 territory
- The four **full adversarial content asset folders** under `content/` (11-word-hook carousel, truncated-axis card, low-contrast card, missing-source card) and the blank-PNG stub asset. Sprint 005 builds those as real asset folders and asserts the *end-to-end* CLI FAIL on each. Sprint 004 proves the **same check logic** fails via crafted-manifest fixtures (§7) — but does not author the 005 asset folders.
- **README wiring** (runnable render+validate commands documented) — Sprint 005.
- **`/loop-qa` SKILL.md update** to invoke the validator and consume `qa-verdict.json` — Sprint 005.
- Cross-fixture full end-to-end acceptance (TGRERA PASS + all five fixtures FAIL together) — Sprint 005.
- No renderer changes: `render.py`, `measure.py`, `test_render.py`, `test_chart_card.py` are **not modified** (validator is a new consumer). No new third-party dependency beyond Pillow. No writes outside the asset's `render/` dir and its `meta.md`. No changes to any other repo.

### Scope-honesty note
Sprint 004 proves the **gate mechanically discriminates PASS from FAIL** and that the TGRERA card passes. It does not build the 005 adversarial *assets*; it builds the validator + fail-path fixtures those assets will exercise. Do not score S004 on the 005 end-to-end; score it on whether V2–V12 are implemented, applicability-gated, cite the rule, and correctly pass TGRERA / fail crafted violations.

## 1. Language / runtime decision

- **Python 3** (`/usr/bin/python3`, 3.9.6) + **Pillow** — same runtime as Sprints 002/003. Pillow reads real PNG bytes (dims, pixel sampling) deterministically with zero network.
- **No new third-party dependency beyond Pillow.** No `pip install`, no network. Imports allowed in `validate.py`: Python stdlib (`argparse`, `json`, `sys`, `re`, `pathlib`, `datetime`) + `PIL` + the local `measure` module (used verbatim; not modified).
- Reuses `measure.py`: `TOKENS`/`TOKEN_HEXES`/`normalize_hex`/`is_brand_token`/`token_name` (token rule), `contrast_check` (V4), `type_min_ok` (V5 floor), `size_consistent` (V5 cross-check band), `safe_zone_ok` (V6), `parse_blacklist`/`scan_blacklist` (V9). The validator adds only the **pixel measurement** (V2/V3/V5 ink) + orchestration + verdict I/O that `measure.py` intentionally deferred.

## 2. Files this sprint creates / modifies (and ONLY these)

Creates:
- `tools/marketing-render/validate.py` — the validator CLI.
- `tools/marketing-render/tests/test_validate.py` — stdlib `unittest` fail-path tests (§8). Separate file so S001/002/003 suites stay byte-untouched.
- `tools/marketing-render/fixtures/` — crafted-manifest + tiny-PNG fixtures the Evaluator runs from the shell (§7). Generated by a committed helper script `tools/marketing-render/fixtures/make_fixtures.py` (deterministic, stdlib+PIL) so fixtures are reproducible, not opaque binaries.

Modifies:
- `brand/qa-checklist.md` — the single Typography line "IBM Plex Sans 600" → "Inter 600" (Risk 1). No other line touched.
- `content/2026-07-03-tgrera-enforcement-wave/meta.md` — add the structured **provenance attestation block** (§4.11 grammar) if the existing content does not already satisfy the grammar, and (at validate time) receive the appended **verdict block** (§5.3). The provenance-block authoring is a source edit; the verdict block is written by the tool at runtime.

Writes at validate time (created by the tool, not committed as source):
- `content/<slug>/render/qa-verdict.json`
- appends/replaces the delimited verdict block inside `content/<slug>/meta.md`.

Does **NOT** modify: `measure.py`, `render.py`, `test_render.py`, `test_chart_card.py`, any other `brand/` content, the hyd asset, TGRERA's `chart-spec.md` / `script.md`, or any file outside this repo.

## 3. CLI interface (deterministic, fail-loud)

```
python3 tools/marketing-render/validate.py <asset-folder> [--checked-on YYYY-MM-DD] [--checked-by NAME]
```

- `<asset-folder>` — path to `content/<slug>/` (required positional).
- `--checked-on` — override the verdict date (default: today, `datetime.date.today().isoformat()`). Exists so verdict tests are not date-fragile and so a fixed date makes `qa-verdict.json` reproducible in tests.
- `--checked-by` — default `validator-cli`.
- **Exit codes:** `0` = overall verdict PASS; `1` = overall verdict FAIL (one or more applicable checks FAILed); `2` = usage/precondition error (missing folder, missing manifest/PNG, malformed manifest — the §6 error states). Exit 2 is distinct from a content FAIL (exit 1): a FAIL still wrote a valid verdict; an error did not.
- **stdout:** terse, mechanical, cite-the-rule (§7 spec tone). One line per FAILed check `FAIL <id> <surface> — <detail> (<rule>)`, then a final `VERDICT: PASS|FAIL (<n> checks, <f> failed, <s> skipped)`. No praise, no hedging. On PASS, prints the applicable checks summarily and the verdict line.
- **stderr:** for exit-2 errors only, a single explicit message naming the offending path/field.

## 4. Checks — V2–V12 (each: applicability predicate, method, PASS/FAIL, rule cited)

Every emitted check record carries `{id, surface, element_bbox?, status, detail, rule}`. `status ∈ {PASS, FAIL, skipped}`. `skipped` = check does not apply to this surface (recorded, not counted as FAIL). Overall verdict = FAIL iff **any** applicable check has `status:"FAIL"`. `rule` cites `brand-kit.md §<n>` or `qa-checklist.md §<section>` or `spec §5.2 <Vn>`.

Pixel checks (V2, V3, V5-ink) open the real PNG bytes with Pillow; they are the anti-stub core (a correct manifest over a blank PNG must FAIL).

### 4.2 V2 — Canvas (pixel check). Applies: every surface.
Open `render/<png>` with Pillow, read real `(width, height)`. FAIL if `(width,height) != (manifest.canvas.w, manifest.canvas.h)`, OR if the manifest canvas does not match the format required by the surface `role` (`carousel-slide` → 1080×1350; `chart-card` → 1080×1920). Detail names the mismatch. Rule: `qa-checklist.md §Layout` (canvas).

### 4.3 V3 — Ink-present (pixel check, anti-stub). Applies: every text element.
For each element, crop the PNG to its `bbox`, count pixels whose RGB is within Euclidean tolerance `INK_TOL` of the declared `color` (opaque). FAIL if the count `< INK_MIN_PX`. A blank/near-blank PNG yields 0 ink → FAIL. `INK_TOL` and `INK_MIN_PX` are **calibrated on the real TGRERA render** (every real element clears the bar with margin) and against a **blank fixture** (0 ink → FAIL); their chosen values + the calibration measurement are recorded in the trace. Rule: `spec §5.2 V3`.

### 4.4 V4 — Contrast (math on declared hex pair). Applies: every text element.
`measure.contrast_check(color, bg, font_px, weight)`. FAIL if `passes=false`. Detail: `ratio X:1 <threshold> Y:1`. Computed on **declared hex** (not sampled pixels — spec §5.2 V4 is explicit; V3 already proved the pixels are on the canvas). Rule: `brand-kit.md §3` / `qa-checklist.md §Color & contrast`.

### 4.5 V5 — Type-size floor + glyph cross-check. Applies: every non-exempt text element.
Two parts:
- **Floor:** `measure.type_min_ok(surface.role, element.role, font_px)`. Exempt roles (`source-stamp`, `wordmark`, `chart-label`) auto-pass the floor. FAIL if `passes=false`. Rule: `qa-checklist.md §Typography` (px minimums).
- **Glyph cross-check (Risk 4, the anti-lie seam):** measured **from PNG pixels, not from manifest bbox_h vs manifest font_px** (comparing two manifest-declared numbers catches zero lies). Method: crop PNG to `bbox`; find rows containing ink (V3 tolerance); group contiguous ink rows into **bands** separated by ≥`GAP` blank rows; take the **median band height** = one text line's ink extent; `effective_px = median_band_height / K_INTER`. `K_INTER` is an Inter cap-to-descender constant **calibrated on the real TGRERA render** (~0.8; recorded in trace). Then `measure.size_consistent(font_px, effective_px, 0.25)` (±25%, Risk 4). FAIL if inconsistent. Discrimination bar per Risk 4 is a **2× lie**: a manifest declaring `font_px = 2×` the truly-rendered size FAILs; the real TGRERA elements PASS. Both proven by test (§8). Applies only where an ink band is measurable; the exempt-role floor still auto-passes but the cross-check still runs (a lying wordmark size is still caught). Rule: `spec §5.2 V5` / Risk 4.

### 4.6 V6 — Safe zones (manifest bboxes). Applies: elements with role ∈ {headline, body, hook}.
`measure.safe_zone_ok(canvas.w, canvas.h, bbox)`. `source-stamp`, `wordmark`, `chart-label` are **exempt** (skipped). FAIL if `passes=false`; detail = the reason string. Rule: `qa-checklist.md §Layout` (safe zone).

### 4.7 V7 — Hook word count (spec). Applies: the `hook`-role element (carousel slide-1).
Cross-reference the manifest `hook` element text to `carousel.md` slide 1. Word count `> 10` → FAIL naming the count. **Applicability:** an asset with no `hook` element (e.g. TGRERA — chart-card only, no carousel) records V7 `skipped` (N/A), NOT pass and NOT fail. Rule: `qa-checklist.md §Carousel` (slide-1 hook ≤10 words).

### 4.8 V8 — Source/date stamp presence. Applies: every `chart-card` surface and every carousel **source slide**.
At least one `source-stamp` element must exist on the surface, and its text must contain **both** a source attribution and an as-of/order **date**. Detection (presence-based, deterministic): text contains a source cue (`Source` / `·`-joined attributions) **and** a date token matching `\b\d{4}-\d{2}-\d{2}\b` or a month-day like `Jun 22`. Missing element or missing either part → FAIL. Rule: `qa-checklist.md §Chart integrity` (source + as-of date). For TGRERA the source-stamp = `"Source: NewsMeter · Siasat · Deccan Chronicle · TGRERA orders as of 2026-06-22 / 27 / 30"` → PASS.

### 4.9 V9 — Blacklisted stats (single-source). Applies: whole asset.
`measure.parse_blacklist(brand/brand-kit.md)` (§8, not hardcoded) → phrases; `measure.scan_blacklist(text, phrases)` over concatenated copy from `carousel.md`, `script.md`, `chart-spec.md` (those that exist) **and** all manifest element `text`. Any hit → FAIL naming the phrase. Rule: `brand-kit.md §8`.

### 4.10 V10 — Chart integrity (conditional). Applies: `chart-card` surface with `has_axis == true`.
FAIL if `axis_min != 0 && break_disclosed == false` (Risk 3, flag-based). A card with `has_axis == false` (TGRERA) records V10 `skipped` (still requires source-stamp+wordmark via V8 / manifest, which are separate checks). Rule: `qa-checklist.md §Chart integrity` (y-axis from zero or break marked).

### 4.11 V11 — Data-provenance attestation (presence-based, Risk 5). Applies: whole asset.
The validator greps `meta.md` for a structured provenance attestation block delimited by:
```
<!-- provenance:start -->
... key: value lines ...
<!-- provenance:end -->
```
Required greppable keys inside the block (case-insensitive key match, non-empty value):
- `sources:` — the source class/attribution (e.g. `NewsMeter · Siasat · Deccan Chronicle`).
- `terrem_db_numbers:` — must read `none` / `no` (attestation that no TERREM DB numbers are used) OR name the verified real source rows.
- `as_of:` — a date token (`\d{4}-\d{2}-\d{2}` or month-day).
Absent block, or any required key missing/empty → **FAIL** (§6 provenance-missing). Present + keys satisfied → PASS. It is **presence-based, not semantic** (Risk 5): the validator does not verify the claim's truth. The deeper `qa-checklist.md §Data provenance` bullet items are emitted as informational `needs_review` entries (non-blocking, §5.4). Rule: `qa-checklist.md §Data provenance`.
**Authoring:** TGRERA `meta.md` gets this block added (§2) with `sources: NewsMeter · Siasat · Deccan Chronicle`, `terrem_db_numbers: none — public regulator orders only`, `as_of: 2026-06-30`.

### 4.12 V12 — Verdict output. Always.
Writes `render/qa-verdict.json` (§5.4) and the `meta.md` verdict block (§5.3). A single applicable FAIL sets overall `verdict:"FAIL"`, exit 1. All applicable PASS (skipped allowed) → `verdict:"PASS"`, exit 0.

### 4.13 Inter precedence (Risk 1) — what the validator does and does NOT check
Precedence enforced: human request > `brand-kit.md §2` > `qa-checklist.md`; heading/body face is **Inter**. The stale `qa-checklist.md` "IBM Plex Sans 600" line is corrected to "Inter 600" (§2). The validator does **NOT** implement a font-family check: font family is not recoverable from raster pixels, and the renderer already guarantees vendored Inter (S002/003, R4). No IBM Plex Sans check is implemented anywhere. This is stated so the Evaluator does not expect a font-family assertion.

### 4.14 Purity / no-network (R4 analog at validate time)
`validate.py` imports only stdlib + `PIL` + local `measure`. An AST/import scan (in tests or as an Evaluator probe) confirms no network module (`socket`, `urllib`, `http`, `requests`, `ssl`) is imported. No file writes outside `<asset-folder>/render/` and `<asset-folder>/meta.md`.

## 5. Outputs

### 5.4 `qa-verdict.json` (schema — produced verbatim to spec §5.4)
```json
{
  "schema_version": "1",
  "slug": "<slug>",
  "verdict": "PASS",
  "checked_on": "2026-07-04",
  "checked_by": "validator-cli",
  "checks": [ { "id": "V4-contrast", "surface": "chart-card", "element_bbox": [40,300,1000,220], "status": "PASS", "detail": "ratio 13.1:1 >= 4.5:1", "rule": "brand-kit.md §3" } ],
  "failed_checks": [],
  "needs_review": []
}
```
- `checks` = every check record (PASS/FAIL/skipped) in deterministic order (surface order, then check id, then element order).
- `failed_checks` = the subset with `status:"FAIL"` (each `{id, surface, detail, rule}`).
- `needs_review` = the `qa-checklist.md §Data provenance` bullet prompts (informational; do not block).
- `checked_on` is the only run-varying field (date); with `--checked-on` fixed the file is byte-deterministic (tests use a fixed date). Non-date fields are stable across runs on identical input.
- Written pretty-printed, `ensure_ascii=false`, `sort_keys` where it does not disturb the required key order, trailing newline (same convention as manifest writer).

### 5.3 `meta.md` verdict block (idempotent)
The human-readable verdict block (from `qa-checklist.md §Verdict`) is written **between delimited markers** so re-running replaces, never stacks:
```
<!-- qa-verdict:start -->
QA: PASS | FAIL
Failed checks: <list or none>
Checked by: validator-cli on YYYY-MM-DD
<!-- qa-verdict:end -->
```
If the markers already exist in `meta.md`, the block **between** them is replaced in place; otherwise the block is appended at end-of-file (preceded by one blank line). Running the validator twice yields a `meta.md` with **exactly one** verdict block (proven by test + Evaluator probe §10). The validator touches nothing else in `meta.md` (the provenance block and all prior content are preserved byte-for-byte outside the delimited region).

## 6. States that must exist (spec §6)

- **Missing folder / missing required file:** exit 2, stderr names the missing path. Writes nothing.
- **No render yet** (`manifest.json` or a referenced PNG absent): exit 2, stderr `manifest/PNG not found; run render first` naming the path. Not a crash/traceback.
- **Malformed manifest** (unparseable JSON, missing required field, `color`/`bg` outside the §9 token set): exit 2, stderr names the offending field/value. Tolerates **unknown extra fields** (e.g. the `chart_ref` field already present in the S003 manifest) — ignores them, does not choke.
- **Success (PASS):** all applicable checks PASS → `verdict:"PASS"`, exit 0, `qa-verdict.json` written, one verdict block in `meta.md`.
- **Failure (FAIL):** ≥1 applicable check FAIL → `verdict:"FAIL"`, exit 1, `failed_checks` populated with rule citations, verdict block says FAIL + lists failed checks. Nothing "fixed silently."
- **Blank/stub PNG:** manifest present, PNG has no ink where text is declared → V3 FAIL (exit 1). (Fixture in §7.)
- **Provenance missing:** no attestation block / missing required key in `meta.md` → V11 FAIL (exit 1).

## 7. Fixtures the Evaluator runs from the shell (arm the attack)

`tools/marketing-render/fixtures/` holds reproducible fixtures generated by `make_fixtures.py` (deterministic, committed). Each is a minimal `content/`-shaped folder or a crafted `manifest.json` + tiny PNG that trips exactly one check. The Evaluator runs `validate.py <fixture>` and observes the specific FAIL + rule. These prove the gate discriminates; they are **not** the Sprint-005 adversarial content assets.

Minimum fixtures (each FAILs on the named check, exit 1, correct rule cited):
- `fx-blank-png/` — correct manifest over an all-`bg` PNG → **V3 FAIL** (ink-present).
- `fx-low-contrast/` — a text element declaring a low-contrast token pair (e.g. `#57534e` on `#0d3d38`) → **V4 FAIL**.
- `fx-size-lie/` — manifest declares `font_px` at **2×** the truly-rendered glyph size → **V5 cross-check FAIL**.
- `fx-small-headline/` — carousel headline `font_px: 30` (< 48) → **V5 floor FAIL**.
- `fx-out-of-safezone/` — a headline bbox breaching the safe rect → **V6 FAIL**.
- `fx-11-word-hook/` — carousel slide-1 hook of 11 words → **V7 FAIL**.
- `fx-missing-source/` — chart-card surface with no `source-stamp` → **V8 FAIL**.
- `fx-blacklist/` — copy containing a `brand-kit.md §8` phrase → **V9 FAIL** naming it.
- `fx-truncated-axis/` — `has_axis:true, axis_min:20, break_disclosed:false` → **V10 FAIL**.
- `fx-no-provenance/` — asset with no provenance block in `meta.md` → **V11 FAIL**.
- `fx-canvas-mismatch/` — chart-card PNG rendered 1080×1080 → **V2 FAIL**.

A positive control fixture `fx-good-min/` (a minimal well-formed asset) must **PASS** (exit 0), proving the fixtures FAIL for the right reason and not because any asset trivially fails.

## 8. Test plan (`test_validate.py`, stdlib unittest)

Run: `python3 -m unittest discover -s tools/marketing-render/tests -v` (the whole suite — S001/002/003 must still pass; no regression).

Coverage (each check proven to PASS on good input AND FAIL on its violation, feeding crafted manifest dicts + tiny generated PNGs — no network, no reliance on external assets except the real TGRERA render for the calibration/positive path):
1. **V2** dims match / mismatch (crafted 1080×1080 PNG).
2. **V3** real-ink bbox passes; all-`bg` crop fails; calibration values asserted (real TGRERA elements clear `INK_MIN_PX` with margin; blank = 0).
3. **V4** `#1c1917`/`#faf8f3` passes ~13:1; `#57534e`/`#0d3d38` (or similar) fails; delegates to `measure.contrast_check`.
4. **V5 floor** carousel headline 30 fails, 48 passes; chart-card headline 36 passes; exempt roles auto-pass.
5. **V5 cross-check** real TGRERA render: every element consistent within ±25%; a manifest with 2× `font_px` fails; a manifest with 0.5× fails. `K_INTER` value asserted.
6. **V6** in-zone passes; out-of-zone fails; source-stamp/wordmark exempt (skipped).
7. **V7** 10-word passes, 11-word fails, no-hook asset → skipped.
8. **V8** TGRERA stamp passes; stamp missing date fails; stamp absent fails.
9. **V9** clean copy passes; injected blacklist phrase fails, naming it.
10. **V10** `has_axis:false` skipped; `axis_min:20,break_disclosed:false` fails; `break_disclosed:true` passes.
11. **V11** present-full-block passes; missing block fails; block missing a required key fails.
12. **V12 / verdict** one FAIL → `verdict:"FAIL"` exit 1; all pass → PASS exit 0; `qa-verdict.json` matches §5.4 shape.
13. **meta idempotency** validate twice → exactly one `<!-- qa-verdict:start -->` block; prior content preserved.
14. **states** missing folder → exit 2; missing manifest → exit 2; color-outside-token manifest → exit 2 naming field; unknown extra field (`chart_ref`) tolerated.
15. **purity** AST scan: no network import in `validate.py`.
16. **determinism** with fixed `--checked-on`, two runs on TGRERA produce byte-identical `qa-verdict.json`.

## 9. Acceptance — commands & expected results (Evaluator reproduces)

Preconditions: TGRERA already rendered (S003). If not: `python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave`.

1. **Unit suite** — `python3 -m unittest discover -s tools/marketing-render/tests -v` → OK, exit 0; S001/002/003 counts unchanged (no regression); new V2–V12 tests present.
2. **TGRERA PASS end-to-end (this sprint's demo)** —
   `python3 tools/marketing-render/validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on 2026-07-04`
   → exit **0**; stdout ends `VERDICT: PASS`; `render/qa-verdict.json` has `verdict:"PASS"`, `failed_checks:[]`, V7/V10 recorded `skipped` (N/A for a chart-card/`has_axis:false` asset), V2/V3/V4/V5/V8/V9/V11 `PASS`; `meta.md` has exactly one `QA: PASS` verdict block and the provenance block preserved.
3. **Idempotency** — run step 2 again → `meta.md` still has exactly **one** verdict block; `qa-verdict.json` byte-identical.
4. **Each fixture FAILs on its check** — for every `fx-*` in §7: `python3 tools/marketing-render/validate.py tools/marketing-render/fixtures/<fx>` → exit 1, stdout names the expected `Vn` + rule; `fx-good-min` → exit 0.
5. **Error states** — validate a nonexistent folder → exit 2 + stderr; validate an asset whose `render/manifest.json` is deleted → exit 2 + "run render first"; a manifest with a non-token color → exit 2 naming the field.
6. **Purity probe** — `python3 -c "import ast,sys; ..."` (or grep) confirms no network import in `validate.py`.
7. **Contrast spot-check** — assert source-stamp `#57534e` on `#faf8f3` at 20px/400 is treated as **normal** text (threshold 4.5) and still passes (~7:1) — i.e. exempt-from-size ≠ exempt-from-contrast.

## 10. Evaluator probes (Python, since no browser)

- Open `qa-verdict.json`; assert schema keys (§5.4), `verdict`, every check `status ∈ {PASS,FAIL,skipped}`, each FAIL carries a `rule`.
- Confirm V7 and V10 are `skipped` for TGRERA (not silently absent, not false FAIL).
- Grep `meta.md` for exactly one `<!-- qa-verdict:start -->` … `<!-- qa-verdict:end -->` after two runs; confirm provenance block still present.
- Blank-PNG probe: point the validator at `fx-blank-png` and confirm V3 FAIL (not a false PASS from a matching manifest).
- Size-lie probe: `fx-size-lie` → V5 cross-check FAIL, proving the manifest cannot lie about font size.
- Token probe: hand-edit a fixture manifest `color` to `#123456` → exit 2 naming the field.

## 11. Non-goals (restate, spec §8)

No video/animation. No LinkedIn 1200×627 / PDF carousel checks. No auto-fixing (validator reports, never edits copy or re-layouts). No content generation. No font-family raster check / no IBM Plex check (§4.13). No Sprint-005 adversarial content asset folders, README wiring, or `/loop-qa` skill update. No changes outside this repo. No network at validate time.

## 12. Risks this sprint carries (disclosed)

- **R-A (V5 calibration):** `K_INTER` and the ±25% band are calibrated on the real TGRERA render; if a future asset uses very different glyph mixes (all-caps, all-descenders) the effective-px estimate drifts. Mitigation: band is wide (±25%) and discrimination target is a 2× lie; per-line median reduces multi-line noise. Recorded in trace with the measured numbers.
- **R-B (V3 thresholds):** `INK_TOL`/`INK_MIN_PX` calibrated on real render + blank fixture; anti-aliased edges counted, so tiny elements (wordmark 102×30) must still clear `INK_MIN_PX` — verified on TGRERA.
- **R-C (V8 date detection):** regex-based date presence could miss an exotic date format; TGRERA uses ISO + `Jun 22` forms, both matched. Documented as presence-based, not a date parser.
- **R-D (provenance presence-only):** V11 does not verify truth (Risk 5, by design); deeper checks surface as `needs_review`.
