# Sprint 001 Contract — Measurement Core + Schema-v2 Seam (pure, unit-tested, no rendering)

Run 003 · Renderer V2 Format Library + QA Gate V2
Spec refs: §5.1 (R11/R12/R14), §5.2 (V13/V14/V15/V17/V18/V19), §5.3 (manifest v2), §5.4 (meta blocks), §9 (tokens), §10 Risks 1/3/4/5/6, §11 Sprint-001 row.

---

## 0. One-paragraph scope

This sprint adds **pure measurement functions** to `tools/marketing-render/measure.py` and **widens the manifest-schema acceptance** in `tools/marketing-render/validate.py` so that a schema-v2 format-slide manifest validates structurally. It renders **nothing**, opens no PNG, produces no PDF, and wires **no** new V-check into `run_checks`. It establishes the renderer↔validator seam and the arithmetic the later sprints call. All additions are additive: existing `measure.py` functions and constants (`_TYPE_MINIMUMS`, `type_min_ok`, `size_consistent`, contrast, safe-zone, blacklist) are **not mutated**; the existing `_validate_manifest_schema` is only **widened** (nothing previously accepted becomes rejected).

Playwright is **not applicable** — this project has no browser UI. This is a CLI/pure-library sprint. The Evaluator attacks it with `python3 -m unittest` and a shell-driven adversarial matrix (§8), not click paths.

---

## 1. Exact user-visible behaviors (library-level; the "user" is the QA agent / later sprints calling these functions)

### 1.1 New pure functions in `measure.py` (additive — no existing symbol touched)

**A. Dominant-element ratio (V13 core) — `body_reference` + `dominant_ratio`**

- `body_reference(elements) -> int` — returns the **max** `font_px` among elements whose `role == "body"`; if the surface has **no** body element, returns the fallback floor **26** (spec §5.2 V13, Risk 3).
- `count_dominant(elements) -> int` — number of elements with `role == "dominant"`.
- `is_utility_slide(elements) -> bool` — True iff every element's role ∈ `{"so-what", "source-stamp", "wordmark"}` (the V13-exempt utility roles) **and** the element list is non-empty. Any element carrying a content role (`headline`/`hook`/`body`/`chart-label`/`dominant`) makes it **not** a utility slide.
- `dominant_ratio_ok(elements) -> dict` returning
  `{"exempt": bool, "dominant_count": int, "body_reference": int, "dominant_font_px": int|None, "ratio": float|None, "passes": bool, "reason": str}`:
  - If `is_utility_slide(elements)` → `{"exempt": True, ..., "passes": True, "reason": "utility slide (subset of {so-what, source-stamp, wordmark}); V13 exempt"}`.
  - Else require **exactly one** dominant. `dominant_count == 0` → `passes False`, reason `"no dominant element on content slide"`. `dominant_count >= 2` → `passes False`, reason `"N dominant elements; exactly one required"`.
  - With exactly one dominant: `ratio = dominant.font_px / body_reference`; `passes = ratio >= 3.0` (compared on the **raw** float, no rounding-up). Reason names the ratio and the 3× rule when it fails.
- Boundary is exact: `body_reference = 26`, `dominant.font_px = 78` → `ratio = 3.0` → **pass**; `dominant.font_px = 77` → `ratio ≈ 2.96` → **fail**.

**B. Raised type floors for format-slide surfaces (V14 core) — `format_slide_type_min`**

- New module-level table `_V2_TYPE_MINIMUMS` (a **new** dict; `_TYPE_MINIMUMS` stays byte-for-byte unchanged):

  | element role | v2 floor (px) | source |
  |---|---|---|
  | `headline` | 48 | §5.2 V14 |
  | `hook` | 48 | §5.2 V14 |
  | `dominant` | 48 | contract decision (see note) |
  | `body` | 26 | §5.2 V14 |
  | `chart-label` | 26 | §5.2 V14 |
  | `so-what` | 26 | contract decision (see note) |
  | `source-stamp` | 24 | §5.2 V14 |
  | `wordmark` | `None` (exempt) | §5.2 V14 |

  **Contract decisions (documented, conscious — not accidental):** V14's prose pins floors for `headline`/`hook`/`body`/`chart-label`/`source-stamp`/`wordmark` but is silent on the two new v2 roles. This contract pins **`so-what` → 26** (a body-class utility line) and **`dominant` → 48** (a headline-class figure). The `dominant` floor is **deliberately redundant**: V13 already forces `dominant.font_px ≥ 3 × 26 = 78`, so a 48 floor can never be the binding constraint — it exists only for table completeness and to give a graceful floor when V13 is bypassed. Neither decision weakens any existing rule.
- `format_slide_type_min(element_role, font_px) -> dict` returns `{"minimum": int|None, "passes": bool}`. Exempt role (`None` minimum) → `passes True`. Unknown role → `ValueError` naming the role. This function is **keyed only on element role** (surface role is always `format-slide` by construction; routing by surface role happens at the validator in Sprint 005).
- Boundaries: `body` 26 → pass, 25 → fail; `source-stamp` 24 → pass, 23 → fail; `source-stamp` 20 (the old v1 exempt value) → **fail** on v2; `headline` 48 → pass, 47 → fail.

**C. Thumbnail effective-px comparator (V15 core, measured-px route) — `thumbnail_ink_ok`**

- V15 is, per **Risk 4**, a **measured-pixel** check, never a `font_px` predictor. This sprint therefore ships only the **comparator + scale factor + pinned thresholds** — the exact function Sprint 005's real-PNG-downscale path will call — and ships **no** `font_px → pass` function (that would be the Risk-4-forbidden arithmetic route and is an explicit non-goal).
- Pinned constants (fixed integers, contract-pinned):
  - `THUMB_W = 360`, `CANVAS_W = 1080`, scale factor = `THUMB_W / CANVAS_W = 1/3`.
  - `THUMB_HEADLINE_MIN_PX = 13`
  - `THUMB_DOMINANT_MIN_PX = 21`
- `thumbnail_scale_band(full_band_px, canvas_w=1080, thumb_w=360) -> float` — the pure downscale of a full-canvas ink-band height to its 360px-preview effective height = `full_band_px * thumb_w / canvas_w`. (Pure arithmetic; the *source* of `full_band_px` is a real PNG ink measurement wired in Sprint 005 — not here.)
- `thumbnail_ink_ok(role, effective_px) -> dict` returning `{"role": role, "minimum": int, "effective_px": float, "passes": bool}`:
  - `role == "headline"` or `"hook"` → threshold `THUMB_HEADLINE_MIN_PX` (13).
  - `role == "dominant"` → threshold `THUMB_DOMINANT_MIN_PX` (21).
  - any other role → `ValueError` (V15 only gates headline/hook + dominant).
  - `passes = effective_px >= threshold` on the raw float.
- Boundaries: headline `effective_px = 13.0` → pass, `12.99` → fail; dominant `21.0` → pass, `20.99` → fail.
- **Threshold provenance (honest):** 13 and 21 are derived arithmetically from the locked v1 ink constant (`K_INTER = 0.83`, ink-band ≈ `0.83 × font_px`) and the floors — headline `0.83 × 48 / 3 ≈ 13.3`, dominant `0.83 × 78 / 3 ≈ 21.6` — recorded here as a **comment only**, so measure.py takes no dependency on validate.py's `K_INTER`. Because **no v2 render exists yet**, these integers are **provisional pending Sprint-006 real-render revalidation**. The binding invariant the later sprints must preserve: *the v2 positive control clears 13/21 at 360px AND the thumbnail-illegible adversarial fixture fails them.* If the real TGRERA render does not clear 13/21 with margin, the thresholds are consciously adjusted in a later contract (never silently, never below the point where the illegible fixture still fails). This sprint pins the integers and unit-tests only the comparator boundary.

**D. `meta.md` cover-pattern / one-dataset block parser (V17 + V19 core) — `parse_cover_pattern_block`**

- Modeled on the existing `_parse_provenance_block` (validate.py) and the `<!-- provenance:start -->` grammar.
- Block markers: `<!-- cover-pattern:start -->` … `<!-- cover-pattern:end -->`, containing `key: value` lines (`#`-comments after the value tolerated and stripped, matching §5.4's inline-comment example).
- `parse_cover_pattern_block(meta_text) -> dict|None` — returns `{"pattern": str, "one_dataset": str}` (lowercased keys, verbatim values, trailing `# …` comment stripped) or `None` when the block is absent.
- `VALID_COVER_PATTERNS = frozenset({"BIG-NUMBER", "CHART-FIRST"})`.
- `cover_pattern_valid(parsed) -> bool` — True iff `parsed` is not `None`, has a non-empty `pattern` ∈ `VALID_COVER_PATTERNS` (V17). (The `one_dataset` presence check for V19 is a separate predicate: `one_dataset_present(parsed) -> bool` = parsed is not None and `parsed.get("one_dataset")` is a non-empty string. Presence only — never semantic, per Risk 5.)
- These are **parser + validity predicates only**; they are **not** wired into `run_checks` this sprint (that is Sprint 005 V17/V19).

### 1.2 Widened manifest schema in `validate.py` (`_validate_manifest_schema` only)

- Accept `schema_version` `"2"` in addition to `"1"`. (The current code already does not gate on the value, but the contract fixes the accepted set and tests it.)
- Extend the accepted **surface-role** set used by the schema validator to include `"format-slide"` (v1 roles `carousel-slide`, `chart-card` still accepted).
- Extend the accepted **element-role** set to include `"dominant"` and `"so-what"` (v1 roles unchanged).
- Accept, without erroring, the new **per-surface `format`** key with value ∈ `{BIG-NUMBER, TIMELINE, RECEIPTS, VS-CONTRAST, LEADERBOARD, CHART, CHECKLIST}`. A `format` key present on a `format-slide` surface with a value **outside** that set → `PreconditionError` naming the surface and the offending value. `format` on a v1 surface is tolerated/ignored (extra-field tolerance, matching current `chart_ref` behavior).
- Accept, without erroring, the new **top-level `pdf`** key (string filename). Old manifests lacking it still validate (already true; contract fixes and tests it).
- **Isolation guarantee (Risk 1 / advisor flag):** this sprint edits **only** the schema-acceptance frozensets local to `_validate_manifest_schema` (or new schema-local sets). It does **NOT** add `format-slide` to the **check-routing** structures (`_FORMAT_BY_ROLE`, `_SAFEZONE_ROLES`, the V8/V5 routing) and does **NOT** call `run_checks` on a format-slide surface. Wiring V13–V19 and routing format-slide surfaces through checks is **Sprint 005** (explicit non-goal here). Rationale: routing a v2 surface through the v1 checks before V13–V19 exist would crash (`type_min_ok` unknown surface_role) or mis-fire V8 — a shipped-but-untested bug. Keeping the widening to the schema gate contains it.

---

## 2. Routes / screens / components affected

No routes/screens (no UI). Files affected:
- `tools/marketing-render/measure.py` — **add** functions/constants in §1.1. No existing symbol edited.
- `tools/marketing-render/validate.py` — **widen** `_validate_manifest_schema` + its schema-local role sets per §1.2. No check logic edited.
- `tools/marketing-render/tests/test_measure.py` — **add** test classes for the new functions (existing tests untouched).
- `tools/marketing-render/tests/test_validate.py` — **add** schema-widening tests (existing tests untouched).

**Out of scope (do not touch):** `render.py`, `acceptance.py`, `measure.py`'s existing `_TYPE_MINIMUMS`/`type_min_ok`/`size_consistent`/contrast/safe-zone/blacklist, any fixture under `fixtures/`, any file outside `tools/marketing-render/`, `run_checks` and all `_check_v*` functions.

---

## 3. Data / state transitions

Pure functions — no persistent state, no mutation of inputs. `parse_cover_pattern_block` reads a string argument (caller-provided `meta.md` text), opens no file itself. `measure.py` continues to touch the filesystem only via the pre-existing `parse_blacklist(brand_kit_path)` (unchanged). No new file I/O, no network, deterministic outputs for identical inputs.

---

## 4. Empty / loading / success / error / invalid states

- **Empty elements list** → `body_reference([])` returns fallback 26; `is_utility_slide([])` returns `False` (empty is not a utility slide); `dominant_ratio_ok([])` → not exempt, `dominant_count == 0` → `passes False`, reason `"no dominant element on content slide"`.
- **Missing block** → `parse_cover_pattern_block(text_without_block)` returns `None`; `cover_pattern_valid(None)` → `False`; `one_dataset_present(None)` → `False`.
- **Invalid pattern value** → block with `pattern: TIMELINE` → parsed dict returned, `cover_pattern_valid` → `False` (not in `VALID_COVER_PATTERNS`).
- **Unknown role** → `format_slide_type_min("banana", 40)` and `thumbnail_ink_ok("body", 30)` raise `ValueError` naming the role.
- **Malformed manifest** → `_validate_manifest_schema` still raises `PreconditionError` naming the offending field (v1 behavior preserved); v2 manifest with a `format` value outside the 7-tag set raises naming surface + value.
- **No loading state** (synchronous pure functions).

---

## 5. Keyboard / focus / ARIA / contrast / responsive

Not applicable — no UI, no DOM, no viewport. (Contrast math in `contrast_check` is pre-existing and untouched.) Stated explicitly so the Evaluator does not treat the omission as a gap.

---

## 6. Security / privacy assumptions

- No network at any point (import-time or call-time). Evaluator may assert this by running the suite with network disabled.
- No secrets, tokens, or credentials introduced. No `.env`, no DB writes.
- No new third-party dependency: stdlib + the already-vendored Pillow only. `measure.py` gains **no** new imports beyond stdlib `re` (already present).
- No reading of any file outside the repo; `parse_cover_pattern_block` takes a string, not a path.

---

## 7. Commands to run (Evaluator)

From repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`:

```bash
# (a) Full render suite — MUST stay green (139 baseline, extended with new tests; count rises, never falls)
python3 -m unittest discover -s tools/marketing-render/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"

# (b) Full loop suite — MUST stay green and unchanged (254 baseline)
python3 -m unittest discover -s tools/marketing-loops/tests 2>&1 | grep -E "^(Ran|OK|FAILED)"

# (c) New measurement tests in isolation (verbose)
python3 -m unittest -v tools.marketing-render.tests.test_measure 2>/dev/null || \
python3 -m unittest discover -s tools/marketing-render/tests -p 'test_measure.py' -v

# (d) No-network sanity (import must not touch network)
python3 -c "import sys; sys.path.insert(0,'tools/marketing-render'); import measure, validate; print('import-ok')"
```

**Baselines confirmed before this sprint (generator_trace.log):** render suite `Ran 139 tests … OK`; loop suite `Ran 254 tests … OK`. After this sprint the render count MUST be **> 139** (new tests added) and still `OK`; the loop count MUST stay **254 … OK** (loop suite does not import `validate`/`measure` — verified: only doc-comment references in `enqueue.py`/`verify_utm.py`).

---

## 8. Adversarial matrix the Evaluator should run (replaces Playwright click paths)

Each row is a distinct, isolable attack. The Evaluator may add these as ad-hoc asserts against the imported `measure`/`validate` modules; the Generator ships them as unit tests too.

| # | Attack | Expected result |
|---|---|---|
| 1 | `dominant_ratio_ok` with body_ref 26, dominant 78 | `passes True`, ratio 3.0 |
| 2 | body_ref 26, dominant 77 | `passes False`, ratio < 3 |
| 3 | zero dominant elements, has a `body` element | `passes False`, reason names "no dominant" |
| 4 | two dominant elements | `passes False`, reason names "2 dominant … exactly one" |
| 5 | elements = `[{role:"so-what"…},{role:"wordmark"…}]` | `exempt True`, `passes True` |
| 6 | elements = `[{role:"source-stamp"…},{role:"wordmark"…}]` | `exempt True`, `passes True` |
| 7 | utility roles + one `body` element | `exempt False` (content role present) → must carry a dominant |
| 8 | body_reference with NO body element | returns 26 (fallback) |
| 9 | `format_slide_type_min("body", 26)` / `("body", 25)` | pass / fail |
| 10 | `format_slide_type_min("source-stamp", 24)` / `(…, 23)` / `(…, 20)` | pass / fail / fail |
| 11 | `format_slide_type_min("headline", 48)` / `(…, 47)` | pass / fail |
| 12 | `format_slide_type_min("wordmark", 8)` | pass (exempt) |
| 13 | `format_slide_type_min("banana", 40)` | `ValueError` |
| 14 | `thumbnail_ink_ok("headline", 13.0)` / `(…, 12.99)` | pass / fail |
| 15 | `thumbnail_ink_ok("dominant", 21.0)` / `(…, 20.99)` | pass / fail |
| 16 | `thumbnail_ink_ok("body", 30)` | `ValueError` |
| 17 | `thumbnail_scale_band(39.84)` | `13.28` (≈, `full/3`) |
| 18 | `parse_cover_pattern_block` on valid block | `{pattern:"BIG-NUMBER", one_dataset:"…"}` |
| 19 | `cover_pattern_valid` on `pattern: CHART-FIRST` | `True` |
| 20 | `cover_pattern_valid` on `pattern: TIMELINE` (invalid) | `False` |
| 21 | `parse_cover_pattern_block` on text with no block | `None`; `cover_pattern_valid(None)` False; `one_dataset_present(None)` False |
| 22 | `_validate_manifest_schema` on a v1 manifest (schema_version "1", carousel-slide) | no raise (still accepted) |
| 23 | `_validate_manifest_schema` on a v2 manifest (schema_version "2", format-slide, format RECEIPTS, dominant+so-what+wordmark, top-level `pdf`) | no raise |
| 24 | v2 manifest with `format: "BOGUS"` on a format-slide | `PreconditionError` naming surface + value |
| 25 | v1 manifest missing a required element field | `PreconditionError` naming the field (unchanged v1 rejection) |
| 26 | v1 manifest with a non-token color | `PreconditionError` naming the field (unchanged) |

**Widening invariant (must hold):** every manifest that `_validate_manifest_schema` accepted before this sprint still validates; no previously-accepted manifest becomes rejected. Rows 22/25/26 guard this.

---

## 9. Explicit non-goals (Sprint 001)

- **No rendering.** No PNG, no PDF, no Pillow draw calls, no `render.py` edits.
- **No V-check wiring.** V13–V19 are **not** added to `run_checks`; format-slide surfaces are **not** routed through any `_check_v*`. (Sprint 005.)
- **No `_FORMAT_BY_ROLE` / `_SAFEZONE_ROLES` / V8 / V5 routing edits.** Check-routing structures untouched.
- **No `font_px → thumbnail pass` predictor** (Risk-4-forbidden; V15 stays a measured-pixel check whose comparator only is shipped here).
- **No mutation** of `_TYPE_MINIMUMS`, `type_min_ok`, `size_consistent`, or any existing `measure.py`/`validate.py` symbol.
- **No `acceptance.py` change**, no fixture change, no `meta.md`/manifest emission.
- **No semantic "one dataset" judgment** — V19 is presence-only (Risk 5).
- **No new dependency, no network, no writes outside `tools/marketing-render/`.**

---

## 10. Definition of done (what the Evaluator can verify on disk)

1. `measure.py` gains, additively: `body_reference`, `count_dominant`, `is_utility_slide`, `dominant_ratio_ok`, `_V2_TYPE_MINIMUMS`, `format_slide_type_min`, `THUMB_W`/`CANVAS_W`/`THUMB_HEADLINE_MIN_PX`/`THUMB_DOMINANT_MIN_PX`, `thumbnail_scale_band`, `thumbnail_ink_ok`, `parse_cover_pattern_block`, `VALID_COVER_PATTERNS`, `cover_pattern_valid`, `one_dataset_present`. All existing symbols byte-unchanged.
2. `validate.py`'s `_validate_manifest_schema` accepts schema_version "2", `format-slide` surface role, the 7 `format` tags (rejecting bogus ones), `dominant`/`so-what` element roles, and top-level `pdf`; still accepts every v1 manifest and still rejects every previously-rejected malformed manifest naming the field.
3. `tools/marketing-render/tests/` covers the full §8 matrix (26 rows) as unit tests.
4. Render suite: `Ran N tests … OK` with `N > 139`. Loop suite: `Ran 254 tests … OK`.
5. `generator_trace.log` records the baseline (139/254), the files changed, the new-test count, and the passing run output, plus the disclosed risks (provisional 13/21 thresholds; schema-widening-only isolation).

This contract is testable end-to-end by running §7 commands and the §8 matrix. If any row cannot be executed against the shipped code, the contract is not met.
