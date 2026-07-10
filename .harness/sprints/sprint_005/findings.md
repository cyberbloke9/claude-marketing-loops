VERDICT: PASS
SCORE: 4.7
BLOCKERS: 0
HIGH: 0

# Sprint 005 Findings — Facebook Page adapter (round-5-gap, gated)

Mode: EVALUATE. Stdlib CLI + JSON tool; no browser surface (contract §13, Playwright
N/A). Verification = full unittest suite + independent Evaluator-run CLI probes on a
seeded fixture and the real 2-row asset (not trusting the Generator trace).

## Verdict
PASS. Every Sprint-005 behavior (B30/B31/B32 + the step-rendering pieces of
B6/B7/B9/B10/B11/B17 for a facebook row) is implemented, gated, labeled, and
independently reproduced. No blocker/high/medium. One Low note (F-001) for Sprint-006
awareness; non-gating.

## Independent evidence (Evaluator-run)
- Gate 1 — `unittest discover` → Ran 366 tests OK, 0 failures/errors, 0 skips.
- Gate 2 — flag OFF (fixture IG+FB row, run from fixture cwd): exit 0; FB row
  steps=0 + EXACT disabled note; EXACT stderr NOTICE line; IG row 8 steps unaffected.
- Gate 3 — flag ON: exit 0; FB row = 4 steps (N+1, N=3): 3x POST /<FB_PAGE_ID>/photos
  then POST /<FB_PAGE_ID>/feed. Photo params {access_token=<REDACTED>, published=false,
  url=<PUBLIC_ASSET_BASE_URL>/<slug>/format-01.png}. Feed attached_media threads
  <fb-photo-id-1..3> verbatim (B10); message = caption verbatim incl \n (B5); note =
  "...; 4 HTTP calls; round-5-gap: best-documented-guess pending live verification (R4-B5)".
- Gate 4 — grep 'graph.facebook.com/v[0-9]' → nothing (no invented version prefix);
  round-5-gap count 10; best-documented-guess present in code + plan note.
- Gate 5 — --public-asset-base-url joins <base>/<slug>/<filename> concretely; only
  <REDACTED> where a token would go; no token string in stdout or publish-plan.json.
- G1 — 0-attachment enabled FB row → exit 2 cited "no attachments to publish", no
  plan written; no upper-cap invented (correct per R4-B5 gap).
- G2 — disabled row + 0-attachment package → skipped (exit 0), G1 not reached.
- Gate 7 — determinism: real asset DEFAULT dry-run is byte-identical across two
  post-005 runs (proves determinism, NOT a pre/post comparison).
- Gate 6 — non-regression: supported by (a) the `channel == "facebook"` branch is
  gated and NEVER fires for the IG/LI rows (only [(instagram,8),(linkedin,3)] in the
  default plan), and (b) the seed-based non-regression unit test is green. NOTE: the
  checked-in golden is SEED-based, not a captured real-asset Sprint-004 baseline —
  which is why a real-asset run legitimately diverges (real linkedin.json carries
  utm_source=linkedin; the seed golden carries instagram). A literal real-asset
  byte comparison is impossible here (no git; the caption legitimately drifted), so
  Gate 6's intent is met via seed-proxy + the gating-code reasoning above, not a
  literal real-asset diff.
- Anti-stub + no-network — plan_steps & execute both derive from the single _fb_flow
  generator via _drive_plan/_drive_execute (source 934–1031); parity test green.
  urlopen at exactly ONE site inside Transport.request (line 265); no socket in any
  test/dry-run.

## Finding F-001: disabled facebook row with a MISSING package file exits 2 (B4) rather than skipping
Severity: Low
Category: Functionality
Status: Noted (non-gating)

### Contract Clause
§3 G2 / §7.1 (disabled row skipped before guards) vs spec B4 (missing package =
universal exit 2).

### Reproduction Steps
1. Queue a facebook row whose package_path is a non-existent file, flag OFF.
2. Run dry-run. 3. Observe exit 2 (universal B4 check fires before the skip branch).

### Expected
Ambiguous: §7.1 implies skip; B4 implies exit 2.

### Actual
Exit 2 (B4 wins) — Generator-disclosed. When the package EXISTS (all fixtures, any
realistically enqueued FB row) the row skips with exit 0 (confirmed: Gate 2, G2).

### Evidence
Generator trace disclosure; Evaluator confirmed happy skip path exit 0 with seeded
package and G1/G2 behavior.

### Required Fix
None this sprint — spec-consistent (B4 universal) and all gates pass with a seeded
package. If Sprint 006 wants a disabled FB row to skip with an absent package,
resolve B4-vs-§7.1 ordering in the Sprint-006 contract, not in code here.

### Pass Condition
Already passing for every contract fixture (package present ⇒ skip, exit 0).

## Scoring
Weights (infra tool): Functionality 30%, Evidence 25%, Craft 20%, Design 15%,
Originality 10%.
- Functionality 5 — every B30/B31/B32 behavior + guards reproduced by CLI probe.
- Evidence 5 — 366 green (0 skips), all gates independently re-run; determinism +
  non-regression + no-secret verified first-hand.
- Craft 5 — single _fb_flow source, single urlopen seam, exact-string notes,
  deterministic compact JSON, no invented endpoint/version.
- Design 4.5 — faithful photos+feed transcript, visible round-5-gap + redaction.
- Originality 4 — disciplined gated/labeled treatment of the unverified guess.
Weighted = 5(.30)+5(.25)+5(.20)+4.5(.15)+4(.10) = 4.7. Bars met (no blockers/highs,
evidence ≥4, functionality ≥4, weighted ≥4) ⇒ PASS.
