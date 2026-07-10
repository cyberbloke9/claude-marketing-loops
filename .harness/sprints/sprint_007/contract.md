# Sprint 007 Contract — Skill + README (document the direct-publish layer)

Scope: spec §11 Sprint 007 + behavior notes carried across §5 (the CLI shape B1,
the dry-run default B6–B11, the live gate B12, secrets discipline B17, the
`--enable-facebook` round-5-gap B30/B31, the LinkedIn post-type selector B25, exit
codes B40–B42). This is the **documentation-only** closing sprint: it updates the
`/loop-publish` skill and the repo README so both accurately describe the
now-built `publish_api.py` (Sprints 001–006), with the **dry-run preview as the
default operator path** and **`--live` documented as gated on
`SETUP-CHECKLIST.md` completion plus the three live preconditions**.

No code changes. No new API facts. No new tool behavior. This sprint only makes the
prose on disk match the CLI that already exists and passed Sprints 001–006.
`RESEARCH.md` R4-B/R5 remain the sole API authority; nothing here re-derives or
re-states an API fact as new.

This is a stdlib CLI + JSON toolchain; there is **NO browser surface** (Playwright:
N/A — carried from Sprint 006). Verification is: (1) grep the two doc files for the
required greppable claims, (2) run every command the docs show and confirm it
behaves as documented, (3) diff every flag/default the docs cite against
`publish_api.py --help`, (4) confirm no secret/token literal appears in either doc.

---

## 1. Files this sprint changes (exactly two)

1. `/.claude/skills/loop-publish/SKILL.md` — the `/loop-publish` skill.
2. `/README.md` — the repo README.

No other file is created or edited. `git status --porcelain` after the sprint must
show ONLY these two paths as modified (plus the harness bus/log files), and NO
change under `tools/`, `content/`, `.env`, or any queue/plan artifact.

---

## 2. The contradiction this sprint MUST resolve (not just append)

Both docs currently assert the pre-Sprint-001 world where no posting API exists:

- `SKILL.md` intro (≈ lines 10–12): *"There is **no live posting API and no
  credentials** — the operator posts by hand on each platform and records the
  permalink back into the queue."*
- `README.md` "Publish layer (Gap 2)" (≈ lines 105–107): *"There are no posting
  APIs and no platform credentials; a human posts manually and records the
  permalink back into the queue."*

`publish_api.py` now exists. Leaving either sentence standing next to new prose that
documents a posting API makes the docs self-contradictory — an automatic "not
accurate" failure. Both sentences MUST be **reconciled** (reworded), not appended
around. The accurate framing, which the docs must convey:

- A direct-publish API layer (`publish_api.py`) now exists, but it ships
  **dry-run-first**: with **zero platform credentials** it emits a faithful,
  inspectable HTTP request plan and makes zero network calls.
- `--live` (actual posting) is **gated** and **not usable today** because the
  founder has not completed `SETUP-CHECKLIST.md` (no tokens, no
  `PUBLIC_ASSET_BASE_URL` yet).
- Therefore the **only way to actually publish today** remains: dry-run preview →
  post by hand → `mark_posted.py`. The manual flow is **preserved, not replaced**.

---

## 3. Required content — `loop-publish/SKILL.md`

The skill must document BOTH modes and their relationship. Each item below is a
greppable, checkable claim.

### 3.1 Reconcile the stale intro (§2)
- C1. The "no live posting API" sentence is reworded to state that a dry-run-first
  direct-publish CLI (`publish_api.py`) now exists but `--live` is gated on
  `SETUP-CHECKLIST.md` and is not usable today; the operator still posts by hand.

### 3.2 Dry-run as the DEFAULT operator path (works today, no credentials)
- C2. Documents the default preview command form, verbatim-runnable:
  `python3 tools/marketing-loops/publish_api.py --week <YYYY-Www> --dry-run`
  (and notes `--dry-run` is the DEFAULT when neither `--dry-run` nor `--live` is
  passed — B6).
- C3. States what the dry-run produces: the ordered per-row HTTP request plan to
  **stdout** AND to `content/publish-plan.json`, with **zero network calls** and
  **zero queue-state change** (B6–B8).
- C4. States the plan uses **named placeholders** for response-dependent values and
  **`<REDACTED>`** where a secret would go, and that dry-run needs no
  `PUBLIC_ASSET_BASE_URL` (rendered as a placeholder when absent) — B10/B11/B17.

### 3.3 The bridge to the manual flow (today's real publish path)
- C5. Explicitly documents that, because `--live` is gated, the operator today:
  runs dry-run to preview → posts by hand on each platform → records with
  `mark_posted.py <slug> <channel> --posted-on <YYYY-MM-DD> --permalink <url>`.
  The existing manual `package.py` / `mark_posted.py` steps are **retained** in the
  skill, not deleted.

### 3.4 Live mode — documented as gated (future path)
- C6. Documents the live command form:
  `python3 tools/marketing-loops/publish_api.py --week <YYYY-Www> --live --date <YYYY-MM-DD> --i-have-verified-dry-run`.
- C7. Enumerates the **three live preconditions**, each explicitly, and cites
  `SETUP-CHECKLIST.md` as the founder dependency that unlocks them (B12):
  (a) a `.env` (default `./.env`, `--env PATH`) holding the channel tokens
  `IG_USER_ID`, `IG_ACCESS_TOKEN`, `LI_PERSON_URN`, `LI_ACCESS_TOKEN` (and, only
  with `--enable-facebook`, `FB_PAGE_ID`, `FB_PAGE_TOKEN`);
  (b) `PUBLIC_ASSET_BASE_URL` (from `.env` or `--public-asset-base-url`);
  (c) the explicit `--i-have-verified-dry-run` acknowledgment flag.
- C8. States that on a successful live post a row transitions `queued → posted` with
  the returned permalink + `--date` recorded, reusing the same `mark_posted`
  semantics (no re-post of an already-`posted` row) — B14/B15.
- C9. States the per-day cap: default 3 posts/day across channels, `--max-per-day N`
  override, keyed on `--date`; the breaching row is refused (B16).

### 3.5 Facebook flag and LinkedIn selector
- C10. Documents `--enable-facebook` as **default OFF**, labeled `round-5-gap`
  (unverified, best-documented guess — B30); with the flag OFF a `facebook` queue
  row is **skipped with a notice** and does not fail the run or block other channels
  (B31).
- C11. Documents `--linkedin-post-type {document,multi-image}` default `document`,
  and that exactly one LinkedIn flow runs per row (B25).

### 3.6 Exit codes for `publish_api.py`
- C12. Documents the three exit codes accurately (B40–B42):
  `0` success (dry-run plan emitted, or all selected rows posted+recorded);
  `1` domain refusal (already-`posted` row; IG container ERROR; rate-limit
  exceeded; day-cap breach) — cited on stderr;
  `2` usage/precondition (missing/invalid queue or package; unknown channel;
  `--live` missing any of the three gate items; malformed `--week`/`--date`; >10
  carousel children) — cited on stderr, no write.
- C13. Instruction to the skill agent: **report the tool's cited message verbatim;
  never auto-fix, never fabricate a permalink, never bypass the gate** (consistent
  with the existing skill's exit-code discipline).

### 3.7 Secrets discipline in the skill
- C14. States that tokens live only in the untracked `.env`, are never printed and
  never written to any tracked file, and appear as `<REDACTED>` in all output
  (B17/B18). No real token literal appears anywhere in the skill file.

---

## 4. Required content — `README.md`

- C15. Reconcile the stale "no posting APIs / human posts manually" sentence in the
  "Publish layer (Gap 2)" section (§2 above) so it is no longer contradicted by the
  new direct-publish subsection.
- C16. Add a subsection documenting `publish_api.py` as the **direct-publish
  (dry-run-first) layer**, placed logically within/after the "Publish layer (Gap 2)"
  section. It must contain, as greppable claims:
  - The default dry-run command form (runnable):
    `python3 tools/marketing-loops/publish_api.py --week 2026-W28 --dry-run`
    and the statement that dry-run is the DEFAULT, makes zero network calls, changes
    no queue state, and writes `content/publish-plan.json`.
  - That the plan faithfully renders the verified IG (two-step container),
    LinkedIn (`initializeUpload` + `/rest/posts`), and Facebook (round-5-gap) flows
    from `RESEARCH.md` R4-B/R5, with `<REDACTED>` secrets and named placeholders for
    response-dependent values — determinism: same inputs ⇒ byte-identical plan.
  - The `--live` command form and the **three preconditions** (a/b/c as in C7),
    naming `SETUP-CHECKLIST.md` as the founder dependency, and stating `--live` is
    **not usable today** (credentials absent).
  - `--enable-facebook` default OFF (round-5-gap), and exit codes `0/1/2` with the
    same meanings as C12.
  - A pointer that the `/loop-publish` skill wraps this flow and never bypasses the
    gate.
- C17. Every flag/default the README cites must match `--help` verbatim (see §6
  value table). No fabricated flags, no invented output blocks that will drift —
  show the **command**, describe the **behavior/values**, do not paste a full
  captured plan dump.

---

## 5. Value/flag table both docs MUST match `--help` verbatim

Any cited value that disagrees with this table (which is `publish_api.py --help`
ground truth as of Sprint 006) is a defect:

| Flag | Documented fact |
|---|---|
| `--week YYYY-Www` | REQUIRED run scope |
| `--dry-run` | DEFAULT when neither `--dry-run` nor `--live` given |
| `--live` | gated; requires `--date` + the three preconditions |
| `--date YYYY-MM-DD` | required in `--live`; never wall-clock |
| `--max-per-day N` | default **3**; breaching row refused (exit 1) |
| `--enable-facebook` | default **OFF**; round-5-gap adapter |
| `--linkedin-post-type` | `{document,multi-image}`, default **document** |
| `--linkedin-version` | default **202506** (fixed constant) |
| `--public-asset-base-url` | optional in dry-run; satisfies live gate (b) |
| `--env` | default **`.env`** |
| `--i-have-verified-dry-run` | live gate (c) |
| exit codes | **0** success / **1** domain refusal / **2** usage-precondition |

---

## 6. States that must be documented (not just happy path)

- **Dry-run success (default):** plan on stdout + `content/publish-plan.json`, queue
  untouched — documented in both files.
- **Live gate denied:** missing tokens / base URL / acknowledgment → exit 2, cited,
  no network — documented as the reason `--live` is not usable today.
- **Domain refusal:** already-`posted` row / day-cap breach → exit 1, cited —
  documented under exit codes.
- **Facebook flag OFF:** `facebook` row skipped with notice, other channels proceed
  — documented (C10).
- **Empty scope:** no `queued` rows for `--week` → exit 0, "nothing queued"
  (mention permitted but not required; if mentioned, must be accurate).

---

## 7. Non-goals (do NOT do these)

- No code changes to `publish_api.py` or any tool under `tools/`.
- No new flags, no changed defaults, no new API facts.
- No broad README rewrite — only reconcile the one stale claim and add the one
  publish_api subsection. Do not touch other loops' sections.
- No edits to other skills (`loop-create`, `loop-qa`, `loop-measure`, etc.).
- No pasted full plan-dump output that will drift from the tool; show commands and
  describe behavior instead.
- No `.env` example containing a real-looking token; if an env-key list is shown,
  keys only, values `<REDACTED>` / placeholder.

---

## 8. Commands the Evaluator runs (verification)

Run from the project root `/Users/prithviputta/Downloads/terrem-marketing-loops`.
Playwright: **N/A** (no browser surface).

1. **Docs exist and changed only the two files:**
   ```
   git status --porcelain
   ```
   Only `.claude/skills/loop-publish/SKILL.md` and `README.md` (plus harness
   bus/log files) appear; nothing under `tools/`, `content/`, no `.env`, no
   `publish-plan.json`.

2. **Stale-claim reconciliation:** confirm neither doc still asserts "no live
   posting API" / "no posting APIs … human posts manually" as a standing fact:
   ```
   grep -n "no live posting API" .claude/skills/loop-publish/SKILL.md
   grep -n "no posting APIs" README.md
   ```
   The old absolute claim must be gone/reworded (C1, C15).

3. **Greppable required claims present** in `SKILL.md`:
   ```
   grep -n "publish_api.py" .claude/skills/loop-publish/SKILL.md
   grep -n -- "--dry-run" .claude/skills/loop-publish/SKILL.md
   grep -n -- "--i-have-verified-dry-run" .claude/skills/loop-publish/SKILL.md
   grep -n "PUBLIC_ASSET_BASE_URL" .claude/skills/loop-publish/SKILL.md
   grep -n "SETUP-CHECKLIST" .claude/skills/loop-publish/SKILL.md
   grep -n -- "--enable-facebook" .claude/skills/loop-publish/SKILL.md
   grep -n "round-5-gap" .claude/skills/loop-publish/SKILL.md
   grep -n "REDACTED" .claude/skills/loop-publish/SKILL.md
   ```
   And in `README.md`:
   ```
   grep -n "publish_api.py" README.md
   grep -n -- "--live" README.md
   grep -n "SETUP-CHECKLIST" README.md
   grep -n -- "--enable-facebook" README.md
   ```

4. **Every documented command actually runs** — the default dry-run over the REAL
   queued asset (`2026-07-09-anarock-vs-propequity`, 2 queued rows, `2026-W28`):
   ```
   python3 tools/marketing-loops/publish_api.py --week 2026-W28 --dry-run
   echo "exit=$?"
   ```
   Must exit `0`, print a plan, and write `content/publish-plan.json`; the queue
   file is unchanged (`git status` clean for `content/publish-queue.json`). (The
   plan artifact is not committed — see §7 / `.gitignore` expectations.)

5. **Flag/default fidelity:** diff every value the docs cite against ground truth:
   ```
   python3 tools/marketing-loops/publish_api.py --help
   ```
   `--max-per-day` default 3, `--linkedin-post-type` default document,
   `--linkedin-version` default 202506, `--env` default `.env` — must match §5.

6. **Prior suites stay green** (docs sprint must not regress code):
   ```
   python3 -m unittest discover -s tools/marketing-loops/tests -v
   ```
   All prior tests pass (Sprints 001–006 green).

7. **No secret literal in either doc:**
   ```
   grep -nE "(EAAB|Bearer [A-Za-z0-9]{10,}|IGQ[A-Za-z0-9])" .claude/skills/loop-publish/SKILL.md README.md
   ```
   No hit (no real-looking token pasted into docs).

---

## 9. Acceptance criteria (all must hold)

- A1. Only the two doc files changed; no tool/content/secret artifact modified
  (§8.1).
- A2. Both stale "no posting API" claims reconciled, not merely appended (§8.2, C1,
  C15).
- A3. `SKILL.md` documents: dry-run default flow, the preserved manual flow, the
  gated live flow with all three preconditions + `SETUP-CHECKLIST.md`, the
  `--enable-facebook` round-5-gap default-OFF behavior, the LinkedIn selector, exit
  codes 0/1/2, and secrets discipline (C1–C14; §8.3).
- A4. `README.md` has an accurate `publish_api.py` direct-publish subsection with the
  runnable default dry-run command, the three live preconditions, the facebook flag,
  and exit codes (C15–C17; §8.3).
- A5. Every command shown in the docs runs as documented; the real-asset dry-run
  exits 0 and writes `content/publish-plan.json` with the queue untouched (§8.4).
- A6. Every flag/default cited matches `--help` verbatim (§8.5, §5).
- A7. Full prior unittest suite green (§8.6).
- A8. No secret literal in either doc; env keys shown as keys-only /
  `<REDACTED>` (§8.7, C14).

---

## 10. Explicit non-goals

- Not building or changing any API/adapter behavior — Sprints 001–006 own that.
- Not documenting Ayrshare/Buffer, OAuth acquisition, LinkedIn org posting, or
  public asset hosting (all spec §8 non-goals).
- Not adding a live run walkthrough with real tokens — live is documented as a
  future, gated path only.
- No Playwright / browser test — none exists for this CLI toolchain.
