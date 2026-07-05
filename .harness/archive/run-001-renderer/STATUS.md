# Harness Run — Asset Renderer + Deterministic QA Gate

Run started: 2026-07-04
Project dir: /Users/prithviputta/Downloads/terrem-marketing-loops
Workspace (bus): /Users/prithviputta/Downloads/terrem-marketing-loops/.harness

## Raw request

Build the Asset Renderer + Deterministic QA Gate for the TERREM marketing-loop system: (1) renderer turning content/<slug>/ specs (chart-spec.md + carousel.md + meta.md) into 1080×1350 carousel slide PNGs + 1080×1920 vertical chart card, using locked brand tokens from brand/brand-kit.md; (2) mechanical QA validator measuring rendered PNGs + specs against brand/qa-checklist.md (WCAG contrast on hex pairs, px type minimums, safe zones, hook ≤10 words, source/date stamp, blacklisted stats, provenance prompts) with machine-readable PASS/FAIL per asset consumable by /loop-qa; (3) CLI scripts (render + qa), README docs, end-to-end demo on content/2026-07-03-tgrera-enforcement-wave/. Constraints: no network at render time (fonts vendored/system), no TERREM product-repo changes, everything in this repo, Python or Node. Evaluator must render real PNGs, measure pixels/contrast, attack the validator with violating fixtures (11-word hook, truncated y-axis, low-contrast pair, missing source stamp), and confirm the TGRERA asset passes end-to-end.

## Phase table

| Time | Phase | Sprint | Result |
|---|---|---|---|
| start | Step 0 skeleton | — | created |
| — | Step 1 PLANNER | — | pending |
| — | Sprint 001 contract | 001 | ACCEPT (round 1) |
| — | Sprint 001 build+evaluate | 001 | VERDICT: PASS |
| — | Sprint 002 contract | 002 | in progress |
| — | Sprint 002 contract | 002 | REJECT r1 → ACCEPT r2 |
| — | Sprint 002 build+evaluate | 002 | VERDICT: PASS |
| — | Sprint 003 contract | 003 | in progress |
| — | Sprint 003 contract | 003 | ACCEPT (round 1) |
| — | Sprint 003 build+evaluate | 003 | VERDICT: PASS |
| — | Sprint 004 contract | 004 | in progress |
| — | Sprint 004 contract | 004 | ACCEPT (round 1) |
| — | Sprint 004 build+evaluate | 004 | VERDICT: PASS |
| — | Sprint 005 contract | 005 | in progress |
| — | Sprint 005 contract | 005 | REJECT r1 → ACCEPT r2 |
| — | Sprint 005 build+evaluate | 005 | VERDICT: PASS |
| — | Acceptance Gate | all | in progress |
| — | Acceptance Gate (retry after transient) | all | VERDICT: PASS |
| — | Run complete | — | 5/5 sprints PASS + gate PASS |
