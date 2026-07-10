VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 007 Findings — Skill + README (document the direct-publish layer)

Docs-only sprint. No browser surface (Playwright N/A, carried from Sprint 006).
Verification = the contract §8 grep/command battery, run from the project root.
Every gate passed. Verdict: **PASS**.

## Evidence — contract §8 gates

**§8.1 — only the two doc files are this sprint's delta (A1).**
`git status --porcelain` shows `.claude/skills/loop-publish/SKILL.md` and `README.md`
modified. The other ` M` entries under `tools/`, `tests/`, `fixtures/` are the
pre-existing uncommitted Sprints 001–006 tree (HEAD `201456c` predates
`publish_api.py`, which shows as `??` untracked — never committed, hence unchanged by
this sprint). `publish_api.py` is untracked and was not touched. No `.env`, no secret,
no `content/` artifact staged. `content/publish-plan.json` is gitignored
(`git check-ignore` confirms) and absent from status. The docs sprint introduced no
code/content change. PASS (substantive A1 holds; the tool dirt is prior passed work,
disclosed in the generator trace, and must not be reverted).

**§8.2 — stale claims reconciled, not appended (A2).**
`grep "no live posting API" SKILL.md` → exit 1 (no hit). `grep "no posting APIs"
README.md` → exit 1 (no hit). Both absolute claims reworded: SKILL lines 12–19 now
state a dry-run-first CLI exists but `--live` is gated on `SETUP-CHECKLIST.md` and not
usable today, operator still posts by hand; README lines 105–110 the same. PASS.

**§8.3 — required greppable claims present (A3/A4).**
SKILL: publish_api.py=7, --dry-run=5, --i-have-verified-dry-run=2,
PUBLIC_ASSET_BASE_URL=5, SETUP-CHECKLIST=2, --enable-facebook=2, round-5-gap=1,
REDACTED=3. README: publish_api.py=5, --live=4, SETUP-CHECKLIST=2, --enable-facebook=2.
All ≥1. README subsection `### Direct-publish layer — publish_api.py (dry-run-first)`
present at line 148. PASS.

**§8.4 — the documented default dry-run actually runs (A5).**
`python3 tools/marketing-loops/publish_api.py --week 2026-W28 --dry-run` → exit 0,
prints the 2-row plan for `2026-07-09-anarock-vs-propequity` (instagram 8-step
container flow + linkedin document flow), `access_token=<REDACTED>`, absent base URL
rendered as `<PUBLIC_ASSET_BASE_URL>`, caption+UTM link verbatim. Wrote
`content/publish-plan.json` (7141 bytes). `git status content/publish-queue.json` →
clean (queue untouched). PASS.

**§8.5/§5 — every cited flag/default matches `--help` verbatim (A6).**
`--help`: --max-per-day default 3, --linkedin-post-type {document,multi-image} default
document, --linkedin-version default 202506, --env default `.env`, --dry-run DEFAULT.
All match the §5 value table and the prose in both docs. No fabricated flag, no invented
default. PASS.

**§8.6 — full prior suite green (A7).**
`python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'` →
Ran 386 tests, OK, 0 failures/0 errors. Docs sprint did not regress code. PASS.

**§8.7 — no secret literal in either doc (A8).**
`grep -nE "(EAAB|Bearer [A-Za-z0-9]{10,}|IGQ[A-Za-z0-9])" SKILL.md README.md` →
exit 1 (no hit). Env keys shown keys-only; token values as `<REDACTED>`. PASS.

## Content fidelity spot-check (C1–C17)

Read both files in full. SKILL.md covers: reworded intro (C1), dry-run default command
+ default statement (C2), stdout+publish-plan.json/zero-network/zero-queue (C3), named
placeholders + <REDACTED> + no base URL needed (C4), preserved manual mark_posted.py
bridge (C5, steps 3–4 retained), live command form (C6), the three preconditions with
SETUP-CHECKLIST.md (C7), queued→posted + permalink + no-re-post (C8), per-day cap
default 3 keyed on --date (C9), --enable-facebook default-OFF round-5-gap
skip-with-notice (C10), LinkedIn selector default document (C11), exit codes 0/1/2
(C12), report-verbatim/never-bypass discipline (C13), secrets discipline (C14).
README.md reconciles the stale sentence (C15) and adds an accurate direct-publish
subsection with runnable default dry-run, the three live preconditions, facebook flag,
and exit codes (C16); all cited flags match --help (C17), and no full plan-dump is
pasted (no drift surface). Both docs point out the /loop-publish skill wraps the flow
and never bypasses the gate.

## Harsh-pass checklist

No dead claim, no filler copy (domain-specific TERREM/IG/LinkedIn/Facebook framing),
no fabricated flag, no self-contradiction (both stale sentences gone), no pasted output
that will drift, no secret literal. The single-image IG step-count ambiguity the
generator disclosed for prior sprints is out of this docs sprint's scope and does not
surface in either doc's prose.

## Scoring

- Functionality 20% → 5.0 (every documented command runs exactly as written; 386 green)
- Evidence/process 20% → 5.0 (all 8 §8 gates reproduced first-hand)
- Craft 20% → 5.0 (matches --help verbatim; contradiction reconciled, not appended)
- Design/legibility 20% → 4.5 (clear two-mode structure, ordered steps, cited exit codes)
- Originality 20% → 4.5 (domain-specific, no generic/AI-slop copy)

Weighted total ≈ 4.8. No blockers, no high findings. Evidence ≥ 4, Functionality ≥ 4.
