# TERREM Marketing Loops

An evidence-based, agent-automated marketing system for [TERREM](https://intel.terrem.in) — Indian real-estate intelligence.

Every rule in this repo traces to a verified source in `RESEARCH.md`. Unverified assumptions are marked `[hypothesis — A/B test]` and get burned down by the measure loop.

## The system

| Loop | Cadence | Input → Output |
|---|---|---|
| 1. Research | Weekly + event-triggered | Market/platform signals → `signals/YYYY-MM-DD.md` |
| 2. Persona | Monthly | Surveys + audience language → `personas/` |
| 3. Creation | 2–3 assets/week | Signal × hook × template → `content/YYYY-MM-DD-<slug>/` |
| 4. Design/QA | Per asset | Asset vs `brand/qa-checklist.md` → pass/block |
| 5. Publish/Measure | Weekly | Platform metrics → `metrics/YYYY-Www.md` → feeds Loops 1–2 |

North star: **WRR — Weekly Returning Readers** (retention, not reach). See `PLAN.md` §0 for why.

## Layout

```
PLAN.md                  Five-loop system plan + rollout phases
RESEARCH.md              Verified evidence base (with refuted-claims blacklist)
brand/brand-kit.md       Voice, typography, color, chart rules
brand/qa-checklist.md    Loop 4 mechanical gate — nothing publishes without passing
personas/personas.md     The Upgrader & The Investor (ANAROCK-sourced)
personas/hook-bank.md    Pain-point → hook mapping, by psychological mechanism
signals/                 Loop 1 output (TEMPLATE.md defines the format)
content/                 Loop 3 output (TEMPLATE.md defines the asset folder)
metrics/                 Loop 5 scorecards (TEMPLATE.md defines the KPI stack)
.claude/skills/          /loop-research /loop-persona /loop-create /loop-qa /loop-measure
```

## Running the loops

From this directory in Claude Code:

- `/loop-research` — generate this week's ranked signals (also runs on schedule)
- `/loop-create <signal>` — draft the Weekly Ledger assets for a signal
- `/loop-qa <content-folder>` — run the mechanical design gate
- `/loop-measure` — compile the weekly scorecard from exported metrics
- `/loop-persona` — monthly persona/hook-bank refresh

## Rollout status

- [x] Phase 0 — brand kit (real product tokens), templates, hook bank v1, repo scaffolding
- [x] Phase 0 — analytics plumbing (UTM verifier + publish layer + weekly scorecard compiler)
- [x] Phase 1 started — first signals run (2026-07-03); Ledger #1 KILLED at QA (synthetic-data provenance); TGRERA reactive take drafted + QA PASS; Ledger on public data queued (ANAROCK vs PropEquity)
- [ ] Phase 2 (weeks 6–9) — scorecards + posting-time A/B + reactive lane
- [ ] Phase 3 (week 10+) — City Leaderboard + SEO locality pages (Trulia engine)

## Asset Renderer + QA Gate

A deterministic, no-network CLI toolchain under `tools/marketing-render/` renders an
authored asset folder (`content/<slug>/`) into brand-locked PNGs plus a `manifest.json`,
then mechanically validates the PNGs + specs against `brand/qa-checklist.md`, emitting a
machine-readable `qa-verdict.json` and a human verdict block in the asset's `meta.md`.

### Render

Render an asset folder to PNGs and a manifest:

```
python3 tools/marketing-render/render.py content/2026-07-03-tgrera-enforcement-wave
```

Writes `content/2026-07-03-tgrera-enforcement-wave/render/{chart-card.png, manifest.json}`.

### Validate

Validate the rendered asset against the QA checklist:

```
python3 tools/marketing-render/validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on 2026-07-04
```

Writes `render/qa-verdict.json` and appends the verdict block to `meta.md`.
Exit `0` = PASS, `1` = FAIL, `2` = usage/precondition error.

### End-to-end acceptance

Prove the whole gate in one run (TGRERA render + validate PASS; every committed
adversarial fixture FAILs on its named check; the positive-control fixture PASSes):

```
python3 tools/marketing-render/acceptance.py --checked-on 2026-07-04
```

Exit `0` iff the full gate holds.

### Determinism & no network

Fonts are vendored under `tools/marketing-render/fonts/` (Inter, SIL OFL, `OFL.txt`
present). No network is accessed at render or validate time; re-rendering the same input
yields pixel-identical PNGs (R8). The `--checked-on` date only affects the `checked_on`
field of `qa-verdict.json`, never the PNG bytes.

For agent-based validation, the `/loop-qa` skill wraps `validate.py`, consuming
`qa-verdict.json` mechanically.

## Publish layer (Gap 2)

A deterministic, no-network CLI toolchain under `tools/marketing-loops/` assembles a
QA-passed asset into per-channel publish packages and tracks them in a single
machine-readable queue up to (but not across) the live-posting-API boundary. There
are no posting APIs and no platform credentials; a human posts manually and records
the permalink back into the queue.

Verify UTM hygiene across assets (spec §5.0):

```
python3 tools/marketing-loops/verify_utm.py content
```

Reports `OK <slug>` or the specific violation per asset. Exit `0` iff every asset's
Flywheel UTM link matches `utm_source=<channel>&utm_medium=social&utm_campaign=<date-stripped-slug>`;
exit `1` if any asset is flagged; exit `2` on a path error.

Gate + enqueue a publishable asset (spec §5.1):

```
python3 tools/marketing-loops/enqueue.py content/<slug> --week 2026-W27 --queue content/publish-queue.json
```

The **gate has four refusal conditions** — the asset is refused (nonzero exit, cited
reason, no write) if any of: (a) `render/qa-verdict.json` is absent/unreadable;
(b) `verdict` is not exactly `PASS`; (c) `failed_checks` is non-empty; (d) `meta.md`
carries a `QA: KILLED` marker.

Generate per-channel PACKAGE files (final caption = authored `captions.md` body + the
correct per-channel UTM link; attachment PNG paths from `manifest.json`; a deterministic
schedule slot) and record a manual post:

```
python3 tools/marketing-loops/package.py content/<slug> --week 2026-W27 --publish-dir content/<slug>/publish
python3 tools/marketing-loops/mark_posted.py <slug> instagram --posted-on 2026-07-06 --permalink https://instagram.com/p/…
```

**QUEUE as the API seam:** `content/publish-queue.json` carries a `schema_version`, a
fixed `state` enum `{queued, posted}`, and per-row nullable `posted_date` / `permalink`,
so a future live-posting adapter flips state and fills fields without reshaping the file.
The `/loop-publish` skill (`.claude/skills/loop-publish/`) documents the operator flow and
never bypasses the gate.

## Analytics scorecard (Gap 3)

Ingest operator-provided platform + site analytics CSV exports into the weekly
scorecard `metrics/YYYY-Www.md`, faithful to `metrics/TEMPLATE.md` with an appended
Missing-data section (spec §5.2):

```
python3 tools/marketing-loops/scorecard.py --week 2026-W27 \
    --instagram ig.csv --youtube yt.csv --linkedin li.csv --site site.csv \
    --content-dir content --queue content/publish-queue.json --out metrics/2026-W27.md
```

Two distinct handling paths, never conflated:

- **Malformed / truncated CSV → exit `2`, no scorecard.** A missing required header, a
  wrong-column-count row, a truncated row, a non-numeric metric, or a blank join key
  aborts with the offending file + reason and writes nothing (corruption never becomes
  a blank cell). `ingest.py` is the underlying validator.
- **Absent input → blank cell + Missing-data listing, exit `0`.** A whole source or a
  single value that is simply not provided is left blank and enumerated under
  "Missing data". The tool never estimates, defaults, or zero-fills.

**WRR no-partial-sum rule:** the north-star WRR is filled only when all three components
(returning viewers + digest opens + returning social visitors) are present; if any is
absent, WRR is left blank and each missing component is listed — a partial sum is
forbidden (it would be an invented number). The `/loop-measure` skill
(`.claude/skills/loop-measure/`) wraps `scorecard.py` and states this rule.

## Cross-gap acceptance

Prove both gaps in one deterministic, no-network run — every UTM-violation, publish-gate,
malformed-CSV, and missing-input fixture reaches its expected exit on its cited reason,
plus an end-to-end seam chain (`verify_utm → enqueue → package → mark_posted → scorecard`)
on the real TGRERA asset where the scorecard's posting-time A/B bucket is driven by the
`schedule_slot` the publish layer wrote:

```
python3 tools/marketing-loops/acceptance.py
```

Exit `0` iff both gaps hold. The runner redirects every write into a throwaway temp dir,
so it never dirties the repo (`git status --porcelain` shows no publish queue, no
`content/*/publish/`, no new `metrics/`).
