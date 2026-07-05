# Contract — Sprint 006: Acceptance runner + adversarial fixture suite + README rollout

> Closes the marketing-loops build (spec §11, final sprint). Delivers one
> deterministic, no-network **end-to-end acceptance runner** over **both gaps**
> (Gap 2 publish + Gap 3 analytics), invoking the real CLIs as subprocesses
> exactly as an operator / the `/loop-publish` + `/loop-measure` skills do, plus
> the `README.md` rollout-status update (check the Phase-0 analytics-plumbing box)
> and documentation of both toolchains. Mirrors the DNA of
> `tools/marketing-render/acceptance.py` (Sprint-005 renderer runner).
>
> **This sprint writes ONE new runner + README/doc changes. It invents no metric,
> defines no new JSON schema, adds no CLI behavior, and never modifies a
> Sprint-001..005 module** — it only *invokes* the frozen CLIs and *asserts* their
> contracted behavior. The Sprint-001..005 fixture suite **is** the adversarial
> suite; new fixtures are added only if the cross-gap seam chain needs one.
>
> This is a **headless CLI + fixture** deliverable — there are **no routes,
> screens, components, DOM, or Playwright paths**. Verification is exact CLI
> invocations + exit codes + stdout/stderr substrings + **byte-for-byte
> golden-Markdown** (scorecards) + **path-independent JSON-field invariants**
> (generated publish artifacts). §7 states why byte-comparison is NOT used on
> generated publish artifacts.

## 1. Scope (this sprint only)

Deliver the cross-gap acceptance layer:

- A single runner `tools/marketing-loops/acceptance.py` that:
  1. runs a **normative expectation table** over the committed Sprint-001..005
     fixtures — every UTM-violation, publish-gate-refusal, malformed-CSV, and
     missing-input fixture reaches its **expected exit code on its specific cited
     reason** (not merely "some nonzero exit");
  2. proves an **end-to-end cross-gap seam chain** on the real PASS asset
     `content/2026-07-03-tgrera-enforcement-wave`: `verify_utm → enqueue →
     package → mark_posted → scorecard`, where the scorecard's Posting-time A/B
     table reads the `schedule_slot` **from the queue the publish layer generated**
     (this is what makes it end-to-end over both gaps, not two separate proofs);
  3. asserts **table coverage** — every committed fixture directory in the three
     fixture families (UTM assets, `fixtures/publish/`, `fixtures/metrics/`) is
     named by exactly one expectation-table row, so no fixture is silently
     unchecked (mirrors render `acceptance.py` `table_coverage_error`);
  4. exits `0` **iff** the entire contract holds; on any unmet row, exits `1`
     with the first unmet row cited; usage error exits `2`.
- The `README.md` update: check the `[ ] Phase 0 — analytics plumbing` box and add
  a **Publish layer** and **Analytics scorecard** section documenting both
  toolchains + the acceptance command (currently only the renderer is documented).
- Unit tests `tools/marketing-loops/tests/test_acceptance.py` over the runner's
  **pure decision logic** (row evaluation, table coverage, invariant checks) in
  isolation from subprocess timing.

**Explicitly OUT of scope:** any change to `render.py`/`validate.py`/`measure.py`/
`utm.py`/`verify_utm.py`/`gate.py`/`queue.py`/`channels.py`/`enqueue.py`/
`captions.py`/`schedule.py`/`package.py`/`mark_posted.py`/`csvspec.py`/
`assetmap.py`/`ingest.py`/`scorecard.py`; any new metric, schema, or CLI flag on a
frozen tool; live posting APIs; network of any kind.

## 2. Files created / affected

New, under `tools/marketing-loops/`:

- `acceptance.py` — the cross-gap runner + its pure decision logic. Paths resolved
  from `__file__` (runs from any cwd). Stdlib only (`argparse`, `json`,
  `subprocess`, `sys`, `pathlib`, `shutil`, `tempfile`, `re`, `hashlib`). No
  `datetime` of any kind (no wall-clock); no network import.
- `tests/test_acceptance.py` — unit tests over the pure logic + a smoke test that
  the runner itself exits `0`.
- (Only if the seam chain needs it) a minimal fixture under
  `tools/marketing-loops/fixtures/acceptance/` — CSVs whose `utm_campaign` =
  `tgrera-enforcement-wave` so the chain's scorecard can place the real asset.
  Reuse `fixtures/metrics/full/{ig,yt,li,site}.csv` if they already suffice (they
  carry the `tgrera-enforcement-wave` campaign). **No fixture may live under
  `content/` or the real `metrics/`.**

Affected:

- `README.md` — Phase-0 box checked; two new documentation sections (§6 below).

**Frozen — must NOT be edited** (verified by the Evaluator via mtime + content):
every `.py` under `tools/marketing-loops/` except the new `acceptance.py` /
`tests/test_acceptance.py`; everything under `tools/marketing-render/`; every real
`content/<slug>/` asset; `metrics/TEMPLATE.md`; all Sprint-001..005 fixtures
(reused read-only).

## 3. The runner — behavior

### 3.1 Invocation & exit taxonomy

```
python3 tools/marketing-loops/acceptance.py [--verbose]
```

- Exit `0` — every expectation-table row met **and** the cross-gap seam chain held
  **and** table coverage is exact. Prints a per-row `PASS/FAIL` report then
  `ACCEPTANCE: PASS (<met>/<total> expectations met)`.
- Exit `1` — one or more rows unmet, or the chain failed, or coverage is
  incomplete. Prints the report, then `ACCEPTANCE: FAIL (<met>/<total> …) — first
  unmet: <reason>`.
- Exit `2` — the runner's own usage/precondition error (a referenced fixture
  directory is missing, a frozen CLI file is absent). Message on stderr.

`--verbose` echoes each invoked CLI's stdout/stderr indented under its row; the
terse row summary is unchanged. Determinism: two runs of `acceptance.py` print an
identical report (row ordering is the table's fixed order; the chain steps are a
fixed sequence). No output field is derived from the wall clock.

### 3.2 All mutable writes redirected to a throwaway temp dir

The runner reads real assets and fixtures **in place** but redirects **every**
CLI write into a fresh `tempfile.mkdtemp()` working area, and removes it on exit
(success or failure). Specifically:

- `enqueue.py` / `package.py` / `mark_posted.py` are always passed
  `--queue <TMP>/publish-queue.json`; `package.py` is passed
  `--publish-dir <TMP>/publish/<slug>`.
- `scorecard.py` is always passed `--out <TMP>/<name>.md` (never the default
  `metrics/` path).

**Hard invariant (Evaluator will check):** after a full run, `git status --porcelain`
shows **no** change to `content/publish-queue.json` (it must not exist or be
untouched), no change under any real `content/<slug>/publish/`, and no new/changed
file under the real `metrics/`. The runner never dirties the repo.

### 3.3 Normative expectation table (cited-reason, not "some FAIL")

Each row carries `{fixture, cli, args, expected_exit, expected_reason_substring}`.
A FAIL/refusal row is met **only** when the exit code matches **and** the cited
reason substring appears in the CLI's stderr (or the emitted verdict), enforcing
that the **named** condition fired. The table below is normative; the runner reads
the real emitted strings at run time. Reason substrings are illustrative of the
frozen CLIs' already-shipped messages — the Generator pins each to the exact
substring the frozen CLI emits (confirmed by running it), and if a frozen message
differs, the table matches the **frozen** message (the runner never asks a frozen
CLI to change).

**Gap 0 — UTM verifier (`verify_utm.py <asset>`):**

| fixture (under `fixtures/`) | expected_exit | cited reason |
|---|---|---|
| `2026-07-03-valid-asset` | 0 | `OK` |
| `2026-07-03-wrong-medium` | 1 | wrong medium |
| `2026-07-03-campaign-mismatch` | 1 | campaign ≠ slug |
| `2026-07-03-unknown-source` | 1 | unknown source |
| `2026-07-03-absent-source` | 1 | source absent/missing |
| `2026-07-03-malformed-query` | 1 | malformed query |
| `2026-07-03-missing-line` | 1 | missing flywheel line |
| `2026-07-03-multi-defect` | 1 | ≥2 cited codes |

**Gap 2 — publish gate + enqueue (`enqueue.py <asset> --week 2026-W27 --queue <TMP>`):**

| fixture (under `fixtures/publish/`) | expected_exit | cited reason | write? |
|---|---|---|---|
| `pass-one-channel` | 0 | enqueued (queued row written) | yes |
| `pass-three-channels` | 0 | 3 queued rows, canonical order | yes |
| `missing-verdict` | 1 | qa-verdict.json absent | **no** |
| `verdict-fail` | 1 | verdict != PASS | **no** |
| `failed-checks-nonempty` | 1 | failed_checks non-empty | **no** |
| `killed` | 1 | KILLED marker | **no** |
| `missing-verdict-and-killed` | 1 | first-cited refusal | **no** |
| `unparseable-verdict` | 1 or 2 (frozen behavior) | verdict unreadable | **no** |
| `no-channel` / `unmapped-channel` | 2 | zero/unmapped channels | **no** |

For every refusal row the runner additionally asserts **no queue write** — the
`<TMP>` queue file is absent (or unchanged from the prior state) after the refusal.

**Gap 2 — package + mark-posted (on a passing fixture, into `<TMP>`):**

| step / fixture | expected_exit | assertion |
|---|---|---|
| `package.py pkg-pass --week 2026-W27` | 0 | per-channel PACKAGE JSON written; `utm_link` correct per channel; `attachments` = manifest PNG order |
| `package.py pkg-no-captions` | 2 | `no captions.md` cited; no write |
| `package.py pkg-missing-channel-caption` | 2 | missing caption body cited; no write |
| `package.py pkg-bad-utm` | 2 | invalid Flywheel UTM cited; no write |
| `package.py pkg-empty-surfaces` | 2 | empty surfaces cited; no write |
| `package.py pkg-no-manifest` | 2 | manifest absent cited; no write |
| `mark_posted.py <slug> instagram --posted-on 2026-07-06 --permalink https://…` (row queued) | 0 | row → `posted`, date + permalink recorded |
| `mark_posted.py … instagram …` (already posted) | **1** | non-queued row refused; no write |
| `mark_posted.py … instagram --permalink "" …` | **2** | empty permalink refused (usage); no write |
| `mark_posted.py … <unknown-channel> …` | **2** | unknown channel (usage); no write |
| `mark_posted.py <missing-slug> instagram …` | **2** | row not found (usage); no write |

(mark-posted `1` vs `2` are **distinct rows** — the frozen CLI returns `1` only for
the non-queued/already-posted domain refusal, `2` for every usage error.)

**Gap 3 — analytics rejection vs missing-input (`scorecard.py --week 2026-W27 --out <TMP>/x.md …`):**

| fixture (under `fixtures/metrics/`) | expected_exit | assertion |
|---|---|---|
| `truncated/site.csv` | 2 | cited file+reason; **`<TMP>/x.md` absent** |
| `wrong-header/site.csv` | 2 | missing required header; **no scorecard** |
| `wrong-colcount/ig.csv` | 2 | wrong column count; **no scorecard** |
| `non-numeric/ig.csv` | 2 | non-numeric metric; **no scorecard** |
| `full/` (all sources) | 0 | byte-equal `expected/full.md` |
| empty (no sources) | 0 | byte-equal `expected/empty.md` |
| `wrr-partial/site.csv` | 0 | byte-equal `expected/wrr-partial.md`; **grep the output for `147`, `252`, `295` → none** (no forbidden partial sum) + `WRR component … absent` present |
| `wrong-utm/` | 0 | byte-equal `expected/wrong-utm.md`; wrong-UTM asset flagged in Missing data |
| `unmatched/` | 0 | byte-equal `expected/unmatched.md` |

The full/empty/wrr-partial/wrong-utm/unmatched scorecards are **path-independent**
(proven in Sprint 005), so byte-golden comparison against
`fixtures/metrics/expected/<name>.md` is safe even when written to a `<TMP>/--out`.

### 3.4 Cross-gap seam chain (the "both gaps" proof)

On the real PASS asset `content/2026-07-03-tgrera-enforcement-wave` (Channels: IG,
YT, LinkedIn; Flywheel campaign `tgrera-enforcement-wave`; captions.md present;
verdict PASS), all writes into `<TMP>`, week fixed at **`2026-W27`**:

1. `verify_utm.py <tgrera>` → exit `0` (`OK`).
2. `enqueue.py <tgrera> --week 2026-W27 --queue <TMP>/q.json` → exit `0`; `<TMP>/q.json`
   has 3 rows `(instagram, linkedin, youtube)` all `state=queued`, sorted by
   (slug, channel).
3. `package.py <tgrera> --week 2026-W27 --queue <TMP>/q.json --publish-dir <TMP>/pub`
   → exit `0`; three PACKAGE JSONs written; **invariant assertions** (per §7,
   parsed from JSON — NOT byte-golden):
   - `instagram.utm_link` contains `utm_source=instagram&utm_medium=social&utm_campaign=tgrera-enforcement-wave`;
     `youtube.utm_link` → `utm_source=youtube…`; `linkedin.utm_link` → `utm_source=linkedin…`;
   - each `caption` = authored body (byte-equal across runs) + its channel UTM link;
   - `attachments` equals the manifest surface PNG order (repo-relative);
   - the generated queue's `schedule_slot` values equal the deterministic
     `schedule.slot_for(2026-W27, channel)` — i.e. `2026-W27/evening/18:00`
     (instagram), `2026-W27/morning/11:00` (youtube), `2026-W27/evening/17:30`
     (linkedin) (these match `fixtures/metrics/full/queue.json`).
4. `mark_posted.py 2026-07-03-tgrera-enforcement-wave instagram --posted-on 2026-07-06
   --permalink https://instagram.com/p/EXAMPLE --queue <TMP>/q.json` → exit `0`; the
   instagram row is `posted` with the date + permalink; the other two remain
   `queued`.
5. `scorecard.py --week 2026-W27 --queue <TMP>/q.json --instagram … --youtube …
   --linkedin … --site … --content-dir <content-root-with-tgrera> --out <TMP>/s.md`
   → exit `0`; the Posting-time A/B table's **instagram bucket reflects the
   `schedule_slot` the publish layer wrote into `<TMP>/q.json`** (the seam): the
   runner parses the slot from the generated queue and asserts the same bucket
   governs the scorecard's instagram A/B row. This is the load-bearing cross-gap
   assertion — the scorecard consumes the publish layer's output, not a fixture
   queue.
6. **Idempotency:** re-run steps 2–3 → exit `0`, queue still has exactly 3 rows
   (no duplicates), the instagram row stays `posted` (no regression to `queued`).

If any step's exit code or invariant fails, the chain fails and the runner exits
`1` citing the failing step.

### 3.5 Table coverage

Before running, the runner computes, for each fixture family, the set of committed
fixture directories on disk and the set named by table rows, and fails
(`ACCEPTANCE: FAIL`, exit `1`) if any on-disk fixture is unnamed or any table row
names a missing directory. This guarantees a hostile Evaluator cannot drop in an
unchecked fixture, and that a deleted fixture surfaces immediately.

## 4. States that must exist

- **Success:** every row met + chain held + coverage exact → exit `0`, `ACCEPTANCE: PASS`.
- **Any single failure:** one row / chain step / coverage gap → exit `1`, first
  unmet reason cited, full report still printed (no early abort that hides later rows).
- **Runner precondition error:** a referenced fixture dir or frozen CLI file
  missing → exit `2`, stderr message, no partial "PASS".
- **Clean repo after run:** temp dir removed; `git status --porcelain` clean w.r.t.
  `content/publish-queue.json`, real `content/*/publish/`, real `metrics/`.

## 5. Security / determinism / hygiene

- No network import anywhere (`requests`/`urllib` fetch/`socket`/`http`); the
  runner is a pure subprocess orchestrator. `grep -nE 'requests|urlopen|socket|http\\.client|urllib\\.request' acceptance.py` → clean.
- No `datetime`/wall-clock in the runner or its output. `grep -n 'datetime\\|time\\.' acceptance.py` → clean (only `subprocess`/`hashlib`/`tempfile` timing internals, none surfaced in output).
- No secret, token, or `.env` value introduced. No dependency on `pmp-gywd@5.0.0`
  or any npm/global resource.
- Determinism: identical report across repeated runs; the runner sorts fixture
  sets and iterates the fixed table order.
- Frozen-module integrity: the runner imports **nothing** from the frozen tools
  except by invoking them as subprocesses (it may `import` a frozen module only to
  read a documented constant such as `schedule.slot_for` for the seam assertion —
  read-only, no mutation, and the Generator discloses any such import in the trace).

## 6. README update (verbatim scope)

- Change `- [ ] Phase 0 — analytics plumbing (UTM scheme, per-channel dashboards)`
  to `- [x]` and reword to reflect what shipped (UTM verifier + publish layer +
  weekly scorecard compiler), without claiming dashboards that were a non-goal.
- Add a **"Publish layer (Gap 2)"** section: the `verify_utm.py` / `enqueue.py` /
  `package.py` / `mark_posted.py` commands, the gate's four refusal conditions, the
  QUEUE-as-API-seam note, and the `/loop-publish` skill pointer.
- Add an **"Analytics scorecard (Gap 3)"** section: the `ingest.py` / `scorecard.py`
  commands, the malformed-CSV(exit 2) vs missing-input(blank + Missing-data)
  distinction, the WRR no-partial-sum rule, and the `/loop-measure` skill pointer.
- Add the **acceptance** command:
  `python3 tools/marketing-loops/acceptance.py` → exit `0` iff both gaps hold.
- Every README claim must be reproducible by the stated command. No
  "production-ready"/"complete"/"polished" language.

## 7. Verification strategy — why generated artifacts are NOT byte-compared

`package.py._repo_relative()` stores a path **repo-relative when under the repo
root, else absolute-resolved**. Because the runner writes packages/queue into a
temp dir **outside** the repo, the QUEUE's `package_path` field is an **absolute
temp path** — non-stable across machines/runs. Therefore:

- **Generated publish artifacts** (queue, packages, written into `<TMP>`) are
  verified by **path-independent JSON-field invariants** (per-channel `utm_link`,
  `caption` bytes, `attachments` list, `schedule_slot` value, `state` transitions,
  no-duplicate-rows on re-run) — **never** whole-file byte-equality. The
  byte-stability of captions/utm_link is asserted by re-running the same step and
  comparing those fields, not the file.
- **Scorecards from fixed fixtures** are path-independent (Sprint-005 proven) and
  ARE byte-golden-compared against `fixtures/metrics/expected/<name>.md`.

This split is the whole reason the runner is deterministic under a hostile
Evaluator. It must be stated in the runner's module docstring.

## 8. Commands to run (Evaluator)

```
# 1. The runner itself — the whole contract in one exit code:
python3 tools/marketing-loops/acceptance.py            # expect exit 0, ACCEPTANCE: PASS
python3 tools/marketing-loops/acceptance.py --verbose  # per-CLI stdout under each row

# 2. Repo is not dirtied by the run:
git status --porcelain                                 # no content/publish-queue.json,
                                                       # no real content/*/publish/, no metrics/*

# 3. Full frozen unit suite still green (no regression to Sprints 001–005):
python3 -m unittest discover -s tools/marketing-loops/tests -q   # expect OK, > 233 tests

# 4. Frozen renderer acceptance still green (untouched):
python3 tools/marketing-render/acceptance.py --checked-on 2026-07-04   # expect exit 0

# 5. Hygiene sweeps:
grep -nE 'datetime|requests|urlopen|socket|http\.client|urllib\.request' tools/marketing-loops/acceptance.py  # clean
```

## 9. Attack checklist (the Evaluator SHOULD try to break these)

1. **Runner honestly fails.** Temporarily corrupt one expected golden or point a
   table row at a wrong exit → runner exits `1`, cites the specific unmet row (it
   is not a rubber-stamp).
2. **Cited reason, not "some FAIL".** A gate refusal that exits nonzero for the
   *wrong* reason must NOT satisfy its row — the reason substring is enforced.
3. **No-write on refusal is real.** After each publish-gate refusal, the `<TMP>`
   queue is absent/unchanged.
4. **No-scorecard on corrupt CSV is real.** After each malformed-CSV row, the
   `<TMP>` `--out` path does not exist.
5. **No partial-sum leaks.** `wrr-partial` scorecard contains no `147`/`252`/`295`
   and lists the missing component.
6. **Seam is genuine.** The chain's scorecard A/B bucket is driven by the
   *generated* queue's slot, not a fixture — mutate the generated slot and the
   assertion changes.
7. **Idempotency + no regression.** Re-running enqueue/package adds no duplicate
   rows and never flips `posted` back to `queued`.
8. **Table coverage.** Add a stray fixture dir → runner fails with "not in table";
   remove a fixture named in the table → runner fails with "no directory".
9. **Repo cleanliness.** `git status --porcelain` after a run shows no publish
   queue, no package files under real assets, no new metrics file.
10. **Frozen integrity.** No Sprint-001..005 `.py` changed (mtime + content); the
    renderer suite + the marketing-loops unit suite both stay green.
11. **README honesty.** Every documented command reproduces; the Phase-0 box is
    checked; no over-claim language; dashboards (a non-goal) are not claimed.
12. **No network / no wall-clock.** Hygiene greps clean; running with networking
    disabled still exits `0`.

## 10. Non-goals

- No change to any Sprint-001..005 module, the renderer toolchain, or any real
  asset / template / skill behavior (the SKILLs were finalized in their own
  sprints; this sprint does not re-touch them).
- No new metric, JSON schema, CLI flag, or gate condition.
- No live posting APIs, credentials, OAuth, scraping, or network.
- No dashboards, web UI, or charts (spec §8) — the README wording must not imply them.
- No new adversarial fixtures beyond what the cross-gap seam chain strictly needs;
  the Sprint-001..005 suite is the adversarial corpus, reused read-only.

## 11. Assumptions

- **A-6.1** The frozen CLIs' stderr/verdict reason strings are stable (shipped in
  Sprints 001–005 and covered by their green unit suites); the Generator pins each
  table row's `expected_reason_substring` to the **actual** emitted string,
  confirmed by invoking the frozen CLI, and never edits a frozen message to fit the
  table.
- **A-6.2** Week `2026-W27` is the canonical acceptance week (matches the committed
  `fixtures/metrics/expected/*.md` and `fixtures/metrics/full/queue.json` slots), so
  the seam chain's generated slots equal the golden fixtures' slots.
- **A-6.3** The join key is `utm_campaign` only (B-A2); the chain's scorecard places
  the real TGRERA asset because the CSV fixtures carry `utm_campaign=tgrera-enforcement-wave`,
  independent of the `--week` label.
- **A-6.4** `unparseable-verdict` frozen behavior may be exit `1` or `2` depending on
  the Sprint-002 implementation; the runner pins the row to whichever the frozen
  gate actually returns (both are valid refusals with no write) rather than forcing
  a value.
