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
QA: PASS (specs level — graphics not yet rendered)
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
