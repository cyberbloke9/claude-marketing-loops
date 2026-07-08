# Contract — Sprint 001: Shared UTM module + verifier CLI

> Closes the §5.0 shared foundation (B-U1..B-U4) of `spec.md`. This is a **CLI /
> library** deliverable, not a web app — there are no routes, screens, or
> Playwright paths. Verification is exact CLI invocations + exit codes + stdout
> substrings, mirroring the DNA of `tools/marketing-render/` (`validate.py`,
> `acceptance.py`).

## 1. Scope (this sprint only)

Deliver the shared UTM foundation that BOTH later toolchains (Gap 2 publish,
Gap 3 analytics) will import:

- An importable Python module exposing the canonical channel↔source map and a
  `validate_asset()` function.
- A thin CLI that scans one asset folder OR all of `content/*/` and reports,
  per asset, `OK` or the specific, cited UTM violation.
- Unit tests + fixtures covering the valid path and every violation type.

Nothing else. Publish gate, queue, packages, captions, CSV ingestion,
scorecards, schedule slots, skills — all OUT of this sprint.

## 2. Files created / affected

Suggested layout (Generator may adjust names but MUST honor the behaviors and
the importable-module requirement):

- `tools/marketing-loops/__init__.py` — package marker (shared package both
  gaps import).
- `tools/marketing-loops/utm.py` — **importable module** (functions + the
  canonical `CHANNEL_SOURCE_MAP` dict). No CLI side effects on import.
- `tools/marketing-loops/verify_utm.py` — thin CLI wrapper importing `utm`.
- `tools/marketing-loops/tests/test_utm.py` — unit tests.
- `tools/marketing-loops/fixtures/<fx-name>/meta.md` — violation + positive
  fixtures. Fixtures are **asset folders under `tools/`, never under
  `content/`** (putting them in `content/` would pollute real content and make
  the real scan fail).

Read-only (do NOT modify): `content/*/meta.md`, `tools/marketing-render/*`.

## 3. Exact user-visible behaviors

### 3.1 The importable module (`utm.py`)

- Exports `CHANNEL_SOURCE_MAP` — the single canonical channel→`utm_source`
  dict, the seam BOTH toolchains MUST reuse (spec B-U3):
  | Channel | utm_source string |
  |---|---|
  | instagram | `instagram` |
  | youtube | `youtube` |
  | linkedin | `linkedin` |
  The allowed-source set is derived from this map's values (no second copy).
- Exports `parse_flywheel_line(meta_text) -> dict|None` (B-U1): finds the
  `Flywheel target:` line, extracts the URL's query string, returns a dict with
  `utm_source`, `utm_medium`, `utm_campaign` (missing keys → `None` values).
  Returns `None` distinctly when no `Flywheel target:` line exists at all.
- Exports `campaign_from_slug(folder_name) -> str` (B-U2 / A-1): strips a
  leading `^\d{4}-\d{2}-\d{2}-` date prefix from the folder name. If no date
  prefix, returns the folder name unchanged.
- Exports `validate_asset(asset_dir) -> result` (B-U2/B-U4): returns a
  structured result carrying `slug`, `ok: bool`, and an ordered list of
  `violations` (each an exact cited code + human message). Pure function; no
  writes, no `datetime.now()`, no network.

### 3.2 Validity rule (B-U2)

A Flywheel link is **valid** iff ALL hold:

1. A `Flywheel target:` line exists and its URL query string parses.
2. `utm_medium == "social"` (exact).
3. `utm_campaign == campaign_from_slug(folder_name)`.
4. `utm_source` is one of `CHANNEL_SOURCE_MAP` values
   (`instagram` / `youtube` / `linkedin`).

Only the **primary** URL on the `Flywheel target:` line is validated. A human
annotation continuation line such as `(per-channel: utm_source=youtube /
linkedin)` under it (present in the real hyd asset) is NOT parsed or validated
here — per-channel link generation is Sprint 003 (non-goal §7).

### 3.3 Violation taxonomy — exact cited codes

Each violation the tool reports uses one of these literal codes (the Evaluator
asserts on the exact string, mirroring `acceptance.py`'s right-check DNA):

| Code | Trigger |
|---|---|
| `missing-flywheel-line` | No `Flywheel target:` line in `meta.md` at all. |
| `malformed-query` | Line present but URL has no parseable query string (no `?`, or unparseable). |
| `wrong-medium` | `utm_medium` present but != `social` (includes absent `utm_medium` key). |
| `campaign-mismatch` | `utm_campaign` != date-stripped folder slug (includes absent key). |
| `unknown-source` | `utm_source` not in the allowed set (includes absent key). |

`missing-flywheel-line` and `malformed-query` are terminal for an asset (no
further value checks possible). When the query parses, value checks
(`wrong-medium`, `campaign-mismatch`, `unknown-source`) are evaluated
**independently**, so an asset with multiple value defects reports **all** of
them, in the fixed table order above (deterministic).

### 3.4 The CLI (`verify_utm.py`) — B-U4

- **Path argument:** positional `path`, optional, default `content`. The tool
  auto-detects:
  - If `path` is a single asset folder (contains a `meta.md`), scan just that
    asset.
  - Else treat `path` as a content-root and scan every immediate
    subdirectory that contains a `meta.md`, in **lexicographic slug order**.
  - This is what lets the Evaluator point the CLI at
    `tools/marketing-loops/fixtures/` (a root of fixture asset folders) OR at a
    single fixture folder, without touching `content/`.
- **Output:** stdout only, one stable line per asset:
  - `OK  <slug>` when valid.
  - `FAIL <slug>  <code>[, <code>...]  — <messages>` when flagged, codes in
    table order. Nothing is written to disk.
- **Exit codes** (matching `tools/marketing-render/validate.py` convention):
  - `0` — every scanned asset valid.
  - `1` — at least one asset flagged (domain failure); a full report still
    printed.
  - `2` — usage / precondition error: `path` does not exist, or a content-root
    with zero `meta.md`-bearing subdirs, or a single folder missing `meta.md`.
- No `datetime.now()` or any wall-clock anywhere in output. Deterministic:
  same inputs → byte-identical stdout.

## 4. States

- **Empty:** content-root with zero asset folders → exit `2` (precondition: a
  scan target with nothing to scan is a usage error, not a silent pass).
- **Success:** all assets valid → exit `0`, one `OK <slug>` line each. Both
  real assets (`2026-07-03-tgrera-enforcement-wave` AND the KILLED
  `2026-07-03-hyd-premium-vs-budget`) are positive controls — UTM validity is
  orthogonal to the publish gate, so BOTH must pass the scan.
- **Invalid input (domain):** any asset flagged → exit `1`, correct code(s)
  cited. Multiple flagged assets → all reported.
- **Precondition error:** path missing / no meta.md → exit `2`, message on
  stderr, nothing on stdout.
- **Offline:** no network; any network import is a defect.

## 5. Non-UI expectations (a11y/responsive/contrast do not apply)

This is a headless CLI. In place of keyboard/focus/ARIA/contrast/responsive:

- **Usability:** violation messages are specific and recoverable — each names
  the asset, the code, and what the operator must fix (e.g. `utm_medium was
  'paid', expected 'social'`), never a bare "invalid".
- **Runs from any cwd:** paths resolved from `__file__` (as `validate.py`
  does), so the tool works whether invoked from repo root or elsewhere.
- **Import safety:** importing `utm` has no side effects and prints nothing.

## 6. Security / privacy

- Stdlib only (`re`, `pathlib`, `argparse`, `urllib.parse` for query parsing —
  parsing only, no network fetch). No third-party deps. No network. No secrets.
  No file writes. CSV/meta inputs treated as untrusted text.

## 7. Explicit non-goals (this sprint)

- No publish gate / queue / packages / captions / schedule slots (Sprints
  002–003).
- No per-channel link generation; the `(per-channel: ...)` annotation line is
  not validated here.
- No `Channels:` free-text parsing or channel↔declared-source cross-check (A-7;
  Sprints 002–003). Validity is pure `utm_source` set-membership.
- No CSV ingestion / scorecard (Sprints 004–005).
- No skill files written or edited this sprint.
- No modification of `content/*` or `tools/marketing-render/*`.

## 8. Commands to run

```bash
cd /Users/prithviputta/Downloads/terrem-marketing-loops

# Unit tests (must pass)
python3 -m unittest discover -s tools/marketing-loops/tests -v

# Scan the real content root — both real assets are valid → exit 0
python3 tools/marketing-loops/verify_utm.py content ; echo "exit=$?"

# Scan a single real asset → exit 0
python3 tools/marketing-loops/verify_utm.py content/2026-07-03-tgrera-enforcement-wave ; echo "exit=$?"

# Scan the fixtures root (contains violation fixtures) → exit 1
python3 tools/marketing-loops/verify_utm.py tools/marketing-loops/fixtures ; echo "exit=$?"

# Precondition error: nonexistent path → exit 2
python3 tools/marketing-loops/verify_utm.py content/does-not-exist ; echo "exit=$?"

# Import-safety: importing the module prints nothing
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); import utm; print(sorted(utm.CHANNEL_SOURCE_MAP.items()))"
```

## 9. Evaluator attack checklist (CLI, not Playwright)

Point the CLI at fixtures the Generator ships under
`tools/marketing-loops/fixtures/`. Required fixtures + expected result:

| Fixture intent | Expected on scan |
|---|---|
| valid asset (positive control) | `OK`, contributes exit 0 |
| missing `Flywheel target:` line | `missing-flywheel-line`, exit 1 |
| line present, no `?query` | `malformed-query`, exit 1 |
| `utm_medium=paid` (wrong) | `wrong-medium`, exit 1 |
| `utm_campaign` != date-stripped slug | `campaign-mismatch`, exit 1 |
| `utm_source=tiktok` (unknown) | `unknown-source`, exit 1 |
| absent `utm_source` key | `unknown-source`, exit 1 |
| multiple defects (wrong medium + unknown source) | both codes in table order, exit 1 |

Adversarial probes the Evaluator should run:

1. Scan real `content/` → exit 0; both real slugs print `OK` (incl. KILLED hyd
   asset — KILLED does not affect UTM validity).
2. Scan a single valid asset folder directly → exit 0.
3. Scan fixtures root → exit 1; assert each expected code appears on the right
   slug (exact-string match, not "some FAIL").
4. Nonexistent path and a `meta.md`-less folder → exit 2, stderr message, empty
   stdout.
5. Determinism: run the fixtures scan twice → byte-identical stdout.
6. Import `utm` → no stdout, `CHANNEL_SOURCE_MAP` has exactly the three
   channels.
7. Grep the source for `datetime.now`, `requests`, network `urllib` fetch →
   none present.

## 10. Definition of done

- `utm.py` importable with `CHANNEL_SOURCE_MAP` + `validate_asset()`, no import
  side effects.
- `verify_utm.py` implements the path-arg auto-detect, the violation taxonomy
  with exact codes, and exit codes 0/1/2.
- Fixtures for every row in §9 shipped under `tools/marketing-loops/fixtures/`.
- Unit tests prove each violation code fires on its fixture and `OK` on the
  valid one; all pass.
- Real `content/` scan exits 0.
- Evidence (command output, exit codes) logged in `generator_trace.log`.
