# Chart Spec — hyd-premium-vs-budget

```
Claim (one sentence): Over the last 3 months, Hyderabad's premium core fell while its
budget corridors surged — the same city moved in opposite directions by up to 28 points.

Chart type: diverging horizontal bar (one bar per locality, sorted by 3-month % change)

Data (locality · median ₹/sqft · 3-month % change):
  GAINERS                      FALLERS
  Medchal        ₹3,534  +19.2%   Banjara Hills  ₹15,992  −3.0%
  Ameerpet       ₹8,234  +12.7%   Punjagutta     ₹11,206  −3.4%
  Tarnaka        ₹5,982  +12.7%   Jubilee Hills  ₹14,980  −6.1%
  Shamirpet      ₹2,489  +12.0%   Begumpet       ₹10,521  −8.0%
  Dilsukhnagar   ₹5,459  +11.3%   Kukatpally      ₹6,251  −8.4%
                                  Dundigal        ₹2,954  −9.4%

Query: locality_metrics JOIN micro_markets, metric_date = latest, ORDER BY price_trend_3m;
       n per locality 3.3k–7.9k priced observations; 302,156 transactions in DB overall.

Accent element: the two extremes (Medchal +19.2%, Dundigal −9.4%) in --accent #0f766e /
--chart-down #dc2626; all other bars --ink-muted. Callout bracket spanning the premium-core
cluster (Banjara Hills, Punjagutta, Jubilee Hills, Begumpet) labeled "the posh core, all red."

Y-axis: bars from zero baseline (diverging at 0%) — no truncation. ✓
On-graphic attribution: "Source: TERREM Intelligence · 302,156 Hyderabad transactions · as of 2026-03-08"
Wordmark: TERREM, bottom-right, --accent-deep #0d3d38.
Background --bg #faf8f3; bar labels Inter 500 ≥24px; headline Inter 700.

Nuance to carry in copy (Candid Analyst credibility beat): 3-month ≠ 12-month. Several
fallers are UP over 12 months (Gopanpally −5.9% 3m but +11.6% 12m; Kukatpally flat 12m).
Premium-core weakness is recent, not a crash. Say so.
```
