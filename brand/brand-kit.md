# TERREM Brand Kit — Content Edition

Evidence basis: RESEARCH.md §Round 2 (D1–D11). Rules here are the source of truth for Loop 4.

## 1. Voice: The Candid Analyst

Founder/analyst on camera and on the page. Data-backed, mildly contrarian, protective of the buyer. "Says what builders won't."

| Do | Don't |
|---|---|
| Lead with one number and its consequence | Open with greetings, context, or throat-clearing |
| Name localities, prices, dates specifically | "Prices are rising in many areas" |
| Show the chart, then the take | Give the take without the data |
| Admit uncertainty with ranges | Overclaim or predict without a basis |
| Dry wit, one beat max | Memes, chaos, forced trends (unhinged ≠ trust) |
| End with what the viewer should *check* | End with "follow for more" as the only CTA |

Register check: would a skeptical CA aunt and a 29-year-old Bengaluru PM both trust this? If either would cringe, rewrite.

## 2. Typography

- **Headings:** IBM Plex Sans, weight 600 (fintech standard, open apertures)
- **Body / data:** Inter, weight 400–500 (generous x-height, digit legibility)
- **Scale:** Major Third (1.25). Base 16 → 20 → 25 → 31 → 39 → 49 → 61
- **Canvas minimums (1080px canvases):**
  - Feed/carousel headline: 48–72px; body ≥24px
  - Story/Reel overlay text: 36–60px
  - Line height 1.4–1.6×; line length 45–90 characters
- **Never:** condensed or thin faces on video overlays (NN/g: +11.2% reading time); all-lowercase overlay text (+26%); decorative/handwriting fonts anywhere

## 3. Color

Tokens must match the live intel.terrem.in palette — pull hex values from the deployed site before first use and record them here (do not invent new brand colors; see TERREM v4 visual-preservation constraint).

```
--bg:            <from site>   # canvas background
--ink:           <from site>   # primary text — must hit 4.5:1 on --bg
--ink-muted:     <from site>   # secondary text — must hit 4.5:1 on --bg
--accent:        <from site>   # one accent only; used for THE number/line that matters
--chart-up:      <from site>   # gains
--chart-down:    <from site>   # declines
```

Rules: WCAG AA — ≥4.5:1 normal text, ≥3:1 large text (≥24px / 18.5px bold). One accent color per asset. Plain backgrounds behind text — no textures/photos under type.

## 4. Charts — the trust surface

The chart is TERREM's listing photo (eye-tracking: viewers look at the visual first and it sets perceived value). Chart integrity IS the brand.

1. One chart, one claim. If it needs two charts, it's two assets.
2. Maximize data-ink: no gridline forests, no 3D, no gradients on bars, no chartjunk.
3. Y-axis starts at zero, or the break is explicitly marked and disclosed.
4. **Source + as-of date printed on the graphic itself** (e.g., `Source: TERREM Intelligence · RERA Karnataka · as of 2026-07-01`). Non-negotiable.
5. TERREM wordmark bottom-right, small.
6. Label directly on the data where possible; legends only when direct labeling fails.
7. The one number that matters gets --accent; everything else stays neutral.

## 5. Layout & safe zones

- Feed/carousel: 1080×1350 (4:5). Critical content inside center ~1000×1270 (grid crops to 3:4).
- Reels/Shorts/Stories: 1080×1920. Keep critical content >250px from top, >440px from bottom (UI overlay zone). Practical rule: central 70–80% of frame.
- LinkedIn link image: 1200×627. LinkedIn carousel PDF: 1080×1350.
- Always preview at 360px width before approving.

## 6. Carousel structure

- Slide 1: hook, ≤10 words, one idea, biggest type on the slide. Answers "is this for me?" + "what do I get if I swipe?"
- Slide 2: second hook (some users land here first).
- One idea per slide — flashcard, not blog paragraph.
- Open loop: question raised on slide 1, resolved on slide 5–6.
- Last slide: the "check this yourself" CTA + link to the TERREM page + source/date.

## 7. Short-form structure

Hook (≤3s, direct-to-camera, from `personas/hook-bank.md`) → the chart (one visual, one claim) → the "so what" for the persona → CTA to the TERREM page.

Talent: founder/analyst, conversational, direct-to-camera (VidMob: +50% hooking power; everyday experts 1.7× vs fronted talent). No hired presenters.

## 8. Blacklist

Never cite these refuted stats in content or docs (killed 0-3 in verification — see RESEARCH.md):
"90% of recall in first 6 seconds" · "TikTok-native ads drive 3.3x actions" · "hooked ads 2x engagement / +43% purchase intent" · "best slots are Wed 4pm / Fri 3–4pm" · "professionals scroll LinkedIn on the evening commute".
