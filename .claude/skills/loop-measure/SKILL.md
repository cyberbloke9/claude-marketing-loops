---
name: loop-measure
description: Loop 5 (measure) — compile the weekly scorecard metrics/YYYY-Www.md from platform + site analytics CSV exports by invoking scorecard.py, then feed decisions back into the other loops. The tool never estimates or invents a number. Args: an ISO week and whichever CSV exports exist. Run weekly after exporting channel analytics.
---

# Loop 5 — Measure (mechanical scorecard compile, up to the data boundary)

This layer is **mechanical, not hand-walked**. You do **not** hand-write the
scorecard tables, hand-compute WRR, invent a metric, or fill a cell from memory.
You invoke the analytics CLI and consume its deterministic Markdown output. There
is **no scraping and no platform API** — inputs are operator-provided CSV exports
only.

Inputs: the ISO week `YYYY-Www`, whichever of the four CSV exports exist
(Instagram / YouTube / LinkedIn platform exports + the site-analytics export),
and optionally `content/publish-queue.json` for the posting-time A/B table.

## Steps

1. **Compile the scorecard.** Run the compiler with the week + whatever exports
   you have:

   ```
   python3 tools/marketing-loops/scorecard.py --week <YYYY-Www> \
     [--instagram FILE] [--youtube FILE] [--linkedin FILE] [--site FILE] \
     [--content-dir content] [--queue content/publish-queue.json] \
     [--out metrics/<YYYY-Www>.md | --stdout]
   ```

   By default it writes `metrics/<week>.md`. It reuses the frozen `ingest`
   pipeline to parse + join the CSVs, computes WRR + flywheel + craft diagnostics
   + the A/B table + decisions, and appends a `## Missing data` section listing
   **every** blanked input and why. The output is byte-deterministic (same
   inputs → identical file); safe to re-run weekly.

2. **Read the scorecard + the Missing-data section.** Open the written
   `metrics/<week>.md`. Every blank cell is intentional and is explained under
   `## Missing data`. Post nothing and edit no numbers — the file is the record.

3. **Feed decisions back.** The `## Decisions fed back` section fills only what
   the data supports (the hook winner / retire-candidate by measured clicks). The
   qualitative bullets (Loop 1 signal resonance, Loop 3 format changes) and the
   8-week hard-stop verdict are **operator-authored** — the tool leaves them blank
   and lists them under Missing data. Add your qualitative judgement by hand if
   you choose; the tool never fabricates it.

## The two distinct failure modes — never conflate them

- **Malformed / truncated CSV → exit 2, NO scorecard written.** An unparseable
  file, a missing required header, a wrong column count, a truncated row, a
  non-numeric numeric cell, or a blank join column is a **corrupt input**. The
  tool rejects it with a cited message on stderr and writes **no** `metrics/*.md`
  (corruption never silently becomes a blank cell). Fix the export and re-run.
- **Absent input → exit 0, blank cell + Missing-data entry.** A whole source you
  did not provide, or a value genuinely absent from an otherwise-valid CSV, is
  **left blank** and enumerated under `## Missing data`. This is a valid partial
  scorecard, not an error.

## The never-invent rule (hard)

The tool **never** estimates, interpolates, defaults, or zero-fills a metric. A
`0` in a cell is only ever a genuinely present `0`. **WRR is filled only when all
three components** (returning viewers + digest opens + returning site visitors
from social) **are present** — if any is absent, WRR is blank and each missing
component is listed; a partial sum is forbidden (it would be an invented number).

## Exit codes — report the tool's message, never guess or auto-fix

- `0` — success (scorecard written / printed), including partial and empty runs.
- `1` — **intentionally unused** (there is no domain verdict on well-formed
  input; missing inputs and wrong-UTM are handled inside a successful scorecard).
- `2` — usage / precondition error, cited on stderr, **no scorecard written**:
  bad `--week`; a provided export path not found; a corrupt CSV (see above); a
  `--queue` path not found or an invalid queue document; `--out` + `--stdout`
  given together.
