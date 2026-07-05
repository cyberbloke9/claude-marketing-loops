VERDICT: PASS
SCORE: 4.9
BLOCKERS: 0
HIGH: 0

# Sprint 005 Findings — Adversarial fixtures, wiring & end-to-end acceptance

Mode: EVALUATE. Sprint 005 (final). Headless Python CLI toolchain — no web UI, no browser, so no
Playwright click-path (contract §0, grounded in spec §1/§11's "fixtures" + "end-to-end" language).
The Evaluator attacked the CLIs directly and reproduced every contract §7 acceptance step and both
§8 tamper probes independently. Verdict: PASS.

## Contract §7 acceptance steps — all 8 green

1. Full unit suite — `python3 -m unittest discover -s tools/marketing-render/tests` → Ran 139
   tests, OK (exit 0). 117 prior (S001-004) + 22 new (test_acceptance.py). No prior test removed.
2. End-to-end acceptance — `acceptance.py --checked-on 2026-07-04` → exit 0,
   `ACCEPTANCE: PASS (14/14 expectations met)`. All 12 fixtures hit their §6.2 expected check+rule;
   TGRERA re-render+validate PASS.
3. Determinism (R8) — ran twice; chart-card.png SHA-256
   91f8407faf85a78718ca5709009c50ce56d4572edcfade63df62b34249f583cc identical. Independently
   confirmed date-independence: --checked-on 2026-12-25 changed only JSON checked_on; PNG unchanged.
4. Named discrimination — fx-11-word-hook fires V7-hook-words; fx-blank-png fires V3-ink
   ("0 ink px < 50"); each cited by rule. Verified via --verbose echoing real validate.py stdout.
5. /loop-qa skill — SKILL.md contains all six §5 behaviors (invoke validate.py on content/<slug>;
   read/parse qa-verdict.json; report failed_checks id/detail/rule + needs_review informational;
   FAIL blocks publishing + does not fix/never edits; render-only-when-manifest-absent; exit
   0/1/2 mapping + rule-citation-only).
6. README commands runnable — the three fenced commands in "## Asset Renderer + QA Gate" run from
   repo root: render exit 0; validate exit 0 PASS; acceptance exit 0. Real slug, real flag.
7. Purity probe — exact §8 AST heredoc → "PASS: no network imports", exit 0. acceptance.py imports
   only {argparse, hashlib, json, pathlib, shutil, subprocess, sys}.
8. Scope boundary — no new content/ adversarial folders; prior modules import clean; 117-test prior
   suite intact within the 139 green (behavioral non-regression proof).

## Contract §8 tamper probes — the gate is REAL

- Tamper 1 (stale-verdict regeneration): deleted fx-11-word-hook/render/qa-verdict.json, re-ran →
  runner re-invoked validate.py, regenerated verdict, row still PASS. Never trusts a stale verdict.
- Tamper 2 (wrong-check rejection): in-dir scratch copy flipped fx-11-word-hook expected id to
  V4-contrast → runner "ACCEPTANCE: FAIL (13/14) — expected V4-contrast not in failed_checks; got
  V7-hook-words", and exited 1 (non-zero, confirmed via direct $? capture — the runner's exit
  code tracks its verdict per §6.3). Only the NAMED check is accepted. Scratch removed.

## Robustness / hidden-breakage

- Error states: validate.py content/does-not-exist → exit 2 (precondition, named path);
  render.py content/nope → exit 1, clear message. Matches §9.
- meta.md idempotency: two validate runs → exactly one qa-verdict block and one provenance block;
  no accumulation.
- --verbose is live (trace self-repair verified), not a dead flag.

## Harsh Pass Standard — pass

No user hesitation (two documented commands + one-shot runner). No dead controls. No placeholder
copy; tone terse/mechanical/cite-the-rule per spec §7. Error paths exit with named messages, not
tracebacks. Browser/mobile/keyboard N/A (no UI; justified §0). Evidence reproduces on independent
re-run.

## Notes (non-blocking)

- N-1 (evidence, not defect): tools/ is git-untracked, so §8 "git diff empty for prior source"
  cannot be run as a literal git command. Corroborated two ways instead: (a) mtimes — render.py
  10:47, validate.py 11:18, measure.py 09:18, all prior test_*.py predate the 11:58-12:05 S005
  build window; only acceptance.py/test_acceptance.py fall in it; (b) the full 139-test suite green
  after S005 edits (behavioral non-regression). Stronger than a byte-diff. No action.
- N-2 (on-stack determinism, disclosed R-D): R8 pixel-identity guaranteed on this Pillow/freetype
  stack with vendored fonts + no network; disclosed, consistent with prior sprints.

## Scoring

Functionality 5 (gate proven real via wrong-check tamper) · Design/CLI-UX 5 · Originality 4.5 ·
Craft 5 · Evidence/process 5. Weighted (20% each) = 4.9. Bar met: 0 blockers, 0 high, evidence >=4,
functionality >=4, weighted >=4. VERDICT: PASS.
