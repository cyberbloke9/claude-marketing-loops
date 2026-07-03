---
name: loop-create
description: Loop 3 — draft a content asset set (script + carousel + chart spec) from a signal. Args: signal reference (e.g. "2026-07-07 #2") or a raw topic for the reactive lane.
---

# Loop 3 — Content Creation

Create `content/YYYY-MM-DD-<slug>/` with `meta.md`, `script.md`, `carousel.md`, `chart-spec.md` per `content/TEMPLATE.md`.

1. Read the referenced signal in `signals/`, plus `personas/personas.md`, `personas/hook-bank.md`, and `brand/brand-kit.md` (voice §1, structures §6–7, blacklist §8).
2. Pick the hook: prefer a proven bank hook adapted to this signal; if drafting a new one, add it to the bank with the next number and tag it NEW.
3. Draft in this order: chart-spec (the one claim) → script → carousel. If the claim can't be stated in one sentence over one chart, split into two assets.
4. Voice check against the Candid Analyst do/don't table. Specifics mandatory: locality, number, date. CTA must target a live intel.terrem.in page with UTM params.
5. Fill `meta.md` completely, including target metrics.
6. Finish by running `/loop-qa` on the new folder and appending the verdict.

Weekly Ledger default: one carousel + one short from the same data. Reactive Take: script only, 48h deadline, note the trigger event in meta.
