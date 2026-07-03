# TERREM Marketing Loops

An evidence-based, agent-automated marketing system for [TERREM](https://intel.terrem.in) — Indian real-estate intelligence.

Every rule in this repo traces to a verified source in `RESEARCH.md`. Unverified assumptions are marked `[hypothesis — A/B test]` and get burned down by the measure loop.

## The system

| Loop | Cadence | Input → Output |
|---|---|---|
| 1. Research | Weekly + event-triggered | Market/platform signals → `signals/YYYY-MM-DD.md` |
| 2. Persona | Monthly | Surveys + audience language → `personas/` |
| 3. Creation | 2–3 assets/week | Signal × hook × template → `content/YYYY-MM-DD-<slug>/` |
| 4. Design/QA | Per asset | Asset vs `brand/qa-checklist.md` → pass/block |
| 5. Publish/Measure | Weekly | Platform metrics → `metrics/YYYY-Www.md` → feeds Loops 1–2 |

North star: **WRR — Weekly Returning Readers** (retention, not reach). See `PLAN.md` §0 for why.

## Layout

```
PLAN.md                  Five-loop system plan + rollout phases
RESEARCH.md              Verified evidence base (with refuted-claims blacklist)
brand/brand-kit.md       Voice, typography, color, chart rules
brand/qa-checklist.md    Loop 4 mechanical gate — nothing publishes without passing
personas/personas.md     The Upgrader & The Investor (ANAROCK-sourced)
personas/hook-bank.md    Pain-point → hook mapping, by psychological mechanism
signals/                 Loop 1 output (TEMPLATE.md defines the format)
content/                 Loop 3 output (TEMPLATE.md defines the asset folder)
metrics/                 Loop 5 scorecards (TEMPLATE.md defines the KPI stack)
.claude/skills/          /loop-research /loop-persona /loop-create /loop-qa /loop-measure
```

## Running the loops

From this directory in Claude Code:

- `/loop-research` — generate this week's ranked signals (also runs on schedule)
- `/loop-create <signal>` — draft the Weekly Ledger assets for a signal
- `/loop-qa <content-folder>` — run the mechanical design gate
- `/loop-measure` — compile the weekly scorecard from exported metrics
- `/loop-persona` — monthly persona/hook-bank refresh

## Rollout status

- [x] Phase 0 — brand kit (real product tokens), templates, hook bank v1, repo scaffolding
- [ ] Phase 0 — analytics plumbing (UTM scheme, per-channel dashboards)
- [x] Phase 1 started — first signals run (2026-07-03); Ledger #1 KILLED at QA (synthetic-data provenance); TGRERA reactive take drafted + QA PASS; Ledger on public data queued (ANAROCK vs PropEquity)
- [ ] Phase 2 (weeks 6–9) — scorecards + posting-time A/B + reactive lane
- [ ] Phase 3 (week 10+) — City Leaderboard + SEO locality pages (Trulia engine)
