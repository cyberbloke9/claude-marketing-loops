---
name: loop-research
description: Loop 1 — generate this week's ranked content signals for TERREM. Run weekly (scheduled) or on demand after a market event (RBI, budget, RERA ruling, builder news).
---

# Loop 1 — Research

Produce `signals/YYYY-MM-DD.md` (today's date) following `signals/TEMPLATE.md` exactly.

1. Read `personas/personas.md` (pain codes) and the two most recent files in `signals/` and `metrics/` (what resonated; don't repeat a covered signal unless the data changed).
2. Gather candidate signals:
   - TERREM platform data first (locality price moves, /markets anomalies, daily_refresh deltas) — this is the exclusivity moat.
   - Web: RBI announcements, RERA news for target cities (Bengaluru, Hyderabad, NCR, Chennai, MMR, Pune), registration/stamp-duty data releases, major launch/delivery news, ANAROCK/Knight Frank/JLL report releases.
3. Score each candidate: exclusivity × persona-pain relevance × timeliness. Discard anything that maps to no pain code.
4. Write the top 5 using the template — every signal needs a concrete data pull, a hook direction (cite `personas/hook-bank.md` numbers), and a flywheel target page on intel.terrem.in.
5. If a reactive-lane trigger fired this week, put it as Signal 1 and flag `REACTIVE — 48h deadline`.

Output only the signals file. Do not draft content — that's `/loop-create`.
