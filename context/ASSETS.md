# TERREM — Asset Inventory for the Creative Engine

What exists and can be used in posts, with provenance status.

## Usable now

| Asset | Where | Notes |
|---|---|---|
| Brand tokens + chart rules | `brand/brand-kit.md` | Pulled from product globals.css — locked |
| Inter 400/500/600/700 (vendored, OFL) | `tools/marketing-render/fonts/` | Deterministic rendering |
| Renderer v1 | `tools/marketing-render/render.py` | 1080×1350 carousel + 1080×1920 card; v2 format library planned (PIPELINE-V2 §4) |
| QA gate | `tools/marketing-render/validate.py` | V2–V12 pixel+spec checks |
| Publish layer | `tools/marketing-loops/` | UTM, gate, queue, packages, scorecard — API seam ready |
| Hook bank (21 hooks by mechanism) | `personas/hook-bank.md` | Winners/losers updated by Loop 5 |
| Verified evidence base + blacklist | `RESEARCH.md` | Rounds 1–3 (+4 pending) |
| Public-data signal stream | `signals/` (weekly, automated) | Cloud routine, Mondays ~07:00 IST |

## Usable with care

| Asset | Constraint |
|---|---|
| TERREM product screenshots (dashboard, locality pages) | Strong trust asset; must show only provenance-clean views (no synthetic-data price trends until Path A). Capture set: TODO — needs founder to pick approved views. |
| TERREM Hyderabad DB (302k transactions, locality metrics) | **BLOCKED for content** — 95.4% synthetic; unblocks when Path A productionizes real-only metrics or registry data is licensed. |

## Does not exist yet (don't reference in posts)

- Video/motion assets, founder photo/avatar set, testimonials, press mentions.
- Platform accounts for direct publishing (Instagram professional / Facebook Page / LinkedIn app) — setup checklist comes from research round 4, PIPELINE-V2 §6.
