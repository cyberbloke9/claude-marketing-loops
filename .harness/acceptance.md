VERDICT: PASS
SCORE: 4.7
BLOCKERS: 0
HIGH: 0

# EVALUATE_SYSTEM — Cross-sprint acceptance for `publish_api.py` (Sprints 001–007)

Whole-project end-to-end regression pass. Reconstructed the cumulative behavior set
from `spec.md` (all 7 sprints) and every `sprints/sprint_00N/contract.md`, then
re-exercised the primary and failure paths each sprint promised, together, from a
clean tree. No cross-sprint regression found. Verdict: **PASS**.

This is a stdlib Python CLI + JSON tool. Per every sprint contract (Sprint 006 §13,
Sprint 007 §8) there is **no browser surface** — Playwright is N/A by design.
Verification is `unittest` + CLI probes, which is what was run.

## Evidence (commands run, from repo root)

### Full cumulative regression suite — GREEN
- `python3 -m unittest discover -s tools/marketing-loops/tests` → **Ran 386 tests, OK**
  (0 failures / 0 errors / 0 skips). Sprint-006 contract Gate 1 expected 366 (Sprint 005)
  + new Sprint-006 tests; 386 is consistent (no test skipped to pass).
- `python3 -m unittest discover -s tools/marketing-render/tests` → **Ran 266 tests, OK**
  (the `VERDICT: FAIL` lines in that run are an acceptance fixture's own stdout, not a
  unittest failure — the harness assertion wraps it and the suite reports OK).

### Sprint 001 — frozen-module facebook extension integrates across ALL consumers
- `utm.CHANNEL_SOURCE_MAP` = `[instagram, youtube, linkedin, facebook]` — facebook
  appended LAST (B33), ordinals instagram=0/youtube=1/linkedin=2 preserved.
- `queue.VALID_CHANNELS` includes `facebook`; `channels._ALIASES` has both `fb` and
  `facebook` (B34); `schedule._TIMES` has `facebook`, `slot_for('2026-W28','facebook')`
  = `2026-W28/evening/19:00` (B35, no KeyError). The five enumerated legacy test
  assertions (test_utm/test_channels/test_queue/test_schedule) were updated and pass.

### Sprints 002–005 — real-asset dry-run fidelity (Gate 7)
- `python3 tools/marketing-loops/publish_api.py --week 2026-W28 --dry-run` → **exit 0**,
  exactly the 2 real queued rows of `2026-07-09-anarock-vs-propequity` in `(slug,channel)`
  order. IG row renders the full 8-step container flow (content_publishing_limit →
  3 child containers → parent CAROUSEL → poll status → media_publish → permalink fetch)
  on `graph.instagram.com`; LI row renders the 3-step Document flow (`/rest/documents`
  initializeUpload → PUT bytes → `/rest/posts`) with versioned headers `LinkedIn-Version:
  202506`, `X-Restli-Protocol-Version: 2.0.0`. Caption + UTM link are verbatim. Secrets
  shown as `<REDACTED>`; dependent values as named placeholders (`<ig-child-container-id-N>`,
  `<ig-parent-creation-id>`, `<li-upload-url-1>`, `<li-document-urn>`, `<PUBLIC_ASSET_BASE_URL>`).
  No blacklisted `_publishing` misspelling; matches RESEARCH R4-B2/R4-B3/R5-3/R5-6.

### Sprint 006 — live transition wiring, no-regress, day-cap, determinism
- Determinism (Gate 8): two DEFAULT dry-runs produced **byte-identical**
  `content/publish-plan.json`. Queue unchanged vs HEAD after dry-runs.
- Named Sprint-006 live tests all pass: `test_live_happy_path_ig_li_transition`,
  `test_live_targeted_already_posted_refusal`, `test_live_rerun_fully_posted_week_exit0`,
  `test_live_daycap_breach_refusal_prior_stand`, `test_live_daycap_counts_existing_posted_today`,
  `test_live_adapter_refusal_container_error`, `test_live_incremental_write_prior_posts_persist`,
  `test_live_no_secret_in_queue_or_output`, `test_live_facebook_enabled_posts`,
  `test_live_facebook_disabled_skipped_no_count`, `test_dryrun_raising_transport_still_exit0`
  (B8 no-network proof, exit 0 with raising transport), `test_live_ast_single_urlopen_site`
  (B38 single `urlopen` call site preserved after all additions).

### Sprint 007 — docs reconciled to match the shipped CLI
- Stale absolute claims removed: `grep -c "no live posting API" SKILL.md` = 0;
  `grep -c "no posting APIs" README.md` = 0 (C1/C15 reconciled, not appended).
- All required greppable claims present in SKILL.md (`publish_api.py`, `--dry-run`,
  `--i-have-verified-dry-run`, `PUBLIC_ASSET_BASE_URL`, `SETUP-CHECKLIST`,
  `--enable-facebook`, `round-5-gap`, `REDACTED`) and README.md (`publish_api.py`,
  `--live`, `SETUP-CHECKLIST`, `--enable-facebook`).
- `--help` defaults match the §5 value table verbatim: `--max-per-day` default 3,
  `--linkedin-post-type` default `document`, `--linkedin-version` default `202506`,
  `--env` default `.env`, `--enable-facebook` OFF/round-5-gap.
- No secret literal in either doc (`EAAB|Bearer …|IGQ…` → no hit).

## Cross-sprint regression check (the point of this gate)
Later sprints did not break earlier behaviors:
- Sprint 006 live wiring did NOT perturb the Sprints 002–005 dry-run: the real-asset
  2-row plan is still faithful and byte-identical (Gate 7/Gate 8 re-run green).
- Sprint 001 channel-map extension did NOT break `schedule` bucket math or any prior
  suite (386 loops tests green, legacy channel-set assertions updated and passing).
- Sprint 007 is docs-only; full code suite still green, no `tools/`/`content/` behavior
  change, queue and plan artifacts untouched by the doc edits.
- Secrets discipline holds end-to-end: no `.env` token literal appears in stdout,
  plan JSON, the written queue, or the docs (verified by both live tests and grep).

## Notes (non-blocking, not regressions)
- The working tree carries the full multi-sprint diff (channels/schedule/utm/tests +
  new `publish_api.py`, SKILL.md, README.md) because the harness has not committed
  per sprint. This is expected for a cumulative acceptance pass and does not affect
  behavior; Sprint 007's "only two files changed" is a per-sprint hygiene clause, not
  a system-level acceptance condition. `content/publish-plan.json` is a dry-run
  artifact (gitignored) and is correctly never written by any live path.

## Scoring
- Functionality: 5 — every promised cumulative behavior (dry-run fidelity, live
  transition, no-regress, day-cap, gated facebook, exit codes) reproduces on demand.
- Evidence/process: 5 — 652 tests green + independent CLI reproduction of the real-asset
  plan, determinism, and doc/flag fidelity.
- Craft: 5 — deterministic serialization, single injectable transport seam, no
  wall-clock, redaction visible.
- Design (output legibility/safety): 4.5 — plan reads as a faithful API transcript.
- Originality: 4 — domain-specific fidelity work, not generic scaffolding.
- Weighted total ≈ 4.7. No blockers, no high findings. PASS is legal.
