---
name: loop-measure
description: Loop 5 — compile the weekly scorecard from platform metrics and feed decisions back into the other loops. Run weekly after exporting channel analytics.
---

# Loop 5 — Publish/Measure

Produce `metrics/YYYY-Www.md` (current ISO week) per `metrics/TEMPLATE.md`.

1. Inputs: platform exports/screenshots the user provides (IG/YT/LinkedIn insights), site analytics for intel.terrem.in (UTM-filtered), and `content/*/meta.md` published this week. If an input is missing, leave the cell blank and list it under "Missing data" — never estimate or invent numbers.
2. Fill the KPI stack: WRR first, flywheel clicks, per-asset craft diagnostics (3s-hold, swipe-through, shares, clicks) tagged with hook numbers.
3. Update the posting-time A/B table (weeks 1–8); after week 8, write the fixed winning slots into `personas/personas.md`.
4. Write the "Decisions fed back" section concretely: signal types to repeat/drop (→ Loop 1), hook winners and bottom-third retirements (→ hook-bank), format changes (→ Loop 3).
5. Run the hard-stop check: if WRR is flat across 8 published weeks, flag it at the top of the scorecard in bold and recommend re-entering Loop 2.
6. Append publish links/dates to each asset's `meta.md`.
