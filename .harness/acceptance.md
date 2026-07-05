VERDICT: PASS
SCORE: 4.9
BLOCKERS: 0
HIGH: 0

# System Acceptance — TERREM Marketing Loops (Gap 2 publish + Gap 3 analytics)

Cross-sprint, end-to-end regression pass over ALL six shipped sprints together
(001 UTM → 002 gate/queue → 003 package/mark-posted → 004 CSV ingest →
005 scorecard → 006 acceptance runner). Goal: prove the sprints still work
*together* and that no later sprint silently broke an earlier one.

## Result: PASS — no cross-sprint regression found

Every cumulative behavior the spec + the six contracts promised was
re-exercised from a clean state and held. All verification was reproduced
independently by the evaluator, not taken from the Generator's claims.

## Evidence (evaluator-run, this session)

### Whole-system gates
- **Cross-gap acceptance runner** `tools/marketing-loops/acceptance.py` →
  `ACCEPTANCE: PASS (50/50 expectations met)`, exit 0. Covers UTM verifier,
  publish gate/enqueue, package/mark-posted, analytics rejection-vs-missing,
  golden scorecards, and the end-to-end seam chain.
- **Full unit suite** `python3 -m unittest discover` → `Ran 254 tests … OK`
  (Sprints 001–006 all green together — no regressed test).
- **Frozen renderer acceptance** `tools/marketing-render/acceptance.py
  --checked-on 2026-07-04` → `ACCEPTANCE: PASS (14/14)`, exit 0. The
  pre-existing toolchain is untouched and still passes.

### Independent cross-gap seam chain (evaluator-run, NOT via the runner)
Ran `verify_utm → enqueue → package → mark_posted → scorecard` by hand on the
real PASS asset `content/2026-07-03-tgrera-enforcement-wave`, all writes to a
throwaway temp dir, week `2026-W27`:
- enqueue → 3 `queued` rows; package → generated queue slots
  `instagram=evening/18:00`, `youtube=morning/11:00`, `linkedin=evening/17:30`.
- mark_posted instagram → row `posted`, other two remain `queued`.
- scorecard consuming **the generated queue** → Posting-time A/B table placed
  instagram's 51 clicks in **Evening**, youtube's 30 in **Morning**, linkedin's
  67 in **Evening** — i.e. the scorecard's A/B buckets are driven by the slots
  the publish layer wrote, not a fixture. The Gap-2→Gap-3 seam is genuine and
  load-bearing.
- instagram package `utm_link` =
  `…?utm_source=instagram&utm_medium=social&utm_campaign=tgrera-enforcement-wave`
  (correct per-channel UTM).

### Earlier-sprint behaviors still hold under the full system
- **S001** `verify_utm.py content` → exit 0; both real assets `OK` (incl. the
  KILLED hyd asset — UTM validity orthogonal to gate).
- **S002/003** real KILLED hyd asset → `REFUSED … [missing-verdict, killed]`,
  exit 1, **queue file not created** (gate never bypassed, no-write-on-refusal).
- **S005** `wrr-partial` scorecard → WRR this-week cell **blank**, component
  `returning_viewers` listed under Missing data, and the forbidden partial sums
  (`147`/`252`/`295`) appear **nowhere** in the output. No invented number.
- **S004/S005** every corrupt-CSV row (truncated / wrong-header / wrong-colcount
  / non-numeric / blank-join) → exit 2, cited, **no scorecard written**.

### Hygiene / integrity
- **Repo not dirtied:** after the runner AND all evaluator runs,
  `git status --porcelain` shows no `content/publish-queue.json`, no
  `content/*/publish/`, no `metrics/2026-*.md` — all mutable writes went to temp.
- **No network / no wall-clock:** no `requests`/`urlopen`/`socket`/
  `http.client`/`urllib.request` in any `tools/marketing-loops/*.py`; runner
  hygiene grep clean.
- **Skills present:** `.claude/skills/loop-publish/SKILL.md` and
  `.claude/skills/loop-measure/SKILL.md` both exist.
- **README:** Phase-0 analytics-plumbing box checked, reworded to what shipped
  (UTM verifier + publish layer + scorecard compiler) — no dashboard/
  production overclaim.

## Scoring (systems/infra weighting: Functionality + Evidence emphasized)
- Functionality: 5 — both gaps work end-to-end; seam proven genuine.
- Evidence/process: 5 — independently reproduced; determinism, golden files,
  no-write/no-partial-sum invariants all verified by the evaluator.
- Craft: 5 — stdlib-only, deterministic, frozen-module discipline, cited errors.
- Design (schema-as-DNA, recoverable messages): 4.5.
- Originality (adversarial-fixture DNA, no-partial-sum discipline): 4.5.
- Weighted total (Func 30 / Evid 30 / Craft 20 / Design 10 / Orig 10): **4.9**.

## Notes (non-blocking)
- `tools/marketing-loops/` is untracked in git, so frozen-module integrity has
  no git baseline to diff content against; it was corroborated by mtime (only
  `acceptance.py` and `test_acceptance.py` are dated to the Sprint-006 build;
  Sprints 001–005 modules predate it). This is not an unchecked gap: the product
  is behavior, not file identity — even a silent edit to an earlier module would
  have had to evade all of the 254 unit tests, the 50 acceptance rows, and the
  evaluator's manual earlier-sprint spot-checks, and none of those regressed.
  Integrity is therefore backstopped by behavior verification regardless of mtime.
- Runner-level determinism confirmed this session: two `acceptance.py` runs
  produced a byte-identical report (matching shasum).
- Golden-scorecard cell arithmetic (e.g. `expected/full.md` WRR=347, craft
  cells) was verified at the Sprint-005 gate; this session independently
  re-derived the *edge* content (wrr-partial blank + no partial sum, and the
  seam-driven A/B columns 51/30/67) and relied on the prior per-sprint pass for
  the full golden's cell arithmetic — in scope for that gate, not re-computed here.

No blockers, no high findings. The shipped sprints work together with no
cross-sprint regression. **VERDICT: PASS.**
