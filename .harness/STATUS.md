# Harness Run 002 — Publish Queue + Analytics Plumbing (Gaps 2+3)

Run started: 2026-07-04
Project dir: /Users/prithviputta/Downloads/terrem-marketing-loops
Workspace (bus): /Users/prithviputta/Downloads/terrem-marketing-loops/.harness
Prior run: .harness/archive/run-001-renderer (5/5 sprints + acceptance gate PASS)

## Raw request

Close Gap 2 (publish layer up to the API boundary) and Gap 3 (analytics plumbing) of the TERREM marketing-loop system. Gap 3: ingestion tooling that turns platform analytics exports (Instagram/YouTube/LinkedIn CSVs + site analytics) into the weekly scorecard metrics/YYYY-Www.md per metrics/TEMPLATE.md — per-asset craft diagnostics tied to hook numbers, UTM verification, posting-time A/B table, WRR computation from provided inputs; never fabricate missing data (blank + "Missing data" list). Gap 2: from a QA-PASSED asset, generate per-channel publish packages (final captions with per-channel UTM links, rendered PNG paths, schedule slots) and a machine-readable publish queue with states; refuse assets whose qa-verdict is not PASS or that are killed; design the seam so posting APIs can plug in later (no live APIs — no credentials). Sprint format, adversarially evaluated.

## Phase table

| Time | Phase | Sprint | Result |
|---|---|---|---|
| start | Step 0 skeleton (run 2) | — | created |
| — | Step 1 PLANNER | — | pending |
| — | R2 Sprint 001 contract | 001 | ACCEPT (round 1) |
| — | R2 Sprint 001 build+evaluate | 001 | VERDICT: PASS (patch: prompt_patch_001) |
| — | R2 Sprint 002 contract | 002 | in progress |
| — | R2 Sprint 002 contract | 002 | ACCEPT (round 1) |
| — | R2 Sprint 002 build+evaluate | 002 | VERDICT: PASS |
| — | R2 Sprint 003 contract | 003 | in progress |
| — | R2 Sprint 003 contract | 003 | ACCEPT (round 1) |
| — | R2 Sprint 003 build+evaluate | 003 | VERDICT: PASS |
| — | R2 Sprint 004 contract | 004 | in progress |
| — | R2 Sprint 004 contract | 004 | ACCEPT (round 1) |
| — | R2 Sprint 004 build+evaluate | 004 | VERDICT: PASS |
| — | R2 Sprint 005 contract | 005 | in progress |
| — | R2 Sprint 005 contract | 005 | ACCEPT (r1, after limit-cutoff retry) |
| — | R2 Sprint 005 build+evaluate | 005 | VERDICT: PASS (build retried once, transient stall) |
| — | R2 Sprint 006 contract | 006 | in progress |
| — | R2 Sprint 006 contract | 006 | ACCEPT (round 1) |
| — | R2 Sprint 006 build+evaluate | 006 | VERDICT: PASS |
| — | R2 Acceptance Gate | all | in progress |
| — | R2 Acceptance Gate | all | VERDICT: PASS |
| — | Run 002 complete | — | 6/6 sprints PASS + gate PASS |
