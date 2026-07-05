# Contract — Sprint 003: Publish packages + schedule slot + mark-posted + `/loop-publish`

> Closes the second half of Gap 2 (spec §5.1): per-channel publish **package**
> generation (B-P4 attachments + B-P5 caption assembly), the deterministic
> **schedule slot** (B-P6), the human-in-the-loop **mark-posted** transition
> (B-P7), and the **`/loop-publish` skill** (B-P9). Builds directly on the
> Sprint-002 gate/queue/channels modules and the Sprint-001 UTM module — all
> imported, none forked, none modified.
>
> This is a **CLI / library + one skill doc** deliverable, not a web app — there
> are no routes, screens, or Playwright paths. Verification is exact CLI
> invocations + exit codes + stdout/stderr substrings + on-disk JSON byte
> assertions, mirroring the DNA of `tools/marketing-render/` and the
> already-PASSED Sprints 001/002.

## 1. Scope (this sprint only)

Deliver the package + posting-transition layer of the publish toolchain:

- A **caption source** (`captions.md`) authored per asset, plus an importable
  parser that resolves a per-channel caption **body** from it — and errors (never
  invents) when the body is absent (B-P5 / A-3).
- A pure, importable **schedule-slot** function: `(week, channel)` → a
  deterministic morning/evening A/B-bucket slot string, no wall-clock (B-P6 / A-4).
- A **package** CLI that, on a gate-passing asset, writes one per-channel
  **PACKAGE** JSON file (§5.4 PACKAGE) — final caption (authored body + correct
  **per-channel** UTM link), ordered attachment PNG paths (from `manifest.json`),
  and the schedule slot — and updates the Sprint-002 **QUEUE** rows in place with
  `schedule_slot` + `package_path`. It **re-runs the Sprint-002 gate** and never
  bypasses it (B-P4 / B-P9).
- A **mark-posted** CLI that transitions one `(slug, channel)` QUEUE row from
  `queued` → `posted`, recording `--posted-on` and `--permalink`, refusing any
  row that is not currently `queued` and any empty/non-URL permalink (B-P7).
- A **`.claude/skills/loop-publish/SKILL.md`** documenting the operator flow
  (gate+package → read packages → post by hand → mark-posted), invoking the CLIs
  and adding no taste judgement (B-P9), mirroring `loop-qa`.
- Unit tests + fixtures covering every path below.

**Explicitly OUT of this sprint** (Sprints 004–006): any analytics / CSV /
scorecard work; any change to the four gate conditions; live posting APIs. See §7.

## 2. Files created / affected

New, under `tools/marketing-loops/` (Generator may adjust private helper names but
MUST honor the behaviors, the importable-pure-function requirement, and the
fixtures-live-under-`tools/` rule):

- `captions.py` — **importable pure module**: parse `captions.md`; resolve a
  per-channel caption body (§3.1). No CLI side effects on import.
- `schedule.py` — **importable pure module**: `slot_for(week, channel)` → slot
  string (§3.2). No wall-clock, no import side effects.
- `package.py` — the package CLI + its pure builder functions (§3.3). Imports
  `gate`, `channels`, `queue`, `utm`, `captions`, `schedule`. Runs the gate,
  refuses/usage-errors or writes packages + updates the queue.
- `mark_posted.py` — the mark-posted CLI + pure transition function (§3.4).
  Imports `queue`.
- `tests/test_captions.py`, `tests/test_schedule.py`, `tests/test_package.py`,
  `tests/test_mark_posted.py` — unit tests.
- `fixtures/publish/<fx-name>/` — new packaging fixtures (each a full asset
  folder: `meta.md` + `render/qa-verdict.json` + `render/manifest.json` +
  `captions.md` as applicable), listed in §9. Fixtures live **under `tools/`,
  never under `content/`**.

New, in the repo:

- `.claude/skills/loop-publish/SKILL.md` — the skill doc (§3.5), frontmatter +
  steps mirroring `.claude/skills/loop-qa/SKILL.md`.
- `content/2026-07-03-tgrera-enforcement-wave/captions.md` — the real asset's
  authored caption source (§3.1 "Real-asset caption provenance"). **Its body is
  transcribed verbatim from copy already authored in the asset** (the `Hook:`
  line, `meta.md` line 6) — no new marketing claim is introduced; the tool never
  writes prose (B-P5). This is the *only* touch to `content/` this sprint, and it
  is the spec-sanctioned A-3 caption-field introduction, not a content rewrite.

**Read-only — imported, NOT modified** (their Sprint-001/002 contracts are frozen
and already PASSED): `utm.py`, `gate.py`, `queue.py`, `channels.py`, and all of
`content/*` except the one new `captions.md` above and any `content/<slug>/publish/`
or `content/publish-queue.json` artifacts the tool itself writes. New shared logic
this sprint needs (per-channel link building, package-row merging) is authored in
the **new** modules and only *imports* the frozen ones — no function is added to
`utm.py`/`queue.py`, so no PASSED contract can regress.

Default production paths (created on first real run; tracked, non-secret
artifacts): QUEUE `content/publish-queue.json`; PACKAGE files
`content/<slug>/publish/<channel>.json`. Neither is written during tests — tests
pass `--queue <tmp>` and `--publish-dir <tmp>` (§3.6, §8).

## 3. Exact behaviors

### 3.1 Caption source + resolver (`captions.py`) — B-P5 / A-3

**The `captions.md` format** (mirrors the existing `meta.md`
`<!-- provenance:start -->` marker convention — codebase DNA). An asset's caption
source is `content/<slug>/captions.md` containing one or more delimited blocks:

```
<!-- caption:all:start -->
<shared caption body — arbitrary text, preserved verbatim>
<!-- caption:all:end -->

<!-- caption:instagram:start -->
<optional Instagram-specific override body>
<!-- caption:instagram:end -->
```

- Block key is `all` or one of the canonical channels
  `{instagram, youtube, linkedin}` (imported from `utm.CHANNEL_SOURCE_MAP`).
- **Body extraction** is deterministic: the text strictly between a block's
  `:start`/`:end` markers, with leading/trailing blank lines stripped and interior
  text preserved byte-for-byte (no reflow, no trimming of interior whitespace).
- **Per-channel resolution:** for a channel `c`, use the `caption:<c>` block if
  present; else fall back to the `caption:all` block; if **neither** exists →
  the body is **absent** for `c`.

Importable pure API (no writes, no wall-clock, no network):

- `parse_captions(text) -> {block_key: body_str, ...}` — parses all blocks. A
  malformed block (a `:start` with no matching `:end`) → raise `ValueError`
  (the CLI turns this into exit 2). Duplicate block keys → `ValueError`.
- `body_for(blocks, channel) -> str | None` — applies the resolution order
  above; returns `None` when the body is absent for that channel.

**Absent caption is an error, never an invention (B-P5):** if `captions.md` is
missing, unparseable, or has no resolvable body for a channel that is about to be
packaged, `package.py` exits 2, names the asset + the specific channel(s) lacking
a body, and writes **no** package file and **no** queue change (§3.3 step 8). The
tool NEVER substitutes, defaults, or generates caption text.

**Real-asset caption provenance:** `content/2026-07-03-tgrera-enforcement-wave/captions.md`
carries a single `caption:all` block whose body is the asset's own authored `Hook:`
line (`meta.md` line 6), transcribed verbatim. No claim absent from the asset is
added. (The primary *tested* happy-path anchor is a **fixture** with a
Generator-authored caption — normal test data; the real asset merely proves the
end-to-end flow runs on real content.)

### 3.2 Schedule slot (`schedule.py`) — B-P6 / A-4

Pure `slot_for(week, channel) -> str`. **No `datetime.now()`; derived only from
the operator-supplied `--week` and fixed documented constants.**

- `week` is validated `^\d{4}-W\d{2}$`; the 2-digit `WW` is parsed as an int.
- Channel **ordinal** (canonical order): `instagram=0, youtube=1, linkedin=2`.
- **A/B bucket** (deterministic, alternates by week to yield the weeks-1–8 A/B
  data B-A8 later reads): `bucket = "morning" if (WW + ordinal) % 2 == 0 else
  "evening"`.
- **Per-channel default times** — *arbitrary A/B-hypothesis defaults, NOT real
  posting times* (A-4: real times are filled by the human via mark-posted). Fixed,
  documented constants:

  | Channel | morning | evening |
  |---|---|---|
  | instagram | `09:00` | `18:00` |
  | youtube | `11:00` | `20:00` |
  | linkedin | `08:30` | `17:30` |

- **Slot string format:** `<week>/<bucket>/<HH:MM>`.

**Worked ground truth for `--week 2026-W27` (WW=27):**

| Channel | (WW+ord) | bucket | slot string |
|---|---|---|---|
| instagram | 27 (odd) | evening | `2026-W27/evening/18:00` |
| youtube | 28 (even) | morning | `2026-W27/morning/11:00` |
| linkedin | 29 (odd) | evening | `2026-W27/evening/17:30` |

The **identical** slot string is written to BOTH the PACKAGE `schedule_slot` field
and the QUEUE row `schedule_slot` field (computed once, written twice).

### 3.3 Package generation (`package.py` CLI) — B-P4 / B-P5 / B-P6 / B-P9

`python3 tools/marketing-loops/package.py <asset_dir> --week YYYY-Www [--queue PATH] [--publish-dir DIR]`

Ordered steps (all validation happens **before any write** — the operation is
**atomic**: on any error, zero package files are written and the queue is
untouched):

1. **`--week` format** (`^\d{4}-W\d{2}$`) → else exit 2.
2. **Asset precondition:** `<asset_dir>` exists, is a dir, has `meta.md` → else
   exit 2.
3. **Gate first (never bypass — B-P9).** Run `gate.gate_asset(<asset_dir>)`. If
   `ok=False` → print each cited reason to **stderr**, write nothing, exit **1**.
   (This re-uses the *exact* Sprint-002 function; the four conditions are frozen.)
4. **Channels** via `channels.channels_for_asset` (§3.5 of Sprint 002 — imported):
   no `Channels:` line, an unmapped platform token, or zero channels → exit 2.
5. **UTM precondition (why it lives here, not in the gate).** Validate the asset's
   Flywheel link via `utm.validate_asset(<asset_dir>)`. The gate's four conditions
   are frozen and do **not** include UTM (Sprint-002 pinned that); but package
   generation *must parse the `Flywheel target:` line anyway* — it is the only
   source of the destination base URL (`https://intel.terrem.in/markets`), and a
   `meta.md` campaign that disagrees with the folder slug is a real authoring bug
   that must not ship (story #1: "a wrong-UTM asset never ships"). So: if
   `validate_asset` returns violations (missing line, malformed query, wrong
   medium, campaign mismatch, unknown source) → exit **2**, cite the exact
   Sprint-001 violation code(s), write nothing.
6. **Manifest / attachments.** Read `<asset_dir>/render/manifest.json`. Absent,
   unparseable, or with an empty/absent `surfaces` list → exit 2 (a package with
   nothing to attach is not a valid package), write nothing. Otherwise
   `attachments` = the ordered list, in `surfaces[]` order, of
   `<asset_repo_relative>/render/<surface.png>` — POSIX-style forward-slash paths
   **relative to the repo root** (repo root resolved from `__file__`). The real
   assets and all fixtures resolve under the repo root, so these are stable and
   cwd-independent.
7. **Per-channel link.** For each channel `c`, build the per-channel UTM link by
   **canonically rebuilding** the query on the flywheel destination:
   `<scheme>://<host><path>?utm_source=<CHANNEL_SOURCE_MAP[c]>&utm_medium=social&utm_campaign=<campaign>`
   where `<scheme>://<host><path>` is taken from the validated flywheel URL and
   `<campaign>` = `utm.campaign_from_slug(<slug>)` (date-stripped slug). Canonical
   rebuild (not string-splice) makes the link byte-identical regardless of the
   base link's param order. Instagram → `utm_source=instagram`, YouTube →
   `youtube`, LinkedIn → `linkedin` (the frozen Sprint-001 map).
8. **Caption body per channel** via `captions.body_for` (§3.1). If any
   **to-be-packaged** channel (see step 9 for posted-skip) has body `None` →
   exit 2, name the asset + channel(s), write nothing. Final **caption** for a
   channel = `<body> + "\n\n" + <per-channel utm_link>` (exactly two newlines
   between body and link). Same authored body + same channel → byte-identical
   caption (B-P5).
9. **Queue merge + package files (the only writes; happen together, last).** Load
   the queue (`queue.load_queue`, default `content/publish-queue.json`). For each
   declared channel:
   - If an existing QUEUE row for `(slug, channel)` is **`posted`** → **skip**: do
     not overwrite its package file, do not alter its row; emit stdout
     `kept-posted <slug> <channel>` (no-regress / no-overwrite-of-posted, spec §7).
   - Otherwise (new pair, or existing `queued` row): build the row via
     `queue.new_row(slug, channel, week)` (so it uses the frozen `queue.ROW_KEYS`
     exactly), then set `schedule_slot` (§3.2) and `package_path` on it; **write**
     the PACKAGE file `<publish-dir>/<channel>.json` (default publish-dir
     `<asset_dir>/publish`); record `package_path` = that file's path,
     repo-relative (POSIX) when under the repo root, else its absolute resolved
     path. Emit stdout `packaged <slug> <channel>`.
   Merge the built rows into the queue with **package semantics** (a pure helper
   authored in `package.py`): new pair → append; existing `queued` → replace its
   `schedule_slot`/`package_path`/`week` with the freshly-computed values, keep
   `state="queued"`; existing `posted` → keep wholesale (the skip above). Write the
   queue deterministically via `queue.dumps`/`queue.write_queue` (sorted keys,
   `(slug, channel)` row order, single trailing newline). Exit **0**.

**PACKAGE file schema (§5.4 PACKAGE), serialized `json.dumps(..., sort_keys=True,
indent=2) + "\n"`:**

```json
{
  "schema_version": "1",
  "slug": "<content folder slug>",
  "channel": "instagram|youtube|linkedin",
  "utm_source": "instagram|youtube|linkedin",
  "utm_link": "https://intel.terrem.in/markets?utm_source=<src>&utm_medium=social&utm_campaign=<campaign>",
  "caption": "<authored body>\n\n<utm_link>",
  "attachments": ["content/<slug>/render/<png>", "..."],
  "schedule_slot": "<week>/<bucket>/<HH:MM>",
  "week": "YYYY-Www"
}
```

**Idempotency (B-P3 spirit).** Re-running the exact same `package.py` command
(same asset, `--week`, `--queue`, `--publish-dir`) → **byte-identical** PACKAGE
files, **byte-identical** queue file, identical stdout. Everything is derived from
the inputs; nothing is wall-clock.

**Real-asset ground truth (`--week 2026-W27`, using temp `--queue`/`--publish-dir`):**

- `content/2026-07-03-tgrera-enforcement-wave` → exit **0**; three PACKAGE files
  (`instagram.json`, `youtube.json`, `linkedin.json`); each with `schema_version
  "1"`, correct `utm_source`, per-channel `utm_link` (campaign
  `tgrera-enforcement-wave`), `attachments`
  `["content/2026-07-03-tgrera-enforcement-wave/render/chart-card.png"]`,
  `schedule_slot` per the §3.2 W27 table, `week "2026-W27"`; three QUEUE rows
  `state=queued` with `schedule_slot` + `package_path` now **non-null**.
- `content/2026-07-03-hyd-premium-vs-budget` → gate refuses → exit **1**, stderr
  cites `[missing-verdict, killed]`, **no** package files, **no** queue write.
  (The clean real-content refusal anchor — proves the gate is never bypassed
  without depending on any caption.)

### 3.4 Mark-posted (`mark_posted.py` CLI) — B-P7

`python3 tools/marketing-loops/mark_posted.py <slug> <channel> --posted-on YYYY-MM-DD --permalink URL [--queue PATH]`

- **`<channel>`** must be one of `{instagram, youtube, linkedin}` → else exit 2.
- **`--posted-on`** must match `^\d{4}-\d{2}-\d{2}$` **and** be a real calendar
  date (validated via `datetime.strptime` — parsing a supplied date, **never**
  `datetime.now()`) → else exit 2.
- **`--permalink`** must be non-empty after strip **and** match `^https?://` (a
  permalink is a URL) → else exit 2.
- **`--queue`** (default `content/publish-queue.json`) must exist and load as a
  valid QUEUE doc → else exit 2.
- **Row lookup:** find the row for `(slug, channel)`.
  - Not found → exit **2** (precondition: nothing to mark; message names the pair).
  - Found but `state != "queued"` (i.e. already `posted`) → exit **1** (domain
    refusal: "row is already posted; refusing to re-post"). No write.
  - Found and `state == "queued"` → set `state="posted"`, `posted_date=<--posted-on>`,
    `permalink=<--permalink>`; write the queue deterministically; stdout
    `posted <slug> <channel> <posted_on>`; exit **0**.
- **Intentionally NON-idempotent (contrast with enqueue/package).** A *second*
  mark-posted on the same row is refused at exit 1 by design — this is the
  no-double-post guard (B-P7 "refuse to mark posted a row that is not currently
  queued"), not a bug. Enqueue/package are idempotent; mark-posted is a one-way
  state transition.

### 3.5 `/loop-publish` skill (`.claude/skills/loop-publish/SKILL.md`) — B-P9

A skill doc mirroring `.claude/skills/loop-qa/SKILL.md` (YAML frontmatter with
`name` + `description`; numbered steps; an operator "verdict" section). It:

- Documents the flow: (1) run `package.py content/<slug> --week <YYYY-Www>` —
  which re-runs the gate and refuses a non-PASS/KILLED asset; (2) read the
  generated `content/<slug>/publish/<channel>.json` packages (caption + attachments
  + slot) and post **by hand** on each platform; (3) run `mark_posted.py <slug>
  <channel> --posted-on <date> --permalink <url>` for each channel after posting.
- States that the skill **never bypasses the gate** and **adds no taste
  judgement / no copy** — it cites the tools' exit codes and reasons verbatim
  (mirrors `loop-qa` step "adds no independent taste judgement").
- Maps exit codes: `0` success, `1` gate refusal (list cited reasons) / already-
  posted refusal, `2` precondition (missing caption, invalid UTM, absent manifest,
  bad args) — report the tool's message, do not guess or auto-fix.

### 3.6 Exit codes (match render / Sprint-001 / Sprint-002 convention)

- `0` — success (packages written + queue updated; or mark-posted transition done;
  idempotent re-run of `package.py` also 0).
- `1` — **domain failure**: `package.py` gate refusal (reasons on stderr, no
  write); `mark_posted.py` on an already-`posted` row (no write).
- `2` — **usage / precondition error**: malformed `--week`/`--posted-on`; missing
  asset/`meta.md`/`manifest`/`captions.md`-body; invalid Flywheel UTM; unmapped/zero
  channels; empty/non-URL permalink; missing/invalid queue for mark-posted; unknown
  channel arg; row-not-found for mark-posted. Message on stderr, **no write**, empty
  stdout.

## 4. States

- **Empty / first run:** `package.py` against a non-existent `--queue` creates a
  valid QUEUE doc; against an empty `--publish-dir` creates it (`mkdir -p`).
- **Success (package):** gate passes, UTM valid, manifest + captions present →
  N package files + N `queued` rows with `schedule_slot`/`package_path` non-null.
- **Success (mark-posted):** a `queued` row → `posted` with `posted_date` +
  `permalink`.
- **Gate refusal (package):** missing/non-PASS/failed-checks/KILLED → exit 1, cited
  reason(s), no write. (Real hyd → `[missing-verdict, killed]`.)
- **Missing caption:** `captions.md` absent / no body for a packaged channel →
  exit 2, named, **no write, never invented**.
- **Invalid UTM (package):** wrong medium / campaign mismatch / etc. → exit 2 with
  cited Sprint-001 code, no write.
- **Absent manifest / no surfaces:** exit 2, no write.
- **Idempotency:** re-run `package.py` on same inputs → byte-identical package
  files + queue + stdout; no duplicate `(slug, channel)` rows.
- **No-regress / no-overwrite of posted:** a pre-existing `posted` row for
  `(slug, channel)` survives a re-`package.py` unchanged, and its package file is
  **not** rewritten (`kept-posted`).
- **Mark-posted non-idempotent:** second mark-posted on the same row → exit 1, no
  write.
- **Offline:** no network; any network import is a defect.

## 5. Non-UI expectations (a11y / responsive / contrast do not apply)

Headless CLI + one skill doc. In place of keyboard/focus/ARIA/contrast/responsive:

- **Usability:** every refusal/error message is specific and recoverable — it
  names the asset, the channel, and the concrete fact (e.g. `no caption body for
  channel 'youtube' — add a caption:youtube or caption:all block to captions.md`;
  `Flywheel UTM invalid: [campaign-mismatch] ...`; `manifest.json not found at
  <path>`), never a bare "failed".
- **Runs from any cwd:** paths resolved from `__file__`; `<asset_dir>`, `--queue`,
  `--publish-dir` accept absolute or relative paths.
- **Import safety:** importing `captions`, `schedule`, `package`, `mark_posted`
  has no side effects and prints nothing.
- **Single source of truth:** channel↔source map imported from Sprint-001
  `utm.CHANNEL_SOURCE_MAP`; canonical channel order from the same; QUEUE schema
  constants/serialization from Sprint-002 `queue.py`; the gate from Sprint-002
  `gate.py`. No forks, no re-declared maps.

## 6. Security / privacy

- Stdlib only (`json`, `re`, `argparse`, `pathlib`, `datetime` for parsing the
  supplied `--posted-on` only — never `now()`, `urllib.parse` for building/parsing
  query strings only — never to fetch). No third-party deps. No network. No
  secrets. No personal data written. Untrusted inputs (`meta.md`, `manifest.json`,
  `captions.md`) → parse defensively; a malformed input is a cited exit-2 error,
  never a crash and never an invented value. No dependency on the globally-
  installed `pmp-gywd@5.0.0` npm package.
- `content/publish-queue.json` and `content/<slug>/publish/*.json` are tracked,
  non-secret artifacts. Tests write only to temp `--queue`/`--publish-dir` and
  never mutate real `content/` (except the committed real `captions.md`, which is
  source, not a test artifact).

## 7. Explicit non-goals (this sprint)

- **No analytics / CSV / scorecard** (Sprints 004–006).
- **No change to the four gate conditions** — `gate_asset` is imported and re-run
  verbatim; UTM validity remains a *package precondition*, not a gate condition.
- **No live posting APIs, no credentials, no OAuth** — mark-posted only records a
  human-supplied permalink. The API seam stays the `{queued, posted}` state
  machine (B-P8, already materialized in Sprint 002).
- **No modification** of `utm.py`, `gate.py`, `queue.py`, `channels.py`, or any
  `content/*` file other than adding the one real `captions.md`.
- **No marketing-copy generation** — captions are authored input; the tool only
  appends the UTM link.

## 8. Commands to run

```bash
cd /Users/prithviputta/Downloads/terrem-marketing-loops
TMPQ="$(mktemp -d)/queue.json"
TMPP="$(mktemp -d)/publish"

# Unit tests (all Sprint 001+002+003 must pass)
python3 -m unittest discover -s tools/marketing-loops/tests -v

# Real PASS asset -> 3 packages + 3 queued rows with slot+package_path -> exit 0
python3 tools/marketing-loops/package.py \
  content/2026-07-03-tgrera-enforcement-wave --week 2026-W27 \
  --queue "$TMPQ" --publish-dir "$TMPP" ; echo "exit=$?"
cat "$TMPP/instagram.json"   # utm_source instagram; slot 2026-W27/evening/18:00
cat "$TMPP/youtube.json"     # utm_source youtube;   slot 2026-W27/morning/11:00
cat "$TMPQ"                  # 3 rows, schedule_slot + package_path non-null

# Idempotency: re-run -> byte-identical packages + queue
shasum "$TMPP"/*.json "$TMPQ"
python3 tools/marketing-loops/package.py \
  content/2026-07-03-tgrera-enforcement-wave --week 2026-W27 \
  --queue "$TMPQ" --publish-dir "$TMPP" ; shasum "$TMPP"/*.json "$TMPQ"

# Gate never bypassed: real KILLED asset -> exit 1, no packages, no queue write
python3 tools/marketing-loops/package.py \
  content/2026-07-03-hyd-premium-vs-budget --week 2026-W27 \
  --queue "$TMPQ" --publish-dir "$TMPP" ; echo "exit=$?"

# Mark-posted: queued -> posted, then re-run refused (non-idempotent by design)
python3 tools/marketing-loops/mark_posted.py \
  2026-07-03-tgrera-enforcement-wave instagram \
  --posted-on 2026-07-04 --permalink https://instagram.com/p/xyz \
  --queue "$TMPQ" ; echo "exit=$?"
python3 tools/marketing-loops/mark_posted.py \
  2026-07-03-tgrera-enforcement-wave instagram \
  --posted-on 2026-07-04 --permalink https://instagram.com/p/xyz \
  --queue "$TMPQ" ; echo "exit=$? (expect 1: already posted)"

# No-regress: re-package after a post -> instagram kept-posted (package not rewritten)
python3 tools/marketing-loops/package.py \
  content/2026-07-03-tgrera-enforcement-wave --week 2026-W27 \
  --queue "$TMPQ" --publish-dir "$TMPP" ; echo "exit=$?"   # stdout: kept-posted ... instagram

# Import-safety: modules import silently
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); \
  import captions, schedule, package, mark_posted; \
  print(schedule.slot_for('2026-W27','instagram'))"   # -> 2026-W27/evening/18:00
```

## 9. Evaluator attack checklist (CLI, not Playwright)

Fixtures shipped under `tools/marketing-loops/fixtures/publish/` (each a full asset
folder). Required NEW fixtures + expected result:

| Fixture intent | Expected |
|---|---|
| `pkg-pass` — PASS, valid UTM, manifest 1 surface, `captions.md` `[all]` block, 3 channels (positive control) | exit 0; 3 packages; 3 queued rows w/ slot+package_path; caption = body + per-channel link |
| `pkg-multi-surface` — manifest with ≥2 surfaces | `attachments` is the ordered ≥2 repo-relative PNG list |
| `pkg-per-channel-caption` — `captions.md` has `[all]` + `[instagram]` override | instagram caption uses the override body; youtube/linkedin use `[all]` |
| `pkg-no-captions` — no `captions.md` | exit 2, names the channels lacking a body, **no package, no queue write** |
| `pkg-missing-channel-caption` — `captions.md` has only `[instagram]`, Channels include youtube | exit 2, names `youtube` (no `[all]` fallback), no write |
| `pkg-bad-utm` — gate PASS but Flywheel campaign mismatch (or wrong medium) | exit 2, cites the Sprint-001 code (`campaign-mismatch`/`wrong-medium`), no write |
| `pkg-no-manifest` — gate PASS but `render/manifest.json` absent | exit 2, no write |
| `pkg-empty-surfaces` — manifest present but `surfaces: []` | exit 2, no write |
| (reuse `killed`) — KILLED marker | gate refuses, exit 1, no package |
| (reuse `verdict-fail`) — verdict FAIL | gate refuses, exit 1, no package |

Adversarial probes the Evaluator should run:

1. **Real tgrera package** (temp queue + publish-dir, `--week 2026-W27`) → exit 0;
   assert 3 package files; each `schema_version "1"`; `utm_source` matches channel;
   `utm_link` carries `utm_source=<channel>&utm_medium=social&utm_campaign=tgrera-enforcement-wave`;
   `attachments == ["content/2026-07-03-tgrera-enforcement-wave/render/chart-card.png"]`;
   `schedule_slot` exactly per §3.2 W27 table; `caption` ends with the link after a
   blank line; 3 queue rows `queued` with matching `schedule_slot`+`package_path`.
2. **Idempotency** → re-run → `shasum` byte-identical for every package file AND the
   queue; identical stdout; no duplicate rows.
3. **Per-channel link correctness** → instagram/youtube/linkedin packages carry
   `utm_source=instagram|youtube|linkedin` respectively, all same campaign, all
   `utm_medium=social`.
4. **Gate never bypassed** → real hyd → exit 1, stderr `[missing-verdict, killed]`,
   temp queue **unchanged/not created**, publish-dir empty.
5. **Missing caption** → `pkg-no-captions` and `pkg-missing-channel-caption` → exit
   2, the missing channel named, **no** package file written, queue unchanged.
6. **Invalid UTM** → `pkg-bad-utm` → exit 2, Sprint-001 violation code cited, no
   write. (Proves UTM is enforced at publish without being folded into the gate.)
7. **Manifest guards** → `pkg-no-manifest` and `pkg-empty-surfaces` → exit 2, no
   write.
8. **Mark-posted happy path** → seed a queue with a `queued` (tgrera, instagram)
   row → mark-posted with valid date + `https://…` permalink → exit 0; row now
   `state=posted`, `posted_date`, `permalink` set; other rows untouched.
9. **Mark-posted refusals** → (a) same row again → exit 1 "already posted", no
   write; (b) `(slug, channel)` not in queue → exit 2; (c) empty or
   non-`http(s)://` permalink → exit 2; (d) malformed `--posted-on` (`2026-7-4`,
   `2026-13-40`) → exit 2. Each writes nothing.
10. **No-regress / no-overwrite** → after posting (tgrera, instagram),
    re-run `package.py` → stdout `kept-posted … instagram`, the instagram package
    file's mtime/bytes unchanged, the posted row intact; youtube/linkedin
    re-packaged idempotently.
11. **Cross-command regression (Sprint-002 stays passing)** → `enqueue.py` (creates
    null-slot rows) → `package.py` (fills slot+package_path) → `enqueue.py` again →
    the slot+package_path set by package.py **survive** (merge_rows keeps the queued
    row wholesale); final queue byte-stable.
12. **Import safety + determinism source** → `import captions, schedule, package,
    mark_posted` prints nothing; `schedule.slot_for('2026-W27','instagram') ==
    '2026-W27/evening/18:00'`; channel map is the imported Sprint-001
    `CHANNEL_SOURCE_MAP` (no fork).
13. **No network / no wall-clock** → grep the new sources for `datetime.now`,
    `requests`, `urlopen`, `socket`, network `urllib` → none (only
    `datetime.strptime` for `--posted-on` parsing and `urllib.parse` for query
    handling are permitted; assert those are the only hits).
14. **Frozen modules untouched** → `git`/diff shows `utm.py`, `gate.py`,
    `queue.py`, `channels.py` unchanged; the full Sprint 001+002 unit suite still
    passes.

## 10. Definition of done

- `captions.py` parses the marker-delimited `captions.md`, resolves per-channel
  body with `[channel]→[all]` fallback, and returns `None` (never a fabricated
  body) when absent; malformed blocks raise `ValueError`; no import side effects.
- `schedule.py` `slot_for(week, channel)` is pure, wall-clock-free, matches the
  §3.2 formula, and reproduces the W27 worked table exactly.
- `package.py` runs the frozen gate (refuse=1), validates UTM/channels/manifest/
  captions as exit-2 preconditions, and on success writes N deterministic PACKAGE
  files + updates N QUEUE rows (`schedule_slot`+`package_path`) atomically and
  idempotently, skipping/keeping `posted` rows without overwriting.
- `mark_posted.py` transitions `queued`→`posted` with validated `--posted-on` +
  `--permalink`, refuses non-`queued` rows (exit 1) and bad args/rows (exit 2),
  writes deterministic queue JSON, and is intentionally non-idempotent.
- `.claude/skills/loop-publish/SKILL.md` documents the gate→package→post→mark-posted
  flow, invokes the CLIs, never bypasses the gate, adds no copy/taste — mirroring
  `loop-qa`.
- The real `content/2026-07-03-tgrera-enforcement-wave/captions.md` carries an
  asset-authored (verbatim `Hook:`) caption body; real tgrera packages at exit 0
  with the §3.3 ground-truth values; real hyd is refused at exit 1 with
  `[missing-verdict, killed]` and no write.
- Fixtures for every §9 row shipped under `tools/marketing-loops/fixtures/publish/`.
- Unit tests prove caption resolution + missing-body error, schedule determinism,
  package build/attachments/link/caption/idempotency/no-regress, mark-posted
  transition + all refusals, and the cross-command regression; all pass alongside
  the untouched Sprint 001+002 suites.
- Evidence (command output, exit codes, before/after `shasum`, sample PACKAGE +
  QUEUE JSON, grep-clean for wall-clock/network) logged in `generator_trace.log`.
```
