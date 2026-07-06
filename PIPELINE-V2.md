# Pipeline V2 — From Clean Cards to Scroll-Stopping Posts, Published Directly

Status: DRAFT — research round 4 (creative craft + publishing APIs) in progress; §4 and §6 get finalized from its verified findings.
Basis: user directive 2026-07-06 ("TGRERA card is vague, no hook; feed branding/assets/business model; post directly to Instagram/LinkedIn/Facebook").

## 1. Ultrathink autopsy: why the TGRERA card fails as a hook

The v1 card is typographically compliant and *visually inert*. Specific failures:

1. **The hook rides on words alone.** "Telangana's regulator hit three builders in nine days" is a good spoken hook, but rendered as a paragraph headline it competes with every other text post in the feed. The numbers that could stop a scroll — **3 builders · 9 days · ₹14.95L · 10.7%** — are buried at body size.
2. **No dominant visual element.** Eye-tracking research (round 2) says the visual is viewed first and sets perceived value — the card has no visual, only type. Its data never becomes a *picture* (a timeline strip Jun 22→27→30, three order "chips", a big % figure).
3. **Whitespace misallocated.** ~55% of the canvas is empty margin while the payload sits at 30px body size. Feed-thumbnail test: at 360px wide, nothing on this card is readable except the headline.
4. **No so-what on the card.** The viewer's utility ("check the RERA number before you pay a rupee — takes 2 minutes") lives in the script, not the graphic. A card seen without its caption gives facts, not a reason to care. This is the "vague" problem.
5. **No recognizable format.** Nothing makes TERREM card #47 identifiable at a glance the way a Chartr or Visual Capitalist post is. Recurring visual formats are the brand-building mechanic for data publishers.
6. **No CTA / handle on-card.** Shares strip captions; the card must carry its own pointer.

**Root cause:** v1's renderer renders *documents*; v2 must render *formats* — a small library of visually-structured layouts where data becomes the picture.

## 2. The V2 pipeline (end to end)

```
CONTEXT PACK ─┐
              ├→ Loop 1 SIGNALS → Loop 3 CREATIVE ENGINE → RENDERER v2 → QA GATE v2 → PUBLISHER (APIs) → Loop 5 MEASURE
   (standing) ┘        (weekly)      (hook × format choice)   (format lib)   (visual checks)   (direct post)     (feedback)
```

### 3. Context Pack (new, standing inputs — "give TERREM's branding, assets & business model")

A `context/` directory the creative engine reads every run:

- `context/BRAND.md` — voice (Candid Analyst), visual identity beyond tokens: wordmark usage, the recurring format identities (§4), what TERREM never does (hype, fake urgency, unverified stats).
- `context/BUSINESS.md` — what TERREM sells and to whom: real-estate intelligence platform (intel.terrem.in); free market intelligence → sign-up → premium tier (auth/2FA/premium shipped v0.4.0); the flywheel (content → traffic → users → data → better intelligence); what a post must therefore *do* (drive a checkable action on TERREM, not just impressions).
- `context/ASSETS.md` — inventory of usable assets: brand tokens + fonts (vendored), TERREM wordmark, product screenshots (dashboard/locality pages — strongest trust asset once DB content unblocks), the hook bank, chart capabilities of renderer v2.
- Existing: `brand/brand-kit.md` (tokens/type/chart rules), `personas/` (audience + hooks), `RESEARCH.md` (evidence + blacklist).

### 4. Creative Engine + Format Library (the hook fix)

Loop 3 v2 picks **hook × format**, not just hook. Format library (each a renderer template with fixed visual grammar; final rules pending research round 4):

| Format | Visual grammar | Use for |
|---|---|---|
| **BIG NUMBER** | One number at 25–40% canvas height, one-line context above, so-what line below | Single striking stat (e.g., "10.7%" — the interest rate builders now owe) |
| **TIMELINE** | Horizontal/vertical date strip with event chips | Enforcement waves, project delay histories |
| **RECEIPTS** | 2–4 bordered "order chips" with amount as the dominant element per chip | Multi-item evidence (TGRERA orders — the v2 of the current card) |
| **VS / CONTRAST** | Split canvas, two opposing numbers/claims | ANAROCK −6% vs PropEquity +19%; premium vs budget corridors |
| **LEADERBOARD** | Ranked bars, accent on one row | City/locality rankings |
| **CHART** | v1 chart card, upgraded hierarchy | Trend stories (post-Path A) |
| **CHECKLIST** | Numbered utility steps, big index numerals | "Check before you pay" utility posts |

Hard rules v2 adds (draft; finalize from research):
- **One dominant element** ≥ N× body size (measurable — QA-checkable from manifest).
- **Feed-thumbnail test as a gate:** headline + dominant element legible at 360px; QA renders a 360px preview and checks min effective sizes.
- **So-what line mandatory on-card** (the utility/CTA, e.g., "Check any project's RERA number free → intel.terrem.in").
- **Handle/wordmark + source stamp** (kept from v1).
- Carousel covers follow first-slide hook craft (≤10 words, one idea) — kept, now with a visual dominant element required.

### 5. TGRERA card, redesigned under v2 (the concrete example)

RECEIPTS format: headline compressed to "3 builders. 9 days." (giant, top-left); three chips each led by its amount/consequence at display size (₹14.95L REFUND +10.7% · SALES FROZEN · 45 DAYS TO PAY) with builder/date at body size; so-what strip: "All three collected money on unregistered or delayed projects. Check the RERA number before you pay — free → intel.terrem.in"; source stamp + wordmark. Every fact identical to v1; the *information hierarchy* finally matches the story.

### 6. Publisher — direct posting (pending research Part B; structure fixed, details from findings)

- Targets: Instagram professional account, Facebook Page, LinkedIn (company page and/or founder profile) — exact API surfaces, permissions, review steps, and rate limits from round-4 verified findings.
- Architecture: `tools/marketing-loops/publish_api.py` consuming the EXISTING queue schema (built as the API seam in run 2) — queue rows go `queued → posted` automatically with returned permalinks; `mark_posted.py` remains the manual fallback.
- Credentials: `.env`-style local secrets, NEVER committed; setup checklist for the founder (accounts, app review) generated from research.
- Fail-safe: publisher only ever posts rows that passed the gate (frozen modules); dry-run mode default until credentials verified; per-day post caps.

### 7. Execution plan (after research lands)

1. Fold round-4 findings into RESEARCH.md; finalize §4 rules + §6 requirements. (this session)
2. Write `context/` pack (BRAND/BUSINESS/ASSETS). (this session)
3. **Harness run 3:** renderer v2 format library + QA gate v2 (dominant-element + thumbnail-test checks) + TGRERA card re-render in RECEIPTS format. Adversarial fixtures: hook-less card, dominant-element-too-small, thumbnail-illegible, missing so-what line.
4. **Harness run 4:** `publish_api.py` against sandbox/test accounts (dry-run mode) — blocked on founder completing the credentials checklist.
5. Human: complete platform setup checklist (accounts, Meta app review, LinkedIn app) — the only non-code dependency.
