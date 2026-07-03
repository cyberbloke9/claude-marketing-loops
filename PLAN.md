# TERREM Marketing Loops — System Plan

Date: 2026-07-02
Basis: `RESEARCH.md` (19 adversarially verified claims + 2 gap-fill rounds). Every design decision below cites its evidence; anything unverified is marked **[hypothesis — A/B test]**.

---

## 0. Strategic frame (what the evidence actually says)

Three conclusions drive everything:

1. **The engine is the data flywheel, not virality.** Trulia built a $3.5B marketplace with ~zero paid spend by indexing supply-side data, publishing it, and letting traffic convert into more data (NFX/Flint, high confidence). TERREM's proprietary locality intelligence is the same class of asset. Short-form content is the *spark*; SEO-able intelligence assets are the *engine*.
2. **Optimize for returning readers, not followers.** Duolingo's CURR (current-user retention) was ~5x more impactful than any other lever (Mazal, high confidence). The north-star metric for every loop is **Weekly Returning Readers (WRR)** — people who consume TERREM content 2+ weeks in a row — not follower count.
3. **The chart is TERREM's listing photo.** Eye-tracking shows buyers look at the picture first and it predicts perceived value (Seiler 2012). TERREM doesn't sell listings — it sells intelligence — so every piece of content leads with one striking, Tufte-clean, source-stamped data visual.

**Brand voice (ultrathink adaptation of Duolingo):** Duolingo's *unhinged mascot* works for a free consumer app; TERREM sells trust in the largest financial decision of a person's life. What transfers is not the chaos — it's **(a) a consistent, recognizable character, (b) days-not-weeks reactive turnaround, (c) narrative arcs**. TERREM's character: **"The Candid Analyst"** — founder/analyst on camera (1.7x hook lift vs fronted talent, VidMob), data-backed, mildly contrarian, "says what builders won't." Sharp, never zany.

**Personas (from ANAROCK H1 2025, high confidence):**

| Persona | Share | Profile | Top pain points → content hooks |
|---|---|---|---|
| **The Upgrader** (end-use) | ~65% | ₹90L–1.5Cr budget (36% of market), wants 3BHK in Bengaluru/Hyderabad/NCR/Chennai, 2BHK in MMR/Pune | 81% price anxiety ("did I miss the window?"), 98% completion-assurance demand ("will it be delivered?"), 93% construction quality |
| **The Investor** | ~35% | RE is #1 preferred asset class (63%, beating stocks 22%, gold 7%) | Yield vs appreciation by locality, exit liquidity, regulatory (RERA) risk |

Channel map: Instagram Reels + YouTube Shorts for Upgraders; LinkedIn + email/WhatsApp digest for Investors/NRIs. Posting windows remain **[hypothesis — A/B test]**, now on verified ground (Round 3 R1): **no credible India-specific posting-time data exists anywhere** — Sprout's 2026 benchmarks normalize to "Local Time" with no IST edition, and Buffer/Sprout global windows even disagree (3–8 p.m. vs Tue–Thu 8–10 a.m.). First-party A/B in Loop 5 is not a nice-to-have; it is the only way to get IST priors.

---

## 1. The five loops

Each loop = input → agent/process → output artifact on disk → feeds the next loop. All artifacts live in this repo so loops are inspectable and resumable.

### Loop 1 — Research loop (signals)
*Cadence: weekly + event-triggered. Automation: scheduled agent.*

- **Inputs:** TERREM's own platform data (locality prices, /markets, daily_refresh), RBI/repo announcements, RERA filings, registration data, launch news, budget/policy events.
- **Process:** agent ranks signals by (persona pain-point relevance × data exclusivity × timeliness). Exclusivity matters most: content only TERREM can make is the moat.
- **Output:** `signals/YYYY-MM-DD.md` — top 5 content-worthy signals, each with the supporting data pull and a one-line "why now."
- **Reactive lane (Duolingo six-day lesson):** any RBI rate decision, major RERA ruling, or budget announcement triggers an out-of-cycle run with a 48-hour content deadline.
- **Trulia analogue:** every signal that becomes content must link back to a TERREM intelligence page (locality report, market dashboard) — content → traffic → usage data → richer intelligence. That's the flywheel closing.

### Loop 2 — Persona/pain-point loop (audience)
*Cadence: monthly. Automation: scheduled agent + manual comment review.*

- **Inputs:** new survey releases (ANAROCK, Knight Frank, JLL), TERREM search queries, comments/DMs on published content, top-performing hooks from Loop 5.
- **Process:** refresh persona docs; mine actual audience language ("possession delay," "carpet vs super built-up") — hooks in the audience's own words outperform marketing-speak.
- **Output:** `personas/personas.md` + `personas/hook-bank.md` — a living pain-point → hook mapping (e.g., "98% want completion assurance" → hook: *"This builder has delayed 3 of its last 4 projects. Here's how to check yours in 2 minutes."*).

### Loop 3 — Content creation loop (assets)
*Cadence: 2–3 assets/week. Automation: agent drafts, human records/approves.*

Capacity is now evidence-backed (Round 3 R6–R8): Duolingo's breakout channel ran on ~1.5 FTE (2020) and 2 FTE + contractors day-to-day (2025); Surreal runs on 4 with production outsourced, winning with low-production static assets. Two enablers make 2–3 assets/week + the 48h reactive lane work on a 2-person team, and both are policy choices, not hires: **(a) approval authority stays inside the team** (Duolingo: "we approve the content within the team ourselves") — no external sign-off in the loop; **(b) low-production default** — carousels and static-chart assets first (Surreal: "the simpler the better"), talking-head video only when the take needs a face.

- **Inputs:** top signal (Loop 1) × matching hook (Loop 2) × format template.
- **Formats, in priority order:**
  1. **The Weekly Ledger** (hero format) — one carousel + one short/reel, same data, per week. Recurring, named, habit-forming: the retention mechanic. Carousels benchmark 1.92% engagement vs 0.50% Reels (Metricool).
  2. **City Leaderboard** (monthly) — ranked locality price/momentum table. Duolingo's leaderboard lesson (+17% engagement time): competitive framing ("Whitefield just overtook Indiranagar") drives return visits and shares.
  3. **Reactive Analyst Take** (event-triggered, 48h) — direct-to-camera short on the news of the week.
  4. **SEO locality explainers** (ongoing) — the Trulia engine: one intelligence page per locality, updated by daily_refresh, each social asset links to one.
- **Script structure (short-form):** Hook (≤3s, from hook-bank, direct-to-camera: +50% hooking power) → the chart (one visual, one claim) → the "so what" for the persona → CTA to the TERREM page. **Refuted-stats guardrail:** do not cite "90% recall in 6s," "3.3x native actions," or "2x/43% purchase intent" in any content or internal docs — all killed in verification.
- **Carousel structure:** slide 1 = hook, ≤10 words, one idea; slide 2 = second hook; one idea per slide; open loop resolved at slide 5–6; last slide = CTA + source/date.
- **Output:** `content/YYYY-MM-DD-<slug>/` — script.md, carousel.md, chart spec, target persona, target metric.

### Loop 4 — Design/QA loop (gate)
*Cadence: per asset. Automation: checklist agent — every rule below is mechanically checkable.*

Brand kit (build once, then lock as templates):
- **Type:** IBM Plex Sans (headings 600) + Inter (body) — fintech-standard, open apertures for digit legibility. Scale: Major Third (1.25), base 16px equivalent.
- **Canvas minimums:** headlines 48–72px on 1080×1080; story/reel text 36–60px; body ≥24px; line height 1.4–1.6x; preview at 360px width.
- **Contrast:** ≥4.5:1 normal text, ≥3:1 large (WCAG AA). No condensed/thin faces on video overlays (+11–26% reading-time penalty, NN/g). No all-lowercase overlay text.
- **Line length:** 45–90 characters.
- **Safe zones:** feed 1080×1350, critical content in center ~1000×1270; reels/stories keep clear of top 250px / bottom 440px; LinkedIn link images 1200×627.
- **Charts (the trust surface):** maximize data-ink, no chartjunk, y-axis never truncated without disclosure, **source + as-of date printed on every chart**, TERREM wordmark bottom-right. This is non-negotiable — for an intelligence brand, chart integrity *is* the brand.
- **Output:** QA verdict appended to the asset folder; a failed check blocks publish.

### Loop 5 — Publish/measure loop (feedback)
*Cadence: publish per calendar; measure weekly. Automation: scheduled agent compiles the scorecard.*

- **Publish:** schedule per channel; run the posting-time A/B (morning vs 3–8 p.m. IST, per channel) for the first 8 weeks, then fix on winners.
- **Measure — retention-first KPI stack (CURR logic):**
  1. **WRR — Weekly Returning Readers** (north star): repeat consumers across weeks (returning profile visits, repeat viewers, email/WhatsApp open-streaks).
  2. Content → site: clicks to intel.terrem.in per asset; locality-page sessions.
  3. Flywheel depth: sign-ups / data contributions / partner inquiries originating from content.
  4. Craft diagnostics: 3s-hold rate (platform gating metric), carousel swipe-through, completion rate.
  5. Vanity (tracked, never optimized): followers, likes.
- **Loss-aversion mechanics [hypothesis — test]:** streak-style nudges for the owned channel ("your Whitefield price alert expires," "3-week Ledger streak") — Duolingo's streak-saver was their single biggest retention win.
- **Output:** `metrics/YYYY-Www.md` scorecard → feeds Loop 1 (what signals resonated) and Loop 2 (which hooks won).

---

## 2. Rollout sequence (don't launch five loops at once)

- **Phase 0 (week 1):** Brand kit + templates (Loop 4 assets), analytics plumbing (UTM links, per-channel dashboards), hook-bank v1 from ANAROCK pain points. Nothing publishes without measurement in place — the Duolingo playbook is unrunnable without retention data.
- **Phase 1 (weeks 2–5):** Loops 1 + 3 minimal — ship **only The Weekly Ledger** (1 carousel + 1 short/week). Prove the pipeline end-to-end on one format.
- **Phase 2 (weeks 6–9):** Turn on Loop 5 scorecards + posting-time A/B; add the reactive lane; first monthly Loop 2 refresh.
- **Phase 3 (week 10+):** Add City Leaderboard + SEO locality pages (the Trulia engine); scale to 3 assets/week only if WRR is trending up. **Hard stop:** if WRR is flat after 8 published weeks, stop scaling volume and re-enter Loop 2 (it's a resonance problem, not a reach problem).

## 3. Automation map (Claude Code)

| Loop | Mechanism |
|---|---|
| 1 Research | `/schedule` weekly scheduled agent + manual trigger for events |
| 2 Persona | `/schedule` monthly agent; human reviews diffs |
| 3 Creation | On-demand skill: `signal + hook → drafts` into content folder |
| 4 Design/QA | Checklist agent per asset (all rules mechanical); Canva/Figma locked templates for humans |
| 5 Measure | Weekly scheduled agent compiles scorecard from platform exports |

Repo: this folder (`~/Downloads/terrem-marketing-loops/`) — init git, artifacts as files, same file-only coordination pattern as agent-harness.

## 4. Ultrathink review — what changed and why

1. **Killed the Stanford premise honestly.** No GSB picture-formula exists (verified negative). Replaced with the peer-reviewed photo-first evidence base, and translated it: TERREM's "listing photo" is the chart. Chart-first content, chart integrity as brand.
2. **Inverted the funnel.** The draft instinct was short-form-first (Duolingo envy). For a high-consideration purchase, the verified engine is the Trulia data/SEO flywheel; short-form is acquisition for it. Every asset must link into an owned intelligence page or the loop doesn't close.
3. **De-fanged the mascot.** "Unhinged" transfers badly to a trust brand. Kept the mechanics (character consistency, fast reactive turnaround, narrative arcs), swapped the register to Candid Analyst — which the VidMob data independently supports (everyday expert on camera beats fronted talent).
4. **Retention before reach.** Made WRR the north star and Phase 0 = measurement, because the single highest-confidence finding in the whole research base is that returning-user retention beats every other lever ~5x.
5. **Capacity honesty.** 2-person team → one hero format shipped consistently beats five formats shipped raggedly. Consistency is itself the streak mechanic — the audience's habit forms around *your* cadence.
6. **Marked every unverified assumption** [hypothesis — A/B test]: posting times, streak nudges for content, carousel heuristics. The measure loop exists to burn these down with TERREM's own data.
7. **The India flywheel — designed (Round 3 replaces the open question):**
   - **What to index:** registration/IGR transaction data aggregated to **project/society level** — the proven unit of content in India (Zapkey's 145k pages, Square Yards' quarterly studies both use it) — plus state RERA project registries, with **all personal identifiers stripped** (GODL excludes personal data; DPDP-prudent). TERREM already holds the Hyderabad seed: 302k transactions, 55 locality metric series.
   - **Value back to sources (Trulia's mechanic, translated):** builders get named rankings/visibility in data studies (Square Yards proves builders accept and amplify this); buyers get price discovery on real transacted — not asking — prices (Zapkey's utility); media gets syndicable quarterly studies (Hindu Business Line et al. already run Square Yards' — data studies earn distribution).
   - **What is defensible — and what is not:** raw registration data is NOT a moat (Zapkey: 145k pages, ~15 employees, ₹1.75Cr revenue, shrinking). Square Yards and PropEquity already have multi-city raw coverage. **The defensible layer is synthesis + media quality + retained audience** — no incumbent pairs registration data with a lean, Candid-Analyst-grade content operation. That pairing is TERREM's whole thesis, and rounds 1–3 verify each half independently.
   - **Sequencing:** own Hyderabad completely first (data already in hand), expand city-by-city only when the Hyderabad loop demonstrably converts (traffic → sign-ups → data partnerships).
   - **Hard precondition before Phase-3 scale:** legal review of state-portal ToS + DPDP Act 2023 implications for registration records. Incumbent practice is de facto tolerance, not clearance (Round 3 caveat). Until then, publish aggregates and project-level stats, never named natural persons.
