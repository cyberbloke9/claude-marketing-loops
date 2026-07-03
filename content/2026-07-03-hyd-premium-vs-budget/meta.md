# Meta — hyd-premium-vs-budget

```
Signal: signals/2026-07-03.md #1
Persona × pain: P1 × PRICE (primary), P2 × YIELD (secondary)
Hook: hook-bank #13 (contrarian, adapted) — "Per-sq-ft price is the most misleading number in Indian real estate" family; NEW variant added to bank as #21
Format: Weekly Ledger (carousel + short, same data)
Channels: IG carousel + reel, YT short, LinkedIn PDF
Flywheel target: https://intel.terrem.in/markets?utm_source=instagram&utm_medium=social&utm_campaign=hyd-premium-vs-budget
  (per-channel: utm_source=youtube / linkedin)
Target metric: 3s-hold ≥ 30% | carousel swipe-through ≥ 40% | clicks ≥ 50
Data as-of: 2026-03-08 (local DB snapshot 2026-04-21) — REFRESH BEFORE PUBLISH: re-run
  the locality_metrics query against the live daily_refresh DB and update all figures + as-of date.
QA: **KILLED 2026-07-03** — asset failed publish precondition (c), data provenance.
Reason: TERREM's transactions table is 95.4% synthetic (`calibrated_expansion`/`calibrated_model`;
see terrem_intelligence `docs/data-integrity-assessment-2026-06-18.md`). The Path A truth
recompute (`docs/pathA-results-2026-06-18.md`) shows the premium-core localities this story
hinges on have essentially NO real data: Jubilee Hills 5 real rows, Banjara Hills 13,
HITEC City 0, Madhapur 8 — all flagged "insufficient data". The −6.1%/−8.0% "premium core
fell" trends are model artifacts, unverifiable on real data. Publishing would be exactly the
"fabricated certainty" TERREM's own integrity doc warns against.
Lesson fed back: provenance check added to brand/qa-checklist.md; DB-derived price-trend
content BLOCKED until Path A is productionized + registry data licensed (PLAN §2).
Folder retained as record — killed assets are data.

Original (superseded) verdict: PASS (specs level — graphics not yet rendered)
Failed checks: none. Two issues found and fixed during review:
  (1) S8 said "registered-market transactions" — overclaimed provenance; corrected to
      "Hyderabad transactions" to match chart-spec attribution.
  (2) Final slide lacked the TERREM link required by the checklist; added to S8.
Publish preconditions:
  (a) DATA REFRESH — figures are as-of 2026-03-08 from the local DB snapshot; re-run the
      locality_metrics query against live daily_refresh data and update all numbers + as-of
      date before rendering. If the story no longer holds on fresh data, the asset dies.
  (b) Rendered graphics must re-pass the pixel checks (contrast, sizes, safe zones).
  (c) Verify the transactions table's provenance before ever calling it "registered" data.
Checked by: agent (Loop 4) on 2026-07-03
Published: —
```
