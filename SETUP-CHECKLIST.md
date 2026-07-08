# Founder Setup Checklist — Direct Publishing

The only non-code dependencies for Pipeline V2 §6. Everything below requires account ownership; none of it can be done by an agent. Verified API facts: RESEARCH.md R4-B + **Round 5 (all major gaps now resolved)**.

## ⚡ Round-5 headline: this is much easier than feared

- **Instagram + Facebook: NO Meta App Review, NO screencast, NO Business Verification** — because the app only serves accounts you own, Standard Access + app roles is enough (R5-1/R5-4). Realistic setup: **1–3 days**.
- **LinkedIn company page: weeks** (vetted Community Management API application — R5-5). **Do the founder-profile workaround first** (`w_member_social`, "Share on LinkedIn" product — R5-6): posts to your profile, works for MultiImage + PDF documents, and founder-as-face matches the round-1 evidence anyway. Apply for Community Management in parallel; switch the adapter when approved.
- **Build vs buy: build.** No third-party scheduler claim survived verification (R5-7); the direct path is verified and review-free for Meta.

## 1. Accounts (do first, ~30 min)

- [ ] Convert/confirm TERREM Instagram account is a **professional** account (Business or Creator). (Required for any API publishing — R4-B1.)
- [ ] TERREM Facebook Page exists (needed only if choosing the Facebook-Login flavor, or for Facebook posting later).
- [ ] LinkedIn: decide the posting surface — **founder profile**, **TERREM company page**, or both. (Company-page API access path is a round-5 gap; profile posting uses different scopes.)

## 2. Meta developer app (~1 hr + review wait)

- [ ] Create a Meta app at developers.facebook.com (Business type).
- [ ] Add Instagram product; choose the **Instagram Login** flavor (no Facebook Page dependency — R4-B1) unless round-5 finds a reason otherwise.
- [ ] Development Mode first: add the TERREM Instagram account as an app-role tester and verify posting works to your own account. (Whether Dev Mode suffices indefinitely for founder-only posting is an open round-5 question — it may remove App Review entirely.)
- [ ] If App Review needed: prepare screencast of the posting flow + business verification. Permissions to request: `instagram_business_basic`, `instagram_business_content_publish`.

## 3. Public asset hosting (~30 min, needs your server or bucket)

- [ ] Choose: `intel.terrem.in/social-assets/` (self-hosted, matches deploy topology) **or** an S3/R2 bucket.
- [ ] The Graph API fetches images by URL (`image_url`) — bytes cannot be uploaded directly (R4-B2). Rendered PNGs must be publicly reachable at publish time; can be deleted after the container publishes.

## 4. LinkedIn developer app (~1 hr + review wait; scope details = round-5 gap)

- [ ] Create app at developer.linkedin.com, associate with TERREM company page.
- [ ] Request the products covering Posts API w/ MultiImage + Documents (PDF) posting. NOTE: organic carousels are impossible via API (R4-B4) — MultiImage/PDF is the plan, not a workaround gone wrong.

## 5. Secrets handoff (5 min, after 2+4)

- [ ] Put tokens in `~/Downloads/terrem-marketing-loops/.env` (already gitignored — verify before writing): `IG_USER_ID`, `IG_ACCESS_TOKEN`, `LI_ACCESS_TOKEN`, …
- [ ] Tell the session "credentials in place" → publisher gets built (harness run 4) in dry-run mode first.

## Decision to make (can short-circuit 2–4)

**Build vs buy:** a third-party publishing API (Ayrshare, Buffer API, …) may replace ALL of sections 2–4 with one API key + monthly fee. Round-5 research resolves cost/limits; decide after reading it. If you already lean "buy", say so — it reorders the plan.
