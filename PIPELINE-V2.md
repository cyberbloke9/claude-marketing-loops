# Pipeline V2 — From Clean Cards to Scroll-Stopping Posts, Published Directly

Status: FINALIZED against research round 4 (RESEARCH.md R4-A/B), 2026-07-06. Publisher build (§6) is gated on the round-5 questions (R4-B5) + founder checklist (SETUP-CHECKLIST.md).
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

Hard rules v2 (finalized from round-4 evidence; each QA-checkable):
- **Carousel-first strategy** (R4-A1/A2: 6.90% vs 4.44% on IG, 9x saves; 2–3x on LinkedIn): the default asset is a 4:5 carousel, ≤10 slides (Instagram API cap, R4-B2). Single cards are the exception (reactive takes), not the rule.
- **One dataset per post, one concrete comparison/ranking** (Finshots convention, R4-A6; Chartr stand-alone rule, R4-A5). If a post needs two datasets it's two posts.
- **The visual must stand alone without its caption** (R4-A5) — so-what line + source + handle on-card, always.
- **Type floors raised** (Voronoi, R4-A4 — text renders ~half-size on mobile): body & chart labels ≥26px, footnotes/sources ≥24px on the 1080-wide canvas (≈ Voronoi's 25pt/23pt at 1200-wide). Headline floor unchanged (≥48px).
- **One dominant element ≥3× body size** on every surface — the number or visual structure doing the hook's work. QA-checkable from manifest.
- **Feed-thumbnail gate:** QA renders a 360px preview; headline + dominant element must clear minimum effective sizes.
- **Cover-slide craft = hypothesis lane** (R4-A7: no verified evidence exists on cover patterns, faces, carousel length) — covers follow the ≤10-word/one-idea rule and get A/B-tested via Loop 5; log cover pattern (BIG-NUMBER vs CHART-FIRST) per asset in meta.md so our own data answers what research couldn't.
- **Platform mapping** (R4-A3, R4-B4): Instagram = native carousel; **Facebook = reuse Instagram assets unchanged** (format barely matters: 5.20% vs 4.84% vs 4.76%); **LinkedIn = MultiImage post or multi-page PDF document** (organic carousels are API-impossible — verified negative).

### 5. TGRERA card, redesigned under v2 (the concrete example)

RECEIPTS format: headline compressed to "3 builders. 9 days." (giant, top-left); three chips each led by its amount/consequence at display size (₹14.95L REFUND +10.7% · SALES FROZEN · 45 DAYS TO PAY) with builder/date at body size; so-what strip: "All three collected money on unregistered or delayed projects. Check the RERA number before you pay — free → intel.terrem.in"; source stamp + wordmark. Every fact identical to v1; the *information hierarchy* finally matches the story.

### 6. Publisher — direct posting (finalized architecture; build gated on R4-B5 answers + checklist)

**Verified API surfaces (RESEARCH.md R4-B):**
- **Instagram (primary):** professional account; prefer **Instagram Login flavor** (`instagram_business_basic` + `instagram_business_content_publish`, `graph.instagram.com`, no Facebook Page dependency). Two-step container flow: `POST /media` per image (carousel children `is_carousel_item=true`, ≤10) → parent `media_type=CAROUSEL` → `media_publish`; poll `status_code`; containers expire 24h. Rate limit 50-or-100/24h (documented discrepancy) — check `GET /<IG_USER_ID>/content_publishing_limit` at runtime; TERREM posts ~1/day, far below either.
- **LinkedIn:** MultiImage post type or PDF document post — **never** attempt organic carousels via API (verified impossible). Renderer v2 therefore also emits a **multi-page PDF** variant of each carousel (slide PNGs → PDF), which is the LinkedIn-native "carousel".
- **Facebook Page:** reuse Instagram images; exact Pages API endpoints are a round-5 gap — do not code this leg until verified.

**Architecture constraint discovered (R4-B2):** `image_url` must be a **publicly hosted URL** — the Graph API fetches it; you cannot upload bytes directly for feed images. TERREM needs a public static path for rendered PNGs (options: `intel.terrem.in/social-assets/<slug>/…` on the self-hosted server, or an S3/R2 bucket). This goes on the founder checklist.

**Code shape:** `tools/marketing-loops/publish_api.py` consumes the existing queue (the API seam built in run 2): reads `queued` rows → uploads/publishes per channel adapter → writes `posted` + permalink (same transition `mark_posted.py` does manually, same no-regress rules). Secrets in untracked `.env`; **dry-run default** until credentials verified; per-day cap enforced in code; only gate-passed rows are ever eligible (frozen modules, unchanged).

**Round-5 questions to resolve before writing the publisher** (R4-B5): Meta App Review requirements for the publish permissions — and whether Development Mode with app-role (founder-owned) accounts suffices indefinitely for self-posting; LinkedIn OAuth scopes/review path for member vs organization posts; Facebook Pages endpoints; Ayrshare/Buffer-style third-party API as a lower-friction alternative (build-vs-buy).

### 7. Execution plan (after research lands)

1. Fold round-4 findings into RESEARCH.md; finalize §4 rules + §6 requirements. (this session)
2. Write `context/` pack (BRAND/BUSINESS/ASSETS). (this session)
3. **Harness run 3:** renderer v2 format library + QA gate v2 (dominant-element + thumbnail-test checks) + TGRERA card re-render in RECEIPTS format. Adversarial fixtures: hook-less card, dominant-element-too-small, thumbnail-illegible, missing so-what line.
4. **Harness run 4:** `publish_api.py` against sandbox/test accounts (dry-run mode) — blocked on founder completing the credentials checklist.
5. Human: complete platform setup checklist (accounts, Meta app review, LinkedIn app) — the only non-code dependency.
