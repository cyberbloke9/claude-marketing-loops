# Contract — Sprint 005: Scorecard compiler → `metrics/YYYY-Www.md`

> Closes the **compile half** of Gap 3 (spec §5.2, §11). Consumes the frozen
> Sprint-004 **INGEST** structure (`build_ingest(...)`) plus the optional
> Sprint-002 **QUEUE** document (`content/publish-queue.json`) and renders the
> weekly scorecard `metrics/YYYY-Www.md`, section-for-section faithful to
> `metrics/TEMPLATE.md`, with an appended **Missing data** section listing every
> blanked input. Implements B-A5 (WRR, incl. the no-partial-sum critical edge),
> B-A6 (flywheel), B-A7 (craft diagnostics + hook #), B-A8 (posting-time A/B),
> B-A9 (decisions fed back), B-A10 (output fidelity), B-A11 (UTM flagging), and
> B-A12 (the `loop-measure` SKILL update).
>
> **This sprint reads INGEST + QUEUE and writes Markdown. It defines NO new JSON
> schema, invents NO metric, and never modifies a Sprint-001..004 module.** It is
> the last build slice before the Sprint-006 acceptance runner.
>
> This is a **CLI + importable pure library** deliverable — no routes, screens,
> components, or Playwright paths. Verification is exact CLI invocations + exit
> codes + stdout/stderr substrings + **byte-for-byte golden-Markdown** assertions,
> mirroring the DNA of `tools/marketing-render/` and the PASSED Sprints 001–004.

## 1. Scope (this sprint only)

Deliver the scorecard-compiler layer of the Gap-3 analytics toolchain:

- A **pure builder** `build_scorecard(ingest, queue_or_none, week) -> (markdown, missing)`
  that turns the validated INGEST dict (Sprint-004 §3.5) plus an optional loaded
  QUEUE dict (Sprint-002) into the scorecard Markdown string and the ordered list
  of Missing-data entries. No I/O, no wall-clock, no network in the builder.
- A **CLI** `scorecard.py` that reuses `ingest.run(args)` to build the INGEST
  structure (thereby **inheriting every B-A3 corrupt-CSV rejection** → exit 2 with
  no output), optionally loads the QUEUE via the frozen `queue.load_queue`, calls
  `build_scorecard`, and writes `metrics/<week>.md` (or a `--out` path, or stdout).
- The **template-faithful renderer**: North star (WRR), Flywheel, Craft
  diagnostics, Posting-time A/B, Vanity, Decisions fed back — heading-for-heading
  with `metrics/TEMPLATE.md` — plus an appended `## Missing data` section.
- The **B-A5 WRR critical edge**: WRR is filled **only** when all three component
  inputs are present; if **any** is absent, WRR is **blank** and each missing
  component is listed under Missing data. A partial sum is forbidden.
- The **B-A12** update to `.claude/skills/loop-measure/SKILL.md` to invoke the new
  CLI and state the malformed-CSV-vs-missing-input distinction + never-invent rule.
- Unit tests + **golden-Markdown fixtures** under `tools/marketing-loops/`.

**Explicitly OUT of this sprint** (Sprint 006, §11): the end-to-end
`acceptance.py` runner across both gaps, the adversarial cross-gap fixture suite,
and the `README.md` Phase-0 rollout-box update. See §7.

## 2. Files created / affected

New, under `tools/marketing-loops/`:

- `scorecard.py` — the scorecard CLI **and** its pure builder
  `build_scorecard(ingest, queue, week)`. Imports the frozen `ingest` (to build
  the INGEST structure and inherit CSV rejection) and the frozen `queue` (to load
  the optional publish queue) and `schedule` only if a documented constant is
  needed. No new schema, no `schema_version` (output is Markdown). Parses args →
  validates (inherited) → builds → renders → writes. Maps errors to exit codes.
- `tests/test_scorecard.py` — unit tests over the pure builder + the CLI (via
  `subprocess` or `main(argv)`), asserting golden-Markdown byte-equality,
  determinism, exit codes, and every §9 row.
- `fixtures/metrics/expected/<name>.md` — **golden scorecard Markdown** files
  (byte-for-byte expected outputs) for the full, partial, empty, wrong-UTM,
  wrr-partial, and unmatched cases. Fixtures live **under `tools/`, never under
  `content/` or the real `metrics/`.**
- New input fixtures under `tools/marketing-loops/fixtures/metrics/` **only where a
  Sprint-004 fixture does not already cover the case** — specifically a
  `wrr-partial/` site CSV (one WRR component column blank, the other two present)
  and a small `queue.json` fixture for the A/B table. Reuse existing `full/`,
  `wrong-utm/`, `unmatched/`, `blank-cell/`, `zero-cell/`, `header-only/`,
  `truncated/`, `wrong-header/` fixtures as-is.

**Read-only — imported, NOT modified** (Sprints 001–004 are frozen and PASSED):
`utm.py`, `gate.py`, `queue.py`, `channels.py`, `captions.py`, `schedule.py`,
`package.py`, `mark_posted.py`, `enqueue.py`, `verify_utm.py`, `csvspec.py`,
`assetmap.py`, `ingest.py`, and all existing tests + fixtures. No function is
added to any frozen module; `scorecard.py` only *imports* them. No PASSED contract
may regress: the full Sprint 001–004 unit suite must still pass unchanged.

**No new machine schema is introduced.** The scorecard output is human-readable
Markdown; its only machine inputs are the existing INGEST (built in-process) and
QUEUE (loaded via `queue.load_queue`). The single tracked write is the scorecard
`.md` file where the operator points `--out` (default `metrics/<week>.md`).

## 3. Exact behaviors

### 3.1 CLI shape

```
python3 tools/marketing-loops/scorecard.py --week YYYY-Www \
  [--instagram FILE] [--youtube FILE] [--linkedin FILE] [--site FILE] \
  [--content-dir DIR] [--queue FILE] [--out FILE | --stdout]
```

- The four `--<source>` flags, `--week`, and `--content-dir` have **identical
  semantics to `ingest.py`** (Sprint-004 §3.4). `scorecard.py` builds the INGEST
  structure by delegating to `ingest.run(args)` (or `ingest.build_ingest` after the
  same validation), so **every ingestion rule is inherited verbatim**: bad `--week`
  → exit 2; a provided `--<source>` path that does not exist → exit 2; a corrupt
  CSV (unparseable / missing header / wrong column count / truncated / non-numeric
  numeric cell / blank join column) → **exit 2, cited message on stderr, NO
  scorecard written** (B-A3 / story #7); an absent source → recorded missing,
  contributes blanks; the empty run (no sources) → valid all-blank scorecard.
- `--queue FILE` (optional) is the publish-queue path. Loaded via
  `queue.load_queue`. A missing file path passed to `--queue` → exit 2
  (`--queue file not found: <path>`). A file that exists but is not a valid QUEUE
  document (unparseable JSON / no `rows` list) → exit 2 (cited, no scorecard).
  When `--queue` is omitted, the posting-time A/B table is entirely blank + listed
  under Missing data (§3.6).
- Output: by default writes `metrics/<week>.md` (repo `metrics/` resolved from
  `__file__`; parent `mkdir -p`). `--out FILE` overrides the path. `--stdout`
  writes the Markdown to stdout and writes no file (for preview / tests).
  `--out` and `--stdout` are mutually exclusive → exit 2 if both given.
- On success the CLI prints the written path (or nothing extra when `--stdout`) and
  exits **0**.

### 3.2 Output fidelity — the template skeleton (B-A10)

The rendered Markdown reproduces `metrics/TEMPLATE.md` **section-for-section,
heading-for-heading**, with the literal week substituted into the title:

1. `# Weekly Scorecard — <week>` (the `YYYY-Www` from `--week`).
2. The template's one-line preamble, verbatim.
3. `## North star` — the WRR table (§3.3).
4. `## Flywheel` — the flywheel table (§3.4).
5. `## Craft diagnostics (per asset)` — the craft table (§3.5).
6. `## Posting-time A/B (weeks 1–8)` — the A/B table (§3.6).
7. `## Vanity (tracked, never optimized)` — Followers/Likes line (§3.7).
8. `## Decisions fed back` — the decisions section (§3.8).
9. `## Missing data` — the appended enumeration (§3.9). **Not** in the template;
   it is the mandated appendix (spec §5.4 "Missing-data listing", B-A4/B-A10).

A **blank cell** is rendered as an empty table cell (the text between the pipes is
a single space, matching the template's own empty rows). No cell ever shows a
placeholder like `N/A`, `0`, `—`, `TODO`, or an invented number. The document ends
with exactly one trailing newline. Section order and heading text are fixed;
determinism (§3.10) guarantees byte-stable output.

### 3.3 North star / WRR (B-A5) — THE CRITICAL EDGE

The WRR row: `| **WRR — …** | <this-week> | <last-week> | <trend> |` (the metric
label copied verbatim from the template).

- **This week** = the integer sum `returning_viewers + digest_opens +
  returning_visitors_social` **iff all three** `ingest["wrr_components"][*]
  ["present"]` are `true`. Rendered as that integer.
- **If ANY of the three components is absent** (`present == false`): the This-week
  cell is **blank**, and **each** absent component is listed individually under
  Missing data (`WRR component 'returning_viewers' absent` etc.). A partial sum of
  the present components is **forbidden** — it is an invented number (spec B-A5).
  The present components are NOT shown anywhere as a running total.
- **Last week** and **Trend** cells are **always blank** this sprint: the tool does
  not read a prior scorecard, so last-week WRR and the trend are unavailable →
  each listed under Missing data (`last-week WRR not provided (no prior-week
  input)`, `WRR trend not computable (needs last-week WRR)`). The tool never
  fabricates a trend arrow.

Worked example (full fixture, `2026-W27`): components 200 + 95 + 52 → **This
week = 347**; Last week + Trend blank + two Missing-data lines. Blank one
component's column (the `wrr-partial` fixture) → **This week blank**, the missing
component listed, and the two present components NOT summed.

### 3.4 Flywheel (B-A6)

The template's three-row Flywheel table is reproduced with fixed row labels:

| Row label (verbatim from template) | Value | Notes |
|---|---|---|
| `Clicks to intel.terrem.in (by UTM campaign)` | per-campaign click lines | — |
| `Locality-page sessions from social` | blank | (no input column) |
| `Sign-ups / alerts created from content traffic` | blank | (no input column) |

- **Row 1 Value cell** is filled from `ingest["flywheel_clicks_by_campaign"]`
  (already social-filtered + grouped + summed by Sprint 004), one line per campaign
  in the INGEST order (lexicographic by campaign), formatted `<campaign>: <clicks>`.
  A campaign whose `clicks` is `null` renders `<campaign>: ` (blank click value)
  and is listed under Missing data. If the site source was not provided at all →
  the Value cell is blank and Missing data carries the single `site analytics
  export not provided` entry (no per-campaign spam).
- **Rows 2 and 3** have **no column** in any Sprint-004 CSV contract → their Value
  cells are **always blank** and each is listed once under Missing data
  (`Flywheel 'Locality-page sessions from social' has no input column`, likewise
  for sign-ups). Stated here so the empty cells are documented intent, not a defect.

### 3.5 Craft diagnostics (B-A7)

One table row per `ingest["craft"]` entry, in the INGEST order
(`(campaign, channel)`), columns exactly:
`| Asset | Channel | 3s-hold % | Completion / swipe-through % | Shares | Clicks | Hook # |`.

- **Asset** = the entry's `slug` when matched; for an **unmatched** campaign
  (`slug == null`) render the campaign string suffixed with ` (unmatched)` and list
  the campaign under Missing data (`unmatched-campaign: <campaign>`), so metrics are
  never silently attributed to a nonexistent asset.
- **Channel** = the entry's channel (`instagram`/`youtube`/`linkedin`).
- **3s-hold %, Completion %, Shares, Clicks** = the entry's numeric values. An
  **absent** cell (`null`) renders **blank** (never `0`); a genuine `0` renders `0`.
  The blank cell is listed under Missing data with its asset+channel+metric.
- **Hook #** = the entry's `hook_number`; `null` renders blank and is listed under
  Missing data (`hook # absent for <slug>`). The tool never invents a hook number.
- Zero craft entries (empty run) → a header-only table (no data rows) and the
  Missing-data listing carries the source-absence lines.

### 3.6 Posting-time A/B (B-A8) — single-week semantics, pinned

The A/B table has one row per channel in canonical order (`instagram`, `youtube`,
`linkedin`), columns:
`| Channel | Morning slot perf | Evening (3–8pm IST) perf | Verdict so far |`.

**Rationale (pinned, non-defect):** the schedule bucket is deterministic in
`schedule.py` as `bucket = morning if (WW + channel_ordinal) % 2 == 0 else
evening` — it depends only on `(week, channel)`, **not** on the asset. Therefore in
any **single** week every asset of a given channel shares **one** bucket, so at
most **one** of {Morning, Evening} can hold a number and the other is
**necessarily blank**. A morning-vs-evening **verdict** requires ≥2 weeks with
opposite buckets and the compiler has exactly one week's INGEST → the verdict is
**always blank** in a single-week scorecard. These blanks are **intended**, and
each is listed under Missing data with that reason. This is documented here so a
hostile reviewer reads the half-empty table as correct, not as missing work.

Per channel:

- Read the recorded bucket from the **QUEUE**, never recompute it: find queue
  `rows` with `week == --week` and `channel == <channel>` and a non-null
  `schedule_slot`; parse the bucket from the slot string `<week>/<bucket>/<HH:MM>`
  (split on `/`, take index 1). Recomputing via `schedule.bucket_for` is
  **forbidden** — it would fabricate a slot for an asset that was never queued.
- **Perf cell (the documented scalar):** for the bucket the queue rows fall in,
  the cell = the **sum of `clicks`** across that channel's craft entries for the
  week whose `clicks` are present (non-null). Computed from present values only; if
  the channel has no craft entries with present clicks, the cell is blank + Missing
  data. This single scalar is chosen for clean golden-testing (spec §7
  determinism); it is a measured aggregate, never an estimate. The **opposite**
  bucket cell is blank + Missing data (`no <channel> <bucket> data in <week>`).
- **Verdict cell:** always blank; one Missing-data line per channel
  (`posting-time A/B verdict for <channel> needs cross-week comparison`).
- **No `--queue` provided:** every cell blank; Missing data carries a single
  `publish queue not provided (posting-time A/B table blank)` line (no per-channel
  spam). A channel with a queue but no matching row for the week → both perf cells
  blank + a `no <channel> slot recorded for <week>` Missing-data line.

### 3.7 Vanity (B-A10 fidelity)

Reproduce the template's `Followers: __ · Likes: __` line with **both blanks
preserved** (rendered `Followers:  · Likes: ` — the value after each colon empty).
No Sprint-004 CSV contract carries followers or likes, so both are **always blank**
and each is listed once under Missing data (`Vanity 'Followers' has no input
column`, likewise Likes). Documented intent, not a defect.

### 3.8 Decisions fed back (B-A9)

Reproduce the template's `## Decisions fed back` bullet structure. Fill **only**
what the data supports; blank the rest + list under Missing data:

- **Hook winners & retirements bullet (→ Loop 2):** compute the **top** and
  **bottom** hook by the same documented scalar as §3.6 — each **asset's** total
  `clicks` across its channels (present values only). Requires **≥2 matched assets**
  each with ≥1 present clicks value and a resolved `hook_number`. Deterministic
  tie-break: higher clicks wins; ties broken by ascending `slug`. Render e.g.
  `→ Loop 2: top hook #11 (347 clicks); retire-candidate hook #7 (54 clicks)`. If
  fewer than 2 qualifying assets → the bullet's data clause is **blank** and a
  Missing-data line is added (`hook ranking needs ≥2 assets with clicks + hook #`).
- **Signal-types bullet (→ Loop 1)** and **format-changes bullet (→ Loop 3)** are
  **qualitative, not data-derivable** → rendered as the template's label with no
  data clause + one Missing-data line each (`Loop 1 signal-resonance decision is
  qualitative (operator-authored)`, likewise Loop 3).
- **Hard-stop check (WRR flat after 8 weeks):** reproduce the template's bold
  hard-stop line; the flat-across-8-weeks determination needs 8 weeks of scorecards
  and the compiler has one → the line is reproduced but its verdict is **blank** +
  a Missing-data line (`hard-stop WRR-flat check needs 8 published weeks`). Never
  fabricates a stop/continue verdict.

### 3.9 Missing data section (spec §5.4)

An appended `## Missing data` section: an **ordered, de-duplicated** bullet list of
every input/cell left blank and **why**, drawing from:

1. The INGEST `absences` list (source-not-provided, wrr-component, unmatched-
   campaign, wrong-utm) — rendered verbatim as `<kind>: <detail>` bullets.
2. The renderer's own structural blanks (last-week/trend WRR, flywheel rows 2–3,
   vanity, A/B blanks + verdicts, decisions blanks) as pinned in §3.3–§3.8.
3. **B-A11 UTM flags:** every asset in `ingest["assets"]` with `utm_valid == false`
   is listed (`wrong-UTM asset <slug>: <violations>`) so a scheme-invalid asset is
   **never silently attributed** (the INGEST `wrong-utm` absence already carries
   this; the renderer surfaces it in this section).

Ordering is deterministic: bullets sorted lexicographically by their rendered text,
de-duplicated. When there is genuinely nothing missing (full fixture with a valid
queue and both WRR-adjacent structural blanks) the section still lists the
**structural** blanks that are always absent (last-week WRR, trend, flywheel rows
2–3, vanity, A/B verdicts) — it is honest about what a single-week scorecard cannot
contain, and is never falsely empty.

### 3.10 Determinism (spec §7)

Same inputs → **byte-identical** scorecard Markdown. Row ordering: assets/craft by
the INGEST order (already `(campaign, channel)` / slug-sorted); flywheel by
campaign (lexicographic); A/B by canonical channel order; Missing-data bullets
lexicographically sorted + de-duplicated. **No `datetime.now()` or any wall-clock**
in output — the only date-ish value is the operator-supplied `--week` (used as a
literal string). **No network.** Two runs with the same inputs `shasum`-match.

### 3.11 Exit codes (match ingest / render / Sprints 001–004)

- **`0`** — success, including the **full**, **partial** (some sources absent), and
  **empty** (no sources) runs. A valid partial/empty scorecard is a success (spec
  §6 "Partial input … exit 0").
- **`1`** — **intentionally unused**, mirroring `ingest.py`: there is no "domain
  verdict on well-formed input." Corrupt CSV / bad queue / bad path are usage
  errors (→ 2); missing inputs and wrong-UTM are handled inside a successful
  scorecard (blanks + Missing data). Documented for the Sprint-006 taxonomy.
- **`2`** — **usage / precondition error**, message on **stderr**, **no scorecard
  written**: bad `--week`; a provided `--<source>` path not found; a bad
  `--content-dir`; an asset-map campaign collision; **every inherited B-A3 CSV
  rejection**; a `--queue` path not found or an invalid QUEUE document; and both
  `--out` and `--stdout` given together.

## 4. States

- **Empty (no sources, no queue):** `--week` only → exit 0; full template skeleton
  with all tables blank (craft header-only), Vanity blank, Decisions data-clauses
  blank, A/B all blank, and a Missing-data section enumerating every source
  absence + every structural blank.
- **Full success:** four well-formed sources + a valid queue → WRR filled (347 in
  the worked example), flywheel row 1 per-campaign clicks, all craft rows filled
  with slug+hook#, the one populated A/B bucket per channel, decisions hook
  ranking filled; Missing data lists only the always-structural blanks (last-week
  WRR, trend, flywheel rows 2–3, vanity, A/B opposite-buckets + verdicts).
- **WRR partial (the critical edge):** site CSV with one WRR component column
  blank → WRR This-week **blank**, that component listed, the other two **not
  summed** anywhere; exit 0.
- **Partial sources:** e.g. IG-only → craft rows only for IG, flywheel/WRR blank
  (site absent), every blank enumerated; exit 0.
- **Corrupt CSV:** truncated / wrong-header / wrong-colcount / non-numeric /
  blank-join → exit 2 (inherited), cited, **no `metrics/*.md` written** (verify no
  file appears even when `--out`/default path was targeted).
- **Bad queue:** `--queue` to a nonexistent path → exit 2; `--queue` to malformed
  JSON → exit 2, cited, no scorecard.
- **Unmatched campaign:** a CSV campaign with no asset → craft row
  `Asset = <campaign> (unmatched)`, listed under Missing data; exit 0.
- **Wrong-UTM asset (B-A11):** an asset whose `meta.md` UTM is scheme-invalid →
  `utm_valid=false`, surfaced as a `wrong-UTM asset <slug>: …` Missing-data bullet;
  its metrics are not silently attributed; exit 0.
- **Overwrite (weekly re-run):** re-running with the same inputs rewrites the same
  bytes (idempotent, guaranteed by §3.10); re-running with new data updates the
  file. Overwrite is **intended** — a scorecard is fully regenerable and loses no
  human-entered state (unlike a render or a `posted` queue row), so no `--force`
  gate is added.
- **Idempotency / determinism:** same inputs → byte-identical Markdown; two runs
  `shasum`-match.
- **Offline:** no network; any network import is a defect.

## 5. Non-UI expectations (a11y / responsive / contrast do not apply)

Headless CLI + importable library. In place of keyboard/focus/ARIA/contrast/
responsive:

- **Usability:** every rejection message is specific and recoverable — it names
  the file/row/column (inherited from ingest) or the queue path/reason, never a
  bare "invalid input". The written scorecard prints its path so the operator
  knows where it landed.
- **Runs from any cwd:** paths resolved from `__file__`; default `--content-dir`
  is repo `content/`, default output is repo `metrics/<week>.md`; every path arg
  accepts absolute or relative.
- **Import safety:** importing `scorecard` has no side effects and prints nothing.
- **Single source of truth:** the INGEST is built via the frozen `ingest` module
  (no re-implemented CSV parsing, join, or aggregation); the queue is loaded via
  the frozen `queue.load_queue`; the channel order + bucket parsing derive from the
  frozen `schedule`/`utm` maps (no forked literals).

## 6. Security / privacy

- Stdlib only (`argparse`, `json`, `re`, `pathlib`) plus in-repo imports
  (`ingest`, `queue`, `schedule`, `utm`). **No** `datetime` for "now" (no date math
  is required; `--week` is a literal string). No third-party deps. No network. No
  secrets. No personal data written. CSV inputs remain **untrusted** and are parsed
  by the frozen `csvspec` (every malformation → cited exit 2, never a crash, never
  an invented value). No dependency on the globally-installed `pmp-gywd@5.0.0`.
- The only write is the scorecard `.md` at the operator-pointed path; tests write
  to temp / `--stdout` only and never mutate the real `content/` or `metrics/`.

## 7. Explicit non-goals (this sprint)

- **No `acceptance.py` end-to-end runner, no cross-gap adversarial suite** —
  Sprint 006.
- **No `README.md` rollout-box update** — Sprint 006.
- **No new JSON schema, no `schema_version`** — the output is Markdown; inputs are
  the existing INGEST + QUEUE.
- **No modification** of any Sprint-001..004 module, test, fixture, or any
  `content/*` file. No re-implementation of CSV parsing / join / aggregation.
- **No reading of a prior-week scorecard** — last-week WRR and trend stay blank +
  listed (§3.3). No cross-week A/B verdict, no 8-week hard-stop verdict.
- **No estimation, interpolation, defaulting, zero-filling, partial WRR sum, or
  generated marketing/qualitative prose** — absent stays blank; `0` is only ever a
  genuinely present `0`.
- **No live posting APIs, no network, no scraping** — inputs are operator-provided
  CSV + the local queue file only.

## 8. Commands to run

```bash
cd /Users/prithviputta/Downloads/terrem-marketing-loops
FX=tools/marketing-loops/fixtures/metrics

# Full unit suite (Sprints 001+002+003+004+005 must all pass)
python3 -m unittest discover -s tools/marketing-loops/tests -v

# Full happy path -> exit 0, scorecard to stdout; WRR = 347, flywheel + craft filled
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --instagram "$FX/full/ig.csv" --youtube "$FX/full/yt.csv" \
  --linkedin "$FX/full/li.csv" --site "$FX/full/site.csv" \
  --content-dir "$FX/full/content" --queue "$FX/full/queue.json" --stdout ; echo "exit=$?"

# Golden byte-equality (full)
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --instagram "$FX/full/ig.csv" --youtube "$FX/full/yt.csv" \
  --linkedin "$FX/full/li.csv" --site "$FX/full/site.csv" \
  --content-dir "$FX/full/content" --queue "$FX/full/queue.json" --stdout \
  | diff - "$FX/expected/full.md" && echo "GOLDEN-MATCH"

# WRR critical edge: one component blank -> WRR blank, NO partial sum
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --site "$FX/wrr-partial/site.csv" --content-dir "$FX/full/content" --stdout \
  | grep -A2 "North star"   # This-week cell blank
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --site "$FX/wrr-partial/site.csv" --content-dir "$FX/full/content" --stdout \
  | grep -i "WRR component"  # each missing component listed

# Empty state: no sources, no queue -> exit 0, all-blank skeleton + full Missing data
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --content-dir "$FX/full/content" --stdout ; echo "exit=$?"

# Determinism: two runs -> byte-identical
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --site "$FX/full/site.csv" --content-dir "$FX/full/content" --stdout | shasum
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --site "$FX/full/site.csv" --content-dir "$FX/full/content" --stdout | shasum

# Corrupt CSV inherited rejection -> exit 2, NO scorecard file written
OUT=$(mktemp -u).md
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --site "$FX/truncated/site.csv" --content-dir "$FX/full/content" --out "$OUT"
echo "exit=$? ; file exists? $([ -f "$OUT" ] && echo YES || echo no)"

# Bad queue -> exit 2
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --content-dir "$FX/full/content" --queue /no/such/queue.json --stdout ; echo "exit=$?"

# Default-path write (to a temp metrics dir), then confirm path printed
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
  --site "$FX/full/site.csv" --content-dir "$FX/full/content" \
  --out "$(mktemp -d)/2026-W27.md" ; echo "exit=$?"

# Import-safety + no wall-clock / no network in the new source
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); import scorecard; print('ok')"
grep -nE "datetime\.now|requests|urlopen|socket|urllib" \
  tools/marketing-loops/scorecard.py || echo "clean"

# Frozen modules unchanged (no diff vs prior sprint)
python3 -m unittest discover -s tools/marketing-loops/tests -q  # 205+ tests still green
```

## 9. Evaluator attack checklist (CLI, not Playwright)

New fixtures under `tools/marketing-loops/fixtures/metrics/`: `expected/*.md`
(golden Markdown), `wrr-partial/site.csv` (one WRR component blank), and
`full/queue.json` (A/B slots). Reuse existing input fixtures. Required behaviors:

| Attack | Expected |
|---|---|
| Full happy path + `--queue` | exit 0; **byte-equal** `expected/full.md`; WRR=347; flywheel row1 per-campaign; all craft rows w/ slug+hook#; one A/B bucket filled per channel; decisions hook ranking filled |
| **WRR one-component-blank** (`wrr-partial`) | exit 0; WRR This-week **blank**; that component listed under Missing data; the other two **NOT** summed anywhere in the file |
| WRR all-absent (no site) | exit 0; WRR blank; all three components listed |
| Empty run (no sources, no queue) | exit 0; full skeleton, all tables blank (craft header-only); Missing data enumerates every source + structural blank |
| Determinism | two runs → identical `shasum`; golden byte-match |
| Corrupt CSV (`truncated`/`wrong-header`/`wrong-colcount`/`non-numeric`/`blank-join`) | **each** exit 2, cited (inherited), **no scorecard file created** even with `--out` |
| Bad `--queue` path / malformed queue JSON | exit 2, cited, no scorecard |
| Unmatched campaign (`unmatched`) | exit 0; craft `Asset = <campaign> (unmatched)`; listed under Missing data |
| Wrong-UTM asset (`wrong-utm`) | exit 0; `wrong-UTM asset <slug>: <violations>` under Missing data; metrics not silently attributed |
| `blank-cell` vs `zero-cell` craft | blank metric renders **blank** + listed; `0` renders `0`; never conflated |
| No `--queue` | exit 0; A/B table entirely blank; single `publish queue not provided` Missing-data line |
| A/B single-week semantics | per channel at most one bucket filled, opposite blank, verdict blank — all as intended (§3.6), each listed under Missing data |
| `--out` + `--stdout` together | exit 2 (usage) |
| Bad `--week` (`2026-27`, `26-W27`) | exit 2, no scorecard |
| Import safety + grep | `import scorecard` prints nothing; no `datetime.now`/network in the source |
| Frozen modules untouched | Sprint 001–004 suite still fully green; no frozen file mtime change |

Adversarial probes the Evaluator should run:

1. **Golden match** — full run → byte-equal `expected/full.md`; hand-verify WRR=347,
   flywheel clicks per campaign, every craft cell against the fixture CSVs, the one
   populated A/B bucket per channel, the hook ranking (#11 top, #7 bottom by total
   clicks), and that Missing data lists exactly the structural blanks.
2. **WRR no-partial-sum** — `wrr-partial` → grep the whole file for the sum of the
   two present components; it must **not** appear anywhere. WRR cell blank; the
   absent component named.
3. **Corruption never becomes a blank cell** — each corrupt CSV → exit 2, empty
   stdout, and **no** `metrics/*.md` or `--out` file created.
4. **A/B honesty** — confirm the half-empty A/B table + blank verdicts are present
   AND explained in Missing data; confirm no bucket is fabricated for an asset with
   no queue row (drop `--queue` → whole table blank).
5. **Determinism** — run twice → `shasum` identical; reorder input flags → identical
   output (INGEST sorts internally).
6. **Never-invent sweep** — grep the full-run and empty-run outputs for `N/A`,
   `TODO`, `0` in a cell that should be blank, a fabricated trend arrow, or any
   number not traceable to an input cell. None permitted.
7. **Frozen suite** — `python3 -m unittest discover` → the full Sprint 001–004
   suite still green; diff the frozen modules → unchanged.
8. **SKILL update (B-A12)** — `.claude/skills/loop-measure/SKILL.md` invokes
   `scorecard.py`, states the malformed-CSV (exit 2) vs missing-input (blank +
   Missing data) distinction and the never-invent rule, mirroring the loop-publish
   SKILL style.

## 10. Definition of done

- `scorecard.py` exposes a pure `build_scorecard(ingest, queue_or_none, week) ->
  (markdown, missing)` and a CLI that reuses `ingest.run(args)` (inheriting all
  B-A3 rejection → exit 2, no output), optionally loads the QUEUE via
  `queue.load_queue`, renders the template-faithful scorecard + Missing-data
  appendix, and writes `metrics/<week>.md` / `--out` / `--stdout`; partial and
  empty runs are exit-0 successes; exit 1 is unused; corrupt CSV / bad queue / bad
  path → exit 2 with no scorecard.
- WRR obeys the B-A5 critical edge: filled only when all three components present;
  any absent → blank + each listed, never a partial sum.
- Flywheel, craft (blank≠0, unmatched flagged, hook# blank-not-invented), A/B
  (single-week semantics pinned, buckets read from the queue, verdict blank),
  vanity (blank), and decisions (hook ranking filled, qualitative bullets blank,
  hard-stop verdict blank) all render per §3, with every blank enumerated under
  Missing data and B-A11 wrong-UTM assets surfaced there.
- Output is byte-deterministic (golden Markdown fixtures + `shasum`-twice), with no
  wall-clock and no network.
- `.claude/skills/loop-measure/SKILL.md` updated (B-A12) to invoke the CLI and state
  the malformed-vs-missing distinction + never-invent rule.
- Unit tests + golden fixtures for every §9 row shipped under
  `tools/marketing-loops/`; all pass alongside the untouched Sprint 001–004 suite.
- Evidence (command output, exit codes, golden-diff results, before/after `shasum`,
  grep-clean for wall-clock/network, frozen-suite green) logged in
  `generator_trace.log`.
