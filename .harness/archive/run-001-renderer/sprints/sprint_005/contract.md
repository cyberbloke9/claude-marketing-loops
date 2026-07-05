# Sprint 005 Contract — Adversarial fixtures, wiring & end-to-end acceptance

Status: PROPOSED (revised per contract_review.md — B-001, B-002, B-003, H-001, H-002, H-003, H-004 addressed)
Sprint: 005 (final sprint)
Depends on: Sprint 001 (`measure.py`, PASSED), 002 (carousel renderer, PASSED), 003 (chart-card renderer + TGRERA `chart-spec.md`, PASSED), 004 (`validate.py` + `qa-verdict.json` + `meta.md` verdict block + the 12 committed fixtures under `tools/marketing-render/fixtures/`, PASSED score 4.8).
Spec refs: §4 (stories 3 "trust the gate", 4 "ship the reference asset"), §5.1 R8 (determinism), §5.4 (`qa-verdict.json` seam consumed by `/loop-qa`), §9 (verdict-consumption, no-network, in-repo only), §11 (Sprint 005), §1 verification standard ("validator attacked with violating **fixtures** … **and the TGRERA asset passing end-to-end**").

## 0. Purpose & why there is no Playwright path

This sprint closes the toolchain with three genuinely-new deliverables and one end-to-end acceptance run:

1. **README wiring** — a documented, copy-paste-runnable section for the render + validate CLIs and the acceptance runner. The README today (~50 lines) does not mention `tools/marketing-render/` at all.
2. **`/loop-qa` skill rewrite** — replace the manual "walk the checklist by hand" prose prompt with one that invokes `validate.py` and consumes `qa-verdict.json` mechanically.
3. **`tools/marketing-render/acceptance.py`** — a single deterministic, no-network command that proves the whole gate in one run: TGRERA renders + validates **PASS** end-to-end, and every committed fixture reaches its expected verdict on the correct check with the correct rule cited.

It is a **headless Python CLI toolchain** — same as Sprints 002/003/004. There is **no browser and no web UI, therefore no Playwright click-path exists.** The Evaluator attacks the CLIs directly from the shell and probes `qa-verdict.json` / `meta.md` / the acceptance summary with the commands in §7 and the Python probes in §8. This is intentional and stated so the contract is fully testable.

## 1. Language / runtime decision

- **Python 3** (`/usr/bin/python3`, 3.9.6) — same runtime as S002/003/004. `acceptance.py` imports only Python stdlib (`argparse`, `json`, `subprocess`, `sys`, `pathlib`, `shutil`, `hashlib`) to invoke the existing CLIs as subprocesses and parse their `qa-verdict.json` output. **No new third-party dependency; no network.** Pillow is used only transitively by the invoked `render.py`/`validate.py`, not imported by `acceptance.py`.
- Invoking the CLIs as subprocesses (not importing their `main()`) means the acceptance runner exercises the exact shell contract a real operator or the `/loop-qa` skill uses — exit codes and stdout included.

## 2. Scope (including the adversarial-case boundary — set upfront, not discovered)

### 2.1 In scope (Sprint 005)
- `README.md` — add a runnable "Asset Renderer + QA Gate" section (§4, exact text in §4.1). Additive only; no existing loop docs removed.
- `.claude/skills/loop-qa/SKILL.md` — rewrite to invoke `validate.py` and consume `qa-verdict.json` (§5).
- `tools/marketing-render/acceptance.py` — the end-to-end acceptance runner (§6).
- `tools/marketing-render/tests/test_acceptance.py` — stdlib `unittest` tests for the runner's expectation table + exit logic (§3).
- Verified end-to-end acceptance: TGRERA fresh-render → validate PASS; all 12 committed fixtures reach their expected verdict on the right rule (§6.2 table, §7).

### 2.2 Scope boundary on adversarial cases (design choice, declared upfront)

The renderer is **compliant-by-construction**: `render.py` refuses to emit a non-compliant asset. This is a design strength, not a gap, and it fixes which adversarial cases are end-to-end vs. fixtures:

- `render.py` raises `ValueError` on `has_axis: true` (cannot emit a truncated/undisclosed-axis card).
- `render.py` requires a `source-stamp` element and raises `ValueError` if absent (cannot emit a missing-source card).
- `render.py` binds locked brand tokens to fixed roles and never emits an author-chosen low-contrast pair.
- `render.py` always inks real vendored-Inter glyphs; it never emits a blank/near-blank PNG.

Therefore, **only the 11-word-hook case can round-trip the renderer end-to-end** (the carousel renderer draws whatever hook text it is given; V7 is a spec-level word-count check). The other named adversarial cases (truncated-axis, low-contrast, missing-source, blank-png) and all robustness fixtures are **pre-crafted manifest + PNG combinations already committed in Sprint 004**. The acceptance runner tests these fixtures directly by invoking `validate.py` against them — it does **not** render them (which would require disabling the renderer's guards). The **TGRERA asset is the positive end-to-end case** (authored spec → render → validate → PASS).

This boundary is grounded in the spec's own wording: §1 verification standard names these as "violating **fixtures**" and reserves "**end-to-end**" for the TGRERA asset; §11 lists them under "Adversarial **fixtures**." The prior Sprint 004 contract's aspiration to author full `content/` adversarial folders is superseded here because it would contradict the spec's non-goals (§8, no auto-fix / no compliance-gutting) and the compliant-by-construction renderer. If the Evaluator holds the literal S004 aspiration over the spec's plain reading, this §2.2 is the intended point of contest — the contract argues the spec governs.

### 2.3 Explicitly NOT in this sprint (declared, not silently omitted)
- **No new `content/` adversarial asset folders** (§2.2 rationale). The adversarial cases are the committed S004 fixtures.
- **No new render-through adversarial asset** (e.g. a real `content/` 11-word-hook carousel). The render-through positive path is TGRERA.
- **No source changes to `render.py`, `validate.py`, `measure.py`, `make_fixtures.py`,** or any existing `tools/marketing-render/tests/test_*.py` from prior sprints, or any `brand/`, `signals/`, `personas/`, `metrics/`, `PLAN.md`, `RESEARCH.md`. The acceptance runner is a new consumer that invokes them unchanged.
- **No fixture regeneration as a gate step.** `acceptance.py` does NOT run `make_fixtures.py`; it consumes the committed fixture artifacts as-is (regenerating would rewrite committed bytes and add a determinism dependency to the gate).
- No video/animation, no LinkedIn/PDF surfaces, no auto-fixing, no content generation, no network at any time, no CI/scheduler integration beyond CLI-runnability + README docs (spec §8). No changes to any other repo or to the live TERREM product.

## 3. Test plan (`test_acceptance.py`, stdlib unittest)

Run the whole suite: `python3 -m unittest discover -s tools/marketing-render/tests -v` — S001–004 tests must still pass unchanged (no regression), plus the new acceptance tests.

Coverage:
1. **Expectation table completeness** — assert the runner's expectation table contains exactly the 12 fixture rows named in §6.2 (all `fx-*` directories except `make_fixtures.py`), each with `{fixture, expected_exit, expected_check_id, expected_rule_substring}`, and that `fx-good-min` has `expected_exit=0` with no expected check id. If a new fixture directory exists that is not in the table, the test FAILs (table must cover the full committed set).
2. **PASS-detection logic** — feed a synthetic `qa-verdict.json` dict with `verdict:"PASS"`/`failed_checks:[]` → runner's checker returns success for a PASS expectation; a `verdict:"FAIL"` dict → returns failure.
3. **FAIL-detection logic** — feed a synthetic `failed_checks` containing `{id:"V7-hook-words", rule:"qa-checklist.md §Carousel"}` → the runner confirms the expected check id + rule substring are present; a FAIL on the *wrong* check id (e.g. `V4-contrast` when `V7-hook-words` expected) → the runner reports a **mismatch** (the gate must not accept "some FAIL", only "the RIGHT FAIL").
4. **Overall exit logic** — all expectations met → runner returns 0; any single expectation unmet (wrong exit code, missing expected check, or PASS where FAIL expected) → runner returns non-zero.
5. **Purity** — an AST import scan (the exact script in §8) asserts `acceptance.py` imports no network module (`socket`, `urllib`, `http`, `requests`, `ssl`, `httplib`, `ftplib`).

The runner's *invocation* of the real CLIs against the real TGRERA render + real fixtures is exercised by the acceptance run itself (§7 command), which is the primary end-to-end evidence; the unittest layer proves the runner's decision logic in isolation so a green run cannot be a false positive from broken comparison logic.

## 4. README wiring (§0 deliverable 1)

Add one section to `README.md` (heading `## Asset Renderer + QA Gate`), additive, at the end of the file. §4.1 below gives the exact text that MUST be inserted. The command syntax, slug (`content/2026-07-03-tgrera-enforcement-wave`), and flags (`--checked-on 2026-07-04`) are normative: every fenced command must be literally runnable as written from the repo root (verified in §7 step 6). No placeholder slugs, no invented flags.

CLI ground truth confirmed against the committed code (do not deviate):
- `render.py` takes one positional `asset_folder`; exit 0 success, exit 1 error.
- `validate.py` takes one positional `asset_folder` plus optional `--checked-on YYYY-MM-DD` (defaults to today) and `--checked-by`; exit 0 PASS, exit 1 FAIL, exit 2 precondition/usage error.
- `acceptance.py` (this sprint) takes optional `--checked-on YYYY-MM-DD` (default `2026-07-04`, the sprint baseline — see §6, H-001) and `--verbose`; exit 0 iff the whole gate holds.

### 4.1 Exact README text to insert (normative)

Insert verbatim (wording may be lightly adjusted for prose flow, but the heading, the three fenced commands, the exit-code line, and the determinism/no-network + `/loop-qa` sentences MUST appear exactly as their commands/claims below):

```markdown
## Asset Renderer + QA Gate

A deterministic, no-network CLI toolchain under `tools/marketing-render/` renders an
authored asset folder (`content/<slug>/`) into brand-locked PNGs plus a `manifest.json`,
then mechanically validates the PNGs + specs against `brand/qa-checklist.md`, emitting a
machine-readable `qa-verdict.json` and a human verdict block in the asset's `meta.md`.

### Render

Render an asset folder to PNGs and a manifest:

python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave

Writes `content/2026-07-03-tgrera-enforcement-wave/render/{chart-card.png, manifest.json}`.

### Validate

Validate the rendered asset against the QA checklist:

python3 tools/marketing-render/validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on 2026-07-04

Writes `render/qa-verdict.json` and appends the verdict block to `meta.md`.
Exit `0` = PASS, `1` = FAIL, `2` = usage/precondition error.

### End-to-end acceptance

Prove the whole gate in one run (TGRERA render + validate PASS; every committed
adversarial fixture FAILs on its named check; the positive-control fixture PASSes):

python3 tools/marketing-render/acceptance.py --checked-on 2026-07-04

Exit `0` iff the full gate holds.

### Determinism & no network

Fonts are vendored under `tools/marketing-render/fonts/` (Inter, SIL OFL, `OFL.txt`
present). No network is accessed at render or validate time; re-rendering the same input
yields pixel-identical PNGs (R8). The `--checked-on` date only affects the `checked_on`
field of `qa-verdict.json`, never the PNG bytes.

For agent-based validation, the `/loop-qa` skill wraps `validate.py`, consuming
`qa-verdict.json` mechanically.
```

(The three commands must be inside fenced code blocks in the actual README so they are copy-pasteable; the block above shows them un-nested only because this contract is itself Markdown.)

## 5. `/loop-qa` skill rewrite (§0 deliverable 2)

Rewrite `.claude/skills/loop-qa/SKILL.md` so the gate is **mechanical**, not a hand-walked checklist. The new skill body MUST include all six of the following behaviors, expressed as the exact phrase OR a clear semantic equivalent (verification in §7 step 5 greps for these):

1. **Invokes the validator on a `content/` path.** Text includes `validate.py` (or `python3 tools/marketing-render/validate.py`) and references a `content/<slug>` input path.
2. **Reads and parses `qa-verdict.json`.** Text names `qa-verdict.json` (or `render/qa-verdict.json`) and states it is read/parsed after validation.
3. **Reports `failed_checks` and `needs_review`.** Text names `failed_checks` (reporting at least `id`, `detail`, `rule` per failure, formatted e.g. `<id> — <detail> (<rule>)`) and names `needs_review` as informational/non-blocking.
4. **FAIL is terminal and the gate never auto-fixes.** Text includes a statement equivalent to: "A FAIL verdict blocks publishing the asset. The validator reports violations; it does not fix them." Acceptable equivalents for the block claim: `blocks publish`, `blocks publishing`, `prevents publish`, `must not publish`, `do not publish`. Acceptable equivalents for the no-fix claim: `does not fix`, `no auto-fix`, `never edits`, `does not edit`.
5. **Render-only-when-absent behavior.** Text includes a statement equivalent to: "If `content/<slug>/render/manifest.json` does not exist, run `render.py content/<slug>` first; if it exists, use it as-is (do not silently overwrite)." Acceptable equivalents: `render only when`, `render first`, `render once`, `auto-render only when ... absent`.
6. **Exit-code mapping / rule citation only.** Text states that exit `0`=PASS, `1`=FAIL, `2`=precondition error (report the precondition error, not a verdict, on exit 2), and that every reported failure carries the validator-emitted `rule` string with no independent taste judgement added by the skill.

**Verification is content-based, and this is stated in the contract:** `/loop-qa/SKILL.md` is an LLM prompt, not executable code, so it cannot be unit-run. Its acceptance (§7 step 5) is a grep/read assertion over the six items above. No execution test is claimed for the skill; the mechanical gate it wraps (`validate.py`) is fully unit- and acceptance-tested.

## 6. `acceptance.py` — the end-to-end runner (§0 deliverable 3)

Interface: `python3 tools/marketing-render/acceptance.py [--checked-on YYYY-MM-DD] [--verbose]`.

**Date strategy (H-001, Option B — pin to sprint baseline).** Default `--checked-on 2026-07-04` — the **sprint baseline date**, chosen because the committed Sprint-004 fixture `qa-verdict.json` files already bake in `"checked_on": "2026-07-04"`. The runner passes this exact date to every `validate.py` invocation. Consequences, stated honestly:
- **PNG bytes are date-independent and are the actual R8 requirement** — re-rendering TGRERA yields a pixel-identical `chart-card.png` regardless of date; the runner asserts this hash equality (§6.1).
- **`qa-verdict.json` byte-identity with the committed fixtures holds only when `--checked-on 2026-07-04`.** Running with a different date changes only the JSON `checked_on` field, never the PNG. The runner therefore defaults to the baseline so its verdict JSON matches the committed fixtures; the contract does NOT claim JSON byte-identity for arbitrary dates.

### 6.1 Positive end-to-end (TGRERA) — also the R8 determinism proof
1. Record the SHA-256 of the committed `content/2026-07-03-tgrera-enforcement-wave/render/chart-card.png`.
2. Delete `content/2026-07-03-tgrera-enforcement-wave/render/` and **re-render** via `render.py`.
3. Assert the re-rendered `chart-card.png` SHA-256 **equals** the pre-delete hash (R8 pixel-identical determinism; leaves the PNG bytes clean).
4. Run `validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on <date>`; assert **exit 0** and `qa-verdict.json` `verdict:"PASS"`, `failed_checks:[]`.

### 6.2 Adversarial + robustness fixtures — each reaches its expected verdict on the RIGHT check with the RIGHT rule

**The runner MUST test all 12 committed fixtures.** For each fixture, run `validate.py <fixture> --checked-on <date>`, then assert:
- **exit code** equals the fixture's `expected_exit`, AND
- for a FAIL expectation (`expected_exit=1`), the parsed `qa-verdict.json` `failed_checks` **contains an entry whose `id` equals `expected_check_id` and whose `rule` contains `expected_rule_substring`** (not merely "some check failed" — the *named* check must fire), AND
- for the PASS expectation (`fx-good-min`, `expected_exit=0`), `verdict:"PASS"` and `failed_checks:[]`.

**Complete normative expectation table.** These `id` and `rule` strings are the exact strings `validate.py` already emits (read from the committed `qa-verdict.json` files during contract revision; the runner reads the real emitted strings at run time, it does not fabricate a second copy). All 12 rows are **mandatory** for acceptance — exit 0 is returned only when every row meets its expectation:

| fixture | expected_exit | expected_check_id | expected_rule_substring | tier |
|---|---|---|---|---|
| `fx-11-word-hook` | 1 | `V7-hook-words` | `qa-checklist.md §Carousel` | named-adversarial |
| `fx-truncated-axis` | 1 | `V10-chart-integrity` | `qa-checklist.md §Chart integrity` | named-adversarial |
| `fx-low-contrast` | 1 | `V4-contrast` | `brand-kit.md §3` | named-adversarial |
| `fx-missing-source` | 1 | `V8-source-stamp` | `qa-checklist.md §Chart integrity` | named-adversarial |
| `fx-blank-png` | 1 | `V3-ink` | `spec §5.2 V3` | named-adversarial (stub) |
| `fx-good-min` | 0 | (none) | (none) | positive control |
| `fx-size-lie` | 1 | `V5-crosscheck` | `spec §5.2 V5` | robustness |
| `fx-small-headline` | 1 | `V5-floor` | `qa-checklist.md §Typography` | robustness |
| `fx-out-of-safezone` | 1 | `V6-safezone` | `qa-checklist.md §Layout` | robustness |
| `fx-blacklist` | 1 | `V9-blacklist` | `brand-kit.md §8` | robustness |
| `fx-no-provenance` | 1 | `V11-provenance` | `qa-checklist.md §Data provenance` | robustness |
| `fx-canvas-mismatch` | 1 | `V2-canvas` | `qa-checklist.md §Layout` | robustness |

Notes on matching:
- **No wildcards.** Every `expected_check_id` is a literal, full check-id string. The runner asserts exact-`id` equality (not prefix/family matching).
- **`expected_rule_substring` is a substring test** on the emitted `rule` field (e.g. the emitted rule for `fx-low-contrast` is `brand-kit.md §3`, and `brand-kit.md §3` is a substring of it — an exact match here).
- If any committed fixture's real emitted `id`/`rule` were ever to differ from a row above, the contract's binding requirement is that **the runner's table uses the validator's actual emitted strings and the named check fires cited by its rule**; the builder MUST read the real emitted strings from the committed `qa-verdict.json` (which were already confirmed to match this table during revision) and MUST NOT hand-edit the table to a guess. The table above already reflects the confirmed emitted strings.

### 6.3 Output & exit
- **stdout:** a terse, mechanical, cite-the-rule summary — one line per row `PASS|FAIL <fixture> — exit <n>, <check-id> (<rule>) [expected …]`, then a final `ACCEPTANCE: PASS (<n>/<n> expectations met)` or `ACCEPTANCE: FAIL` naming the first unmet expectation. Tone per spec §7: no praise, no hedging.
- **Exit 0 iff** the TGRERA determinism hash matches AND TGRERA validates PASS AND every one of the 12 fixtures meets its expectation. **Any** mismatch → non-zero exit naming the failure. A green exit cannot be a false positive: a wrong-check FAIL, a PASS where FAIL was expected, or a determinism hash mismatch each flips the exit non-zero.

## 7. Acceptance — commands & expected results (Evaluator reproduces)

Preconditions: repo at S004 state (validator + 12 fixtures committed). No network needed or permitted. Use the sprint baseline date `2026-07-04` where a date is shown.

1. **Full unit suite** — `python3 -m unittest discover -s tools/marketing-render/tests -v` → OK, exit 0. S001–004 test counts unchanged (no regression); new `test_acceptance` tests present and green.
2. **End-to-end acceptance** — `python3 tools/marketing-render/acceptance.py --checked-on 2026-07-04` → **exit 0**; stdout ends `ACCEPTANCE: PASS`; shows TGRERA render+validate PASS and all 12 fixtures reaching their §6.2 expected verdict on the named check + rule.
3. **Determinism (R8) inside the run** — the acceptance run deletes and re-renders TGRERA and asserts the re-rendered `chart-card.png` is byte/pixel-identical to the committed one; after the run `git status --porcelain content/2026-07-03-tgrera-enforcement-wave/render/*.png` shows **no PNG byte change**. (The `qa-verdict.json` `checked_on` field is the only intended churn; pinned to `2026-07-04` it too is byte-identical to the committed fixture.)
4. **Adversarial discrimination is named, not vague** — for at least `fx-11-word-hook` (expect `V7-hook-words`) and `fx-blank-png` (expect `V3-ink`), open the fixture's `render/qa-verdict.json` and confirm the `failed_checks` entry id/rule the runner asserted actually appears there (the runner reads real validator output, not a hardcoded verdict).
5. **`/loop-qa` skill content** — read `.claude/skills/loop-qa/SKILL.md` and confirm all six §5 items are present (exact phrase or listed equivalent):
   - (a) references `validate.py` and a `content/<slug>` path;
   - (b) names `qa-verdict.json` and states it is read/parsed;
   - (c) names `failed_checks` (with id/detail/rule) and `needs_review` (informational);
   - (d) states a FAIL blocks publish AND the gate does not auto-fix (grep the §5.4 equivalents);
   - (e) states render-only-when-`render/`/`manifest.json`-absent (grep the §5.5 equivalents);
   - (f) states exit `0`/`1`/`2` mapping and rule-citation-only.
   (Content assertion; the skill is a prompt, not executable — §5.)
6. **README commands runnable as written** — copy each fenced command from the new README section (§4.1) and run it from the repo root:
   - `python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave` → writes `render/`, exit 0;
   - `python3 tools/marketing-render/validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on 2026-07-04` → exit 0 PASS;
   - `python3 tools/marketing-render/acceptance.py --checked-on 2026-07-04` → exit 0.
   No command references a non-existent slug or invented flag.
7. **Purity probe** — run the exact command in §8; exit 0, prints `PASS: no network imports`.
8. **Scope-boundary probe** — `render.py`, `validate.py`, `measure.py`, `make_fixtures.py`, and all prior `test_*.py` are byte-unchanged (`git diff` empty for those paths); no new `content/` adversarial folder was created; no file outside this repo touched.

## 8. Evaluator probes (Python/shell, since no browser)

- **Acceptance run:** `python3 tools/marketing-render/acceptance.py --checked-on 2026-07-04`; assert exit 0 and parse its stdout — confirm all 12 fixtures + the TGRERA rows appear with the §6.2 expected verdicts.
- **Tamper test 1 (gate is real, not a rubber stamp):** delete a fixture's `render/qa-verdict.json` before the run and confirm the runner regenerates it by re-invoking `validate.py` (rather than trusting a stale file or erroring on its absence). The runner never reads the committed verdict as trusted source.
- **Tamper test 2 (wrong-check rejection):** in a scratch copy, point one expectation-table row at the wrong check id (e.g. `fx-11-word-hook → V4-contrast`) and confirm the runner exits non-zero — "some FAIL" is not accepted, only the named FAIL. (Documented as a probe; do not commit the edit.)
- **Determinism probe:** run `acceptance.py --checked-on 2026-07-04` twice; `content/2026-07-03-tgrera-enforcement-wave/render/chart-card.png` SHA-256 identical both times; `git status --porcelain` clean of PNG changes.
- **Skill probe:** read `SKILL.md`; assert the six behaviors of §5 are present in the prose (per §7 step 5).
- **Purity probe (exact, runnable):**

```bash
python3 - <<'PY'
import ast, sys
path = "tools/marketing-render/acceptance.py"
with open(path) as f:
    tree = ast.parse(f.read())
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.add(alias.name.split('.')[0])
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            imports.add(node.module.split('.')[0])
network = {'socket', 'urllib', 'http', 'requests', 'ssl', 'httplib', 'ftplib'}
found = network & imports
if found:
    print(f"FAIL: network imports found: {sorted(found)}")
    sys.exit(1)
print("PASS: no network imports")
sys.exit(0)
PY
```

Exit 0 = PASS (no network imports), exit 1 = FAIL (network import detected).

## 9. States that must exist

- **Acceptance PASS:** TGRERA deterministic + PASS and all 12 fixtures meet expectations → `ACCEPTANCE: PASS`, exit 0.
- **Acceptance FAIL (regression caught):** any fixture stops reaching its expected check/exit, TGRERA stops passing, or the re-render hash drifts → `ACCEPTANCE: FAIL` naming the first unmet expectation, non-zero exit. (This is the runner's whole point — a regression gate for the toolchain.)
- **Missing precondition:** a referenced fixture folder or the TGRERA asset absent → the runner exits non-zero with a named path, not a traceback.
- **`/loop-qa` on a missing render:** the skill (per §5) auto-renders when `render/`/`manifest.json` is absent; on a missing `content/` folder or malformed manifest it surfaces the validator's exit-2 precondition error, not a verdict.
- **README command failure:** none — every documented command runs clean against the real TGRERA slug (§7 step 6).

## 10. Non-goals (restate, spec §8)

No new `content/` adversarial assets (§2.2). No render-through adversarial asset. No fixture regeneration in the gate. No source edits to `render.py`/`validate.py`/`measure.py`/`make_fixtures.py`/prior tests. No video/animation, no LinkedIn/PDF surface, no auto-fixing, no content generation, no font-family raster check. No network at any time. No CI/scheduler wiring beyond CLI-runnability + README. No changes outside this repo or to the live TERREM product.

## 11. Risks this sprint carries (disclosed)

- **R-A (S004-aspiration boundary):** the S004 contract aspired to real `content/` adversarial folders; the renderer's compliant-by-construction guards make four of five impossible, so this sprint uses the committed fixtures instead (§2.2, anchored to spec §1/§11's "fixtures" language). If the Evaluator holds the literal S004 aspiration over the spec's plain reading, §2.2 is the one place to contest — the contract argues the spec governs.
- **R-B (exact validator id/rule strings):** the §6.2 table's id/rule strings were read from the committed `qa-verdict.json` files during revision and confirmed exact. The runner reads the real emitted strings at run time; the builder MUST NOT substitute guesses.
- **R-C (skill is non-executable):** `/loop-qa` verification is content-based (§5); no execution test is claimed. Mitigation: the mechanical gate it wraps (`validate.py`) is fully unit- and acceptance-tested; the skill is a thin, asserted-in-prose wrapper.
- **R-D (determinism across environments):** R8 was proven on this machine's Pillow/font stack (S002/003). The acceptance re-render asserts byte-identity against the *committed* render on the same stack; a different Pillow build could shift bytes. Documented as an on-stack guarantee (fonts vendored, no network), matching prior sprints' determinism scope.
- **R-E (date staleness):** the baseline `--checked-on 2026-07-04` keeps `qa-verdict.json` byte-identical to the committed fixtures. PNG determinism (the R8 requirement) is date-independent. Running with a non-baseline date changes only the JSON `checked_on` field; the contract does not claim JSON byte-identity for arbitrary dates (H-001, Option B).
