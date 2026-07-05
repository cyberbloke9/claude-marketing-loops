# Contract — Sprint 004: Analytics CSV ingestion (robust) → validated INGEST structure

> Opens Gap 3 (spec §5.2). Delivers the **ingestion half** of the analytics
> toolchain: the four documented **CSV column contracts** (B-A1), the **join key**
> that ties a CSV metrics row to an asset + its hook number (B-A2), the
> **malformed/truncated rejection path** (B-A3), and the **absent-input handling**
> foundation (B-A4) — all producing a single **validated intermediate metrics
> structure** (the INGEST schema) that Sprint 005's scorecard compiler consumes.
>
> **This sprint produces NO scorecard markdown, computes NO WRR sum, and writes NO
> `metrics/*.md`.** Those are Sprint 005 (§11). Sprint 004 stops at the validated
> INGEST structure. It reuses the frozen Sprint-001 `utm` module (imported, not
> modified) for the join key and per-asset UTM validity.
>
> This is a **CLI + importable pure library** deliverable — no routes, screens, or
> Playwright paths. Verification is exact CLI invocations + exit codes +
> stdout/stderr substrings + on-disk/stdout JSON assertions, mirroring the DNA of
> `tools/marketing-render/` and the PASSED Sprints 001/002/003.

## 1. Scope (this sprint only)

Deliver the CSV ingestion layer of the Gap-3 analytics toolchain:

- **Four documented CSV column contracts** (§3.1, spec §5.4 CSV-INPUTS): Instagram
  export, YouTube export, LinkedIn export, site-analytics export. Each names its
  required headers, its join column, and which columns feed which downstream
  scorecard cell (craft diagnostics, flywheel clicks, the three WRR components).
  These are an **authored internal contract** (Assumption A-5) — fixtures conform;
  no attempt is made to reproduce any real platform's export layout.
- A **robust CSV parser** (`csvspec.py`) that validates a provided CSV against its
  contract and **rejects** (exit 2, cited file + reason, no downstream output) on:
  unparseable content, a missing required header, a data row with the wrong column
  count, a truncated/unterminated row, or a **non-blank non-numeric** value in a
  numeric column (B-A3 / story #7 "corruption never silently becomes a blank
  cell"). A **blank** cell in a numeric column is **absent**, not corrupt (B-A4).
- An **asset resolver** (`assetmap.py`) that scans `content/*/meta.md`, builds the
  `campaign → (slug, hook_number, utm_valid, utm_violations)` map via the frozen
  Sprint-001 `utm` module, and exposes the join key (B-A2 / B-A11 material).
- An **ingestion builder + CLI** (`ingest.py`) that reads whichever of the four
  CSVs the operator provides, joins metrics rows to assets, aggregates flywheel
  clicks and the three WRR component inputs, tracks every **absence** (source not
  provided / value blank / component missing / campaign-with-no-asset / wrong-UTM
  asset), and emits the **INGEST** JSON structure (§3.5). Provided-but-corrupt CSV
  → exit 2, no output; absent source → recorded as missing, exit 0.
- Unit tests + fixtures covering every path in §9.

**Explicitly OUT of this sprint** (Sprint 005): the scorecard markdown, the WRR
sum + no-partial-sum blanking decision, the Missing-data section text, the
posting-time A/B table, the Decisions-fed-back section, `metrics/YYYY-Www.md`
output, and the `loop-measure` SKILL update. Sprint 004 exposes the raw inputs +
presence flags that Sprint 005 turns into those cells. See §7.

## 2. Files created / affected

New, under `tools/marketing-loops/` (Generator may adjust private helper names but
MUST honor the behaviors, the importable-pure-function requirement, and the
fixtures-live-under-`tools/` rule):

- `csvspec.py` — **importable pure module**: the four column contracts as data +
  `read_csv(path, contract)` returning validated typed rows or raising a cited
  `CsvError`. No CLI side effects on import. No wall-clock, no network.
- `assetmap.py` — **importable pure module**: scan a content dir, return the
  `campaign → asset-record` map (slug, hook_number, utm_valid, utm_violations).
  Imports the frozen Sprint-001 `utm`. No writes, no wall-clock, no network.
- `ingest.py` — the ingestion CLI + its pure builder function `build_ingest(...)`.
  Imports `csvspec`, `assetmap`, `utm`. Parses args, validates CSVs, builds the
  INGEST structure, emits JSON (stdout or `--out`), maps errors → exit codes.
- `tests/test_csvspec.py`, `tests/test_assetmap.py`, `tests/test_ingest.py` — unit
  tests.
- `fixtures/metrics/<fx-name>/` — new ingestion fixtures (CSV files + small content
  dirs of `meta.md`-only asset folders as needed), listed in §9. Fixtures live
  **under `tools/`, never under `content/`**.

**Read-only — imported, NOT modified** (Sprint-001/002/003 contracts are frozen and
PASSED): `utm.py`, `gate.py`, `queue.py`, `channels.py`, `captions.py`,
`schedule.py`, `package.py`, `mark_posted.py`, and all of `content/*`. New shared
logic lives in the **new** modules and only *imports* `utm.py` — no function is
added to any frozen module, so no PASSED contract can regress.

**No new tracked disk artifact is introduced.** `ingest.py` prints the INGEST JSON
to stdout by default; `--out PATH` writes it for inspection. Sprint 005 imports
`build_ingest(...)` directly. Tests read fixture CSVs and write only to temp paths.

## 3. Exact behaviors

### 3.1 The four CSV column contracts (`csvspec.py`) — B-A1 / spec §5.4 CSV-INPUTS

Each contract is a documented, versioned data structure declared once in
`csvspec.py`, exactly like `manifest.json`/`qa-verdict.json` are versioned schemas.
A `CSV_SCHEMA_VERSION = "1"` constant lives once. Column contract fields: the
ordered **required headers**, each header's **type** (`str` | `int` | `num`), and
the **join column**. Extra columns beyond the required set are **ignored** (not an
error). Header match is exact and case-sensitive.

**Platform exports — Instagram / YouTube / LinkedIn** (one row per published
asset×channel; the craft-diagnostics source B-A7 + the `returning_viewers` note
below). Required headers, in order:

| Header | Type | Feeds |
|---|---|---|
| `utm_campaign` | str | **join key** (B-A2) → asset slug + hook # |
| `three_s_hold_pct` | num | Craft: 3s-hold % |
| `completion_pct` | num | Craft: completion / swipe-through % |
| `shares` | int | Craft: Shares |
| `clicks` | int | Craft: Clicks |

The three platform contracts are structurally identical; the **kind** (`instagram`
/ `youtube` / `linkedin`) is supplied by which `--instagram/--youtube/--linkedin`
flag the file arrives on, and fixes the row's `channel`. (A platform CSV does NOT
carry a channel column; the flag is the channel.)

**Site-analytics export** (per-campaign rows; the flywheel source B-A6 + the sole
home of the three WRR component inputs — A-5/A-6 authored contract). Required
headers, in order:

| Header | Type | Feeds |
|---|---|---|
| `utm_source` | str | filter (informational) |
| `utm_medium` | str | filter: only `social` rows count for flywheel + WRR comp3 |
| `utm_campaign` | str | **join key** → flywheel grouping (B-A6) |
| `clicks` | int | Flywheel: clicks to intel.terrem.in by campaign (B-A6) |
| `returning_viewers` | int | **WRR component 1** (returning viewers) |
| `digest_opens` | int | **WRR component 2** (digest/email open-streak) |
| `returning_visitors_social` | int | **WRR component 3** (returning site visitors from social) |

> **Why all three WRR components live in site-analytics (A-5/A-6, documented):**
> WRR is a single week-level rollup, not a per-asset metric. Housing its three
> component columns in the one week/site-level export keeps WRR single-source
> (no "which platform sources were provided" ambiguity) and makes the Sprint-005
> B-A5 "any component absent → blank WRR" edge testable at the value level (blank
> a column → that component absent). This is the manifest.json approach applied to
> inputs; it is an authored internal contract, not a claim about a real export.

**Numeric typing (`int` / `num`) — the B-A3 vs B-A4 crux, pinned:**

- A **blank** cell (`""` after strip) in an `int`/`num` column → the value is
  **absent** (`None`), NOT corrupt, NOT zero. This is B-A4 (Sprint 005 blanks it +
  lists it under Missing data). Exit stays 0.
- A **non-blank** cell in an `int` column must parse as a base-10 integer
  (`^-?\d+$`); in a `num` column as an integer or decimal (`^-?\d+(\.\d+)?$`).
  Any **non-blank value that fails to parse** (e.g. `abc`, `12x`, `1,2`) → **corrupt
  → reject** (exit 2, cite file + 1-based data-row number + column name). This is
  B-A3 / story #7: corruption never silently becomes a blank cell.
- `0` (and `0.0`) is a **present value**, distinct from absent. Absent must never
  be defaulted to `0` (B-A7 "blank cell, not zero"). The blank-vs-non-blank test
  above enforces this; no code path converts absent → 0.
- `str`-typed cells are taken verbatim (leading/trailing whitespace stripped for
  the join column `utm_campaign` and for `utm_medium`); a blank `utm_campaign` in a
  data row → reject (a row that cannot join is corrupt for the join column), cited.

### 3.2 Robust parse + rejection (`csvspec.read_csv`) — B-A3

`read_csv(path, contract)` reads a provided CSV with the stdlib `csv` module and
returns a list of validated row dicts `{header: typed_value_or_None}` — OR raises
`CsvError(message)` (the CLI turns it into exit 2). Rejection conditions, each with
a specific cited message naming the file and (where applicable) the row/column:

1. **Unparseable / unterminated:** the `csv` reader raises `csv.Error` (e.g. an
   unterminated quoted field, a NUL byte) → reject: `"<file>: not parseable as CSV
   (<detail>)"`.
2. **No header / empty file:** zero lines, or a header row that is empty → reject:
   `"<file>: missing required header(s): <list>"` (an empty file is missing every
   required header).
3. **Missing required header:** any contract-required header absent from the header
   row → reject, naming the missing header(s). (Extra headers are ignored.)
4. **Wrong column count:** any **data** row whose field count ≠ the header field
   count → reject: `"<file>: row <n> has <k> columns, expected <h>"`. A file
   truncated mid-row yields a short final row → caught here (or by (1) if a quote is
   left open). `<n>` is the 1-based data-row index (header is not counted).
5. **Non-numeric in a numeric column / blank join column:** per §3.1 typing →
   reject, cited with file + data-row number + column name.

**A provided CSV with a valid header and ZERO data rows is NOT malformed** — it is
a valid, *present* source that contributes no values (every downstream cell drawn
from it is absent → Sprint-005 blanks + lists). This is the sharp line between
"present-but-empty" (exit 0) and "corrupt" (exit 2).

`read_csv` performs **no** wall-clock, **no** network, and **no** writes. It reads
`path` with `encoding="utf-8"`; a decode error → `CsvError` (reject, exit 2).

### 3.3 Asset resolver + join key (`assetmap.py`) — B-A2 / B-A11

`build_asset_map(content_dir) -> {campaign: asset_record}` scans every immediate
subdirectory of `content_dir` that contains a `meta.md` (skipping `TEMPLATE.md` and
non-asset entries), and for each builds an **asset record**:

```
{
  "slug": "<folder name, date prefix intact>",
  "campaign": "<utm.campaign_from_slug(slug)>",   # the join key (B-A2)
  "hook_number": <int|null>,                       # first #<n> on the Hook: line
  "utm_valid": <bool>,                             # utm.validate_asset(...).ok
  "utm_violations": [<code>, ...],                 # Sprint-001 violation codes
}
```

- **Join key (B-A2):** `campaign = utm.campaign_from_slug(slug)` (date-stripped
  slug) — the identical key CSV rows join on. Two assets mapping to the same
  campaign → raise `ValueError` (an authoring collision the operator must fix;
  surfaced, never silently coalesced).
- **Hook number:** the first `#\d+` token on the `Hook:` line of `meta.md`
  (`Hook: hook-bank #11 …` → `11`; `… #13 … #21` → `13`). No `Hook:` line, or no
  `#\d+` on it → `hook_number = null` (Sprint 005 leaves the Hook # cell blank; the
  tool never invents a hook number).
- **UTM validity (B-A11 material):** `utm.validate_asset(asset_dir)` — a wrong-UTM
  asset is recorded (`utm_valid=false`, `utm_violations=[...]`) so Sprint 005 can
  flag it in Missing-data/notes and never silently attribute metrics to it. This
  sprint records the flag; Sprint 005 renders it.
- Pure: no writes, no wall-clock, no network. An asset folder missing `meta.md` is
  skipped (not an error). Result campaigns are unique keys; iteration order is
  irrelevant (the INGEST builder sorts).

### 3.4 Ingestion builder + CLI (`ingest.py`) — B-A2 / B-A4 / B-A6 (aggregation only)

CLI:

```
python3 tools/marketing-loops/ingest.py --week YYYY-Www \
  [--instagram FILE] [--youtube FILE] [--linkedin FILE] [--site FILE] \
  [--content-dir DIR] [--out FILE]
```

Ordered steps (all validation before any output; on any error nothing is written
and stdout is empty):

1. **`--week` format** `^\d{4}-W\d{2}$` → else exit 2 (cited).
2. **At least one of** `--instagram/--youtube/--linkedin/--site` **or** none: **none
   provided is allowed** (the empty state — a valid all-absent INGEST, exit 0).
3. **Provided path existence:** any `--<source> FILE` whose path does not exist / is
   not a file → exit 2 (`"<flag> file not found: <path>"`). *Absent flag ≠ bad
   path:* omitting a flag records the source as not-provided (exit 0); passing a
   flag to a nonexistent file is a usage error (exit 2). These are two distinct
   states.
4. **`--content-dir`** (default: repo `content/`, resolved from `__file__`) must be
   an existing directory → else exit 2. Build the asset map (§3.3); a campaign
   collision → exit 2 (cited).
5. **Parse each provided CSV** via `csvspec.read_csv` with its contract (§3.1–3.2).
   Any `CsvError` → **exit 2**, print the cited message to **stderr**, emit **no**
   JSON (B-A3: no downstream output on corrupt input).
6. **Join + aggregate** (pure `build_ingest(...)`), all from present values only —
   no estimation, interpolation, or defaulting (spec §5.2, §7 anti-patterns):
   - **Craft rows (B-A7):** for each row of each provided platform CSV, one craft
     entry keyed `(campaign, channel)`; resolve `slug` + `hook_number` via the
     asset map (unmatched campaign → `slug=null`, `hook_number=null`, and record an
     `unmatched-campaign` absence). Blank metric cell → `null` (absent), never `0`.
   - **Flywheel clicks (B-A6):** from the site CSV, rows with `utm_medium=="social"`
     grouped by `utm_campaign`, summing `clicks` over **present (non-blank)** cells.
     A campaign whose `clicks` cells are all blank → click total absent for it.
   - **WRR component inputs:** from the site CSV, for each of the three component
     columns, the column-sum over present cells (comp3 filtered to
     `utm_medium=="social"`). Each component: `{"present": bool, "value": int|null,
     "source": "site"}` — `present=true` iff the site source is provided AND that
     column has ≥1 non-blank cell; else `value=null, present=false`. **This sprint
     does NOT sum the three into WRR and does NOT decide the blank-WRR rule** — that
     is Sprint 005's B-A5. It only exposes the three component inputs + presence.
7. **Record absences** (the raw material for Sprint 005's Missing-data section):
   an ordered, de-duplicated list of `{kind, detail}` entries with `kind ∈
   {source, wrr-component, unmatched-campaign, wrong-utm}` (value-level blanks are
   representable by the `null` cells themselves + the `sources_provided` map; the
   absences list captures the higher-level items). Ordering is deterministic
   (by `kind`, then `detail`).
8. **Emit INGEST JSON** (§3.5) to stdout, or to `--out FILE` if given (the file is
   the only optional write; `mkdir -p` its parent). `json.dumps(..., sort_keys=True,
   indent=2) + "\n"`. Exit **0**.

**Determinism (spec §7):** same inputs → byte-identical INGEST JSON. Sorted keys;
craft entries ordered by `(campaign, channel)`; flywheel entries by `campaign`
(lexicographic); assets by `slug`; absences by `(kind, detail)`. No `datetime.now()`
anywhere; the only date-ish input is the operator-supplied `--week` (validated as a
string, never parsed against "now"). No network.

### 3.5 INGEST schema (spec §5.4 "intermediate metrics blob") — the seam Sprint 005 consumes

Serialized `json.dumps(..., sort_keys=True, indent=2) + "\n"`:

```json
{
  "schema_version": "1",
  "week": "YYYY-Www",
  "sources_provided": {
    "instagram": false, "youtube": false, "linkedin": false, "site": false
  },
  "assets": [
    { "slug": "2026-07-03-tgrera-enforcement-wave",
      "campaign": "tgrera-enforcement-wave",
      "hook_number": 11, "utm_valid": true, "utm_violations": [] }
  ],
  "wrr_components": {
    "returning_viewers":        { "present": false, "value": null, "source": "site" },
    "digest_opens":             { "present": false, "value": null, "source": "site" },
    "returning_visitors_social":{ "present": false, "value": null, "source": "site" }
  },
  "flywheel_clicks_by_campaign": [
    { "campaign": "tgrera-enforcement-wave", "clicks": 42 }
  ],
  "craft": [
    { "campaign": "tgrera-enforcement-wave", "channel": "instagram",
      "slug": "2026-07-03-tgrera-enforcement-wave", "hook_number": 11,
      "three_s_hold_pct": 31.0, "completion_pct": 26.0,
      "shares": 4, "clicks": 33 }
  ],
  "absences": [
    { "kind": "source", "detail": "youtube export not provided" }
  ]
}
```

- `schema_version` is `"1"`, declared once in `ingest.py`.
- Absent numeric cells are JSON `null`; present ones are numbers. `0` is `0`, never
  conflated with `null`.
- `craft[].slug` / `hook_number` are `null` for an unmatched campaign.
- The structure is **complete for an all-absent run**: `sources_provided` all
  `false`, `assets` populated from the content scan, `wrr_components` all
  `present:false`, `flywheel_clicks_by_campaign: []`, `craft: []`, and an `absences`
  list naming each not-provided source. This is the empty state (exit 0).

### 3.6 Exit codes (match render / Sprint 001–003 convention)

- **`0`** — success, including a **partial** run (some sources absent → mix of
  present values + `null` cells) and the **empty** run (no sources → all-absent
  INGEST). A valid partial/empty INGEST is a success, not an error (spec §6
  "Partial input … exit 0").
- **`1`** — **intentionally unused** by this tool. Ingestion has no "domain verdict
  on well-formed input" outcome analogous to a gate FAIL: a corrupt CSV is
  *malformed input* (→ 2, matching Sprint-003's malformed-`manifest.json` → 2 and
  render's malformed-input → 2), and unmatched-campaign / wrong-UTM are **flags**
  (B-A11), not rejections. Documented so the Sprint-006 acceptance runner sees a
  consistent taxonomy across both gaps.
- **`2`** — **usage / precondition error**, message on **stderr**, **no** JSON on
  stdout, **no** `--out` write: malformed `--week`; a provided `--<source>` path
  that does not exist; a bad `--content-dir`; an asset-map campaign collision; and
  **every B-A3 CSV rejection** (unparseable, missing header, wrong column count,
  truncated row, non-numeric numeric cell, blank join column).

## 4. States

- **Empty (no sources):** `--week` only → valid all-absent INGEST (§3.5 note),
  exit 0, one `absences` entry per not-provided source.
- **Empty (present-but-header-only):** a provided CSV with header + zero data rows →
  present source, no values, exit 0 (distinct from corrupt).
- **Success (full):** all four sources provided, well-formed → craft rows joined,
  flywheel grouped, three WRR components present with summed values, exit 0.
- **Partial input:** some sources provided → mix of present values + `null` cells +
  `sources_provided` false for the missing → exit 0 (never an error).
- **Absent source vs bad path:** omitting `--youtube` → recorded missing, exit 0;
  `--youtube /no/such.csv` → exit 2 (`file not found`). Two distinct states.
- **Corrupt CSV (B-A3):** unparseable / missing header / wrong column count /
  truncated / non-numeric numeric cell / blank join column → exit 2, cited
  file+row+column, **no JSON emitted, no `--out` write**.
- **Unmatched campaign (B-A11):** a CSV `utm_campaign` matching no content asset →
  craft/flywheel entry retained with `slug=null`, an `unmatched-campaign` absence
  recorded, exit 0 (a flag, not a rejection).
- **Wrong-UTM asset (B-A11):** an asset whose `meta.md` UTM link is scheme-invalid →
  `utm_valid=false` + `utm_violations` recorded in `assets[]` and a `wrong-utm`
  absence entry, exit 0 (Sprint 005 renders the flag).
- **Idempotency / determinism:** same inputs → byte-identical INGEST JSON, stable
  ordering, no wall-clock.
- **Offline:** no network; any network import is a defect.

## 5. Non-UI expectations (a11y / responsive / contrast do not apply)

Headless CLI + importable library. In place of keyboard/focus/ARIA/contrast/
responsive:

- **Usability:** every rejection message is specific and recoverable — it names the
  file, the 1-based data-row number, and/or the column (e.g. `fixtures/…/ig.csv:
  row 3 column 'shares': non-blank value 'x' is not an integer`; `site.csv: missing
  required header(s): digest_opens`), never a bare "invalid CSV".
- **Runs from any cwd:** paths resolved from `__file__`; `--content-dir` and every
  `--<source>` accept absolute or relative paths; default `--content-dir` is the
  repo `content/`.
- **Import safety:** importing `csvspec`, `assetmap`, `ingest` has no side effects
  and prints nothing.
- **Single source of truth:** the join key + per-asset UTM validity come from the
  frozen Sprint-001 `utm` module (`campaign_from_slug`, `validate_asset`); no forked
  channel map, no re-declared campaign-stripping regex.

## 6. Security / privacy

- Stdlib only: `csv`, `json`, `argparse`, `pathlib`, `re`. **No** `datetime` use for
  "now" (no date parsing is even required here — `--week` is validated as a string).
  No third-party deps. No network. No secrets. No personal data written. CSV inputs
  are **untrusted**: parsed defensively; every malformation is a cited exit-2 error,
  never a crash and never an invented/defaulted value. No dependency on the
  globally-installed `pmp-gywd@5.0.0` npm package.
- `ingest.py` writes nothing by default (JSON to stdout); `--out` writes only where
  the operator points it. Tests read fixtures under `tools/` and write only to temp
  paths; no real `content/` or `metrics/` file is mutated.

## 7. Explicit non-goals (this sprint)

- **No scorecard markdown, no `metrics/YYYY-Www.md`** — Sprint 005.
- **No WRR sum, no no-partial-sum blanking decision, no Missing-data section text,
  no posting-time A/B table, no Decisions-fed-back section** — Sprint 005 (B-A5,
  B-A8, B-A9, B-A10). Sprint 004 exposes the raw component inputs + presence + the
  absences list only.
- **No `loop-measure` SKILL update** — Sprint 005 (B-A12).
- **No modification** of any Sprint-001/002/003 module or any `content/*` file.
- **No estimation, interpolation, defaulting, or zero-filling** of any absent
  metric — absent stays `null`; `0` is only ever a genuinely present `0`.
- **No live posting APIs, no network, no scraping** — inputs are operator-provided
  CSV files only.

## 8. Commands to run

```bash
cd /Users/prithviputta/Downloads/terrem-marketing-loops
FX=tools/marketing-loops/fixtures/metrics

# Unit tests (all Sprint 001+002+003+004 must pass)
python3 -m unittest discover -s tools/marketing-loops/tests -v

# Full happy path: 4 well-formed sources -> exit 0, INGEST JSON with craft rows,
# flywheel grouping, three present WRR components
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --instagram "$FX/full/ig.csv" --youtube "$FX/full/yt.csv" \
  --linkedin "$FX/full/li.csv" --site "$FX/full/site.csv" \
  --content-dir "$FX/full/content" ; echo "exit=$?"

# Empty state: no sources -> valid all-absent INGEST, exit 0
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --content-dir "$FX/full/content" ; echo "exit=$?"

# Partial: only IG provided -> mix of present + null, exit 0
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --instagram "$FX/full/ig.csv" --content-dir "$FX/full/content" ; echo "exit=$?"

# Determinism: same inputs -> byte-identical stdout
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --site "$FX/full/site.csv" --content-dir "$FX/full/content" | shasum
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --site "$FX/full/site.csv" --content-dir "$FX/full/content" | shasum

# B-A3 rejections (each exit 2, cited, NO json on stdout):
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --site "$FX/truncated/site.csv" --content-dir "$FX/full/content" ; echo "exit=$?"
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --site "$FX/wrong-header/site.csv" --content-dir "$FX/full/content" ; echo "exit=$?"
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --instagram "$FX/wrong-colcount/ig.csv" --content-dir "$FX/full/content" ; echo "exit=$?"
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --instagram "$FX/non-numeric/ig.csv" --content-dir "$FX/full/content" ; echo "exit=$?"

# Absent source vs bad path:
python3 tools/marketing-loops/ingest.py --week 2026-W27 \
  --youtube /no/such/file.csv --content-dir "$FX/full/content" ; echo "exit=$? (expect 2)"

# Bad --week
python3 tools/marketing-loops/ingest.py --week 2026-27 \
  --content-dir "$FX/full/content" ; echo "exit=$? (expect 2)"

# Import-safety
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); \
  import csvspec, assetmap, ingest; print('ok')"

# No wall-clock / no network in new sources
grep -nE "datetime\.now|requests|urlopen|socket|urllib" \
  tools/marketing-loops/csvspec.py tools/marketing-loops/assetmap.py \
  tools/marketing-loops/ingest.py || echo "clean"
```

## 9. Evaluator attack checklist (CLI, not Playwright)

Fixtures shipped under `tools/marketing-loops/fixtures/metrics/` (CSV files + tiny
`meta.md`-only content dirs). Required NEW fixtures + expected result:

| Fixture intent | Expected |
|---|---|
| `full/` — 4 well-formed CSVs + a content dir with ≥2 assets (incl. tgrera-style, hook #11) | exit 0; craft rows joined w/ slug+hook#; flywheel grouped; 3 WRR components present w/ summed values |
| `full` **present-but-header-only** variant (a CSV with header, 0 data rows) | exit 0; that source present, its values absent (`null`) |
| `truncated/site.csv` — file cut mid-row (unterminated / short last row) | exit 2, cited file + row, **no JSON on stdout** |
| `wrong-header/site.csv` — a required header renamed/removed (`digest_opens` gone) | exit 2, names the missing header, no JSON |
| `wrong-colcount/ig.csv` — one data row with an extra/missing field | exit 2, `row <n> has <k> columns, expected <h>`, no JSON |
| `non-numeric/ig.csv` — `shares` cell `x` (non-blank, unparseable) | exit 2, cites row+column, no JSON (corruption ≠ blank) |
| `blank-cell/ig.csv` — a `clicks` cell left `""` | exit 0; that craft cell is `null` (absent), **not 0** |
| `zero-cell/ig.csv` — a `clicks` cell `0` | exit 0; that craft cell is `0` (present), **not null** |
| `unmatched/ig.csv` — a `utm_campaign` with no matching content asset | exit 0; craft entry `slug=null`, an `unmatched-campaign` absence recorded |
| `wrong-utm/content/` — an asset whose `meta.md` UTM link is scheme-invalid | exit 0; that asset `utm_valid=false`+violations, a `wrong-utm` absence |
| `blank-join/site.csv` — a data row with blank `utm_campaign` | exit 2 (row cannot join), cited, no JSON |
| `empty` (no `--source` flags) | exit 0; all-absent INGEST, one absence per not-provided source |

Adversarial probes the Evaluator should run:

1. **Full happy path** → exit 0; assert INGEST has `schema_version "1"`, correct
   `sources_provided`, craft rows with the RIGHT `slug`/`hook_number` per join,
   flywheel grouped by campaign with summed clicks, all three `wrr_components`
   `present:true` with the expected sums.
2. **Determinism** → run twice → `shasum` byte-identical stdout; ordering stable
   (craft by `(campaign, channel)`, flywheel by campaign, assets by slug, absences
   by `(kind, detail)`).
3. **B-A3 corruption suite** → `truncated`, `wrong-header`, `wrong-colcount`,
   `non-numeric`, `blank-join` → **each** exit 2, a cited message (file + row +
   column where applicable), and **empty stdout** (no partial JSON). Confirm no
   `--out` file is created when `--out` is passed alongside a corrupt input.
4. **B-A4 blank-vs-zero** → `blank-cell` → the cell is JSON `null`; `zero-cell` →
   the cell is `0`. The two are never conflated. No absent value is defaulted to 0.
5. **Absent source vs bad path** → omit `--youtube` → exit 0, `sources_provided.
   youtube=false`, a `source` absence; `--youtube /no/such.csv` → exit 2 `file not
   found`. Two distinct states.
6. **Partial + empty** → IG-only run → exit 0, mix of present + null; no-source run
   → exit 0, all-absent INGEST with the §3.5 shape.
7. **Join correctness** → craft rows resolve `slug` + `hook_number` from `meta.md`
   (tgrera → 11; a fixture asset → its own #); `unmatched` campaign → `slug=null`,
   `hook_number=null`, absence recorded.
8. **WRR component presence** → all three present when site provided with values;
   blank one component's column → that component `present:false, value:null`, the
   other two still present (value-level edge for Sprint-005 B-A5). Confirm Sprint
   004 does **not** emit a summed WRR anywhere.
9. **Wrong-UTM flagging (B-A11)** → `wrong-utm` asset → `utm_valid=false`,
   `utm_violations` = the exact Sprint-001 codes, `wrong-utm` absence; exit 0
   (flagged, not rejected).
10. **Bad `--week`** (`2026-27`, `26-W27`, `2026-W5`) → exit 2, no JSON.
11. **Import safety + no wall-clock/no network** → `import csvspec, assetmap,
    ingest` prints nothing; grep the three new sources → no `datetime.now`,
    `requests`, `urlopen`, `socket`, or network `urllib` (none permitted; the tool
    needs none).
12. **Frozen modules untouched** → diff shows `utm.py`, `gate.py`, `queue.py`,
    `channels.py`, `captions.py`, `schedule.py`, `package.py`, `mark_posted.py`
    unchanged; the full Sprint 001+002+003 unit suite still passes.

## 10. Definition of done

- `csvspec.py` declares the four versioned column contracts + a pure
  `read_csv(path, contract)` that returns typed rows or raises a cited `CsvError`,
  rejecting unparseable/missing-header/wrong-column-count/truncated/non-numeric/
  blank-join inputs and treating a blank numeric cell as absent (`None`), never 0 —
  with no import side effects, no wall-clock, no network.
- `assetmap.py` scans a content dir and returns `campaign → asset-record` (slug,
  hook_number, utm_valid, utm_violations) via the frozen Sprint-001 `utm`; hook # is
  the first `#\d+` on the Hook line or `null`; a campaign collision raises; pure.
- `ingest.py` validates args + CSVs (corrupt → exit 2, no output), joins metrics to
  assets, aggregates flywheel clicks + the three WRR component inputs from present
  values only, records every absence, and emits a deterministic INGEST JSON (§3.5)
  on stdout or `--out`; partial and empty runs are exit-0 successes; exit 1 is
  intentionally unused; no WRR sum and no scorecard are produced.
- Fixtures for every §9 row shipped under `tools/marketing-loops/fixtures/metrics/`.
- Unit tests prove the four contracts' parsing, every rejection path, blank-vs-zero,
  the join + hook resolution, unmatched-campaign + wrong-UTM flagging, WRR component
  presence, determinism, and import safety; all pass alongside the untouched
  Sprint 001+002+003 suites.
- Evidence (command output, exit codes, sample INGEST JSON, before/after `shasum`,
  grep-clean for wall-clock/network) logged in `generator_trace.log`.
