# Sprint 001 Contract — Frozen-module extension: add `facebook`

Scope: spec §5.8 (B33–B37), §10.7. This sprint adds `facebook` as a first-class
channel across the frozen shared modules and consciously updates every test that
asserts the exact old channel set. **No `publish_api.py`, no adapters, no CLI, no
transport this sprint** — those are Sprints 002+. This is a pure
library/data-map change plus test updates.

Ground truth read: `RESEARCH.md` R4-B/R5 (facebook is a round-5 gap; this sprint
only reserves its slot in the channel universe — it does NOT build the FB
adapter). `PIPELINE-V2.md` §6.

---

## 1. Exact user-visible behaviors (all testable via `python3 -m unittest`)

This is a CLI-toolchain internals change; the "user" is the rest of the
toolchain and its test suite. There is no browser surface (Playwright: N/A —
see §9).

### B33 — `utm.CHANNEL_SOURCE_MAP` gains `facebook`, appended LAST
- After change, `utm.CHANNEL_SOURCE_MAP` equals, in this exact insertion order:
  `{"instagram": "instagram", "youtube": "youtube", "linkedin": "linkedin", "facebook": "facebook"}`.
- Ordinals are PRESERVED: `tuple(utm.CHANNEL_SOURCE_MAP).index("instagram") == 0`,
  `…index("youtube") == 1`, `…index("linkedin") == 2`, `…index("facebook") == 3`.
- `utm.ALLOWED_SOURCES` (derived) now contains `"facebook"`; still equals
  `frozenset(CHANNEL_SOURCE_MAP.values())` (no second literal list).
- No other line of `utm.py` changes. `validate_flywheel`/`validate_asset`
  behavior for the existing three channels is byte-identical.

### B34 — `channels.py._ALIASES` gains `facebook` and `fb`
- `channels.parse_channels_line("Facebook post")` returns `(["facebook"], [])`
  (previously returned `([], ["Facebook"])` — i.e. an unmapped platform token
  that the CLI would surface as exit 2). Case-insensitive: `"FB reel"` →
  `(["facebook"], [])`.
- `channels.CANONICAL_CHANNELS` (derived from the map) is now the 4-tuple
  `("instagram", "youtube", "linkedin", "facebook")`.
- A mixed line keeps canonical order:
  `channels.parse_channels_line("Facebook, IG, LinkedIn")` →
  `(["instagram", "linkedin", "facebook"], [])`.
- Existing alias/format-word/unmapped behavior for the first three is unchanged
  (e.g. `"IG reel, Twitter post, YT short"` still surfaces `["Twitter"]`).

### B35 — `schedule.py._TIMES` gains a `facebook` entry
- `schedule.slot_for("2026-W27", "facebook")` returns a well-formed slot string
  `"2026-W27/<bucket>/<HH:MM>"` and does NOT raise `KeyError`.
- Bucket math for facebook uses ordinal 3:
  `bucket = morning if (WW + 3) % 2 == 0 else evening`. For `2026-W27`
  (WW=27): `(27+3)%2 == 0` → `morning`. The `_TIMES["facebook"]` morning/evening
  times are fixed documented A/B-hypothesis constants (module-authored, same
  shape as the existing three; NOT wall-clock derived). Both bucket values must
  be present so neither bucket KeyErrors.
- `slot_for` for instagram/youtube/linkedin returns byte-identical strings to
  before (ordinals unchanged ⇒ buckets unchanged).

### B36 — `captions.py` and `queue.py` pick facebook up automatically (verify; expect NO code change)
- `queue.VALID_CHANNELS` (derived) now contains `"facebook"`;
  `queue.new_row("2026-07-09-x", "facebook", "2026-W28")` succeeds and returns a
  valid queued row (previously raised `ValueError: unknown channel`).
- `captions.body_for({}, "facebook")` returns `None` (does NOT raise
  `ValueError: unknown channel`); `captions.body_for({"all": "hi"}, "facebook")`
  returns `"hi"`.
- If either module needs a code edit to pass the above, that is a finding — the
  contract expectation is these are already map-derived and need none.

### B37 — Consciously update every exact-old-channel-set assertion; suite discipline
See §4 for the enumerated, triaged site list (must-update vs must-stay-green).

---

## 2. Files affected

Production (edit):
- `tools/marketing-loops/utm.py` — append `"facebook": "facebook"` to
  `CHANNEL_SOURCE_MAP` (last key only; nothing else).
- `tools/marketing-loops/channels.py` — add `"facebook": "facebook"` and
  `"fb": "facebook"` to `_ALIASES`.
- `tools/marketing-loops/schedule.py` — add
  `"facebook": {BUCKET_MORNING: "<HH:MM>", BUCKET_EVENING: "<HH:MM>"}` to
  `_TIMES`.

Production (verify, expect no edit): `queue.py`, `captions.py`.

Tests (edit — see §4): `tests/test_utm.py`, `tests/test_channels.py`.

Tests (add — new regression cases, may live in the existing files):
- utm: facebook is the 4th key with ordinal 3; ALLOWED_SOURCES contains facebook.
- channels: `"Facebook"` and `"FB"` map to `["facebook"]`; mixed-order canonical.
- schedule: `slot_for(week, "facebook")` no KeyError, correct bucket for W27.
- queue: `new_row(..., "facebook", ...)` succeeds; VALID_CHANNELS has facebook.
- captions: `body_for` on facebook returns None / all-block, no raise.

---

## 3. Data / state transitions

None. This sprint mutates only in-memory constants and test literals. No queue
file is written, no network, no wall-clock read, no new persisted artifact. The
publish queue schema (`schema_version "1"`) is unchanged (spec §8, §9).

---

## 4. Test-site enumeration (B37) — triaged

Baseline evidence for this triage was captured by grepping every
channel-set literal in `tests/` and reading `ingest.py`.

### 4a. MUST UPDATE — exact old-channel-set literal assertions (will break)
| Site | Current assertion | Required new assertion |
|---|---|---|
| `tests/test_utm.py:39-40` | `sorted(CHANNEL_SOURCE_MAP) == ["instagram","linkedin","youtube"]` | `== ["facebook","instagram","linkedin","youtube"]` |
| `tests/test_channels.py:27-28` | `CANONICAL_CHANNELS == ("instagram","youtube","linkedin")` | `== ("instagram","youtube","linkedin","facebook")` |

### 4b. MUST STAY GREEN — derived-from-map assertions (auto-pass, no edit)
These assert equality to `utm.CHANNEL_SOURCE_MAP.keys()`, so they track the map
automatically once B33 lands. The Evaluator must confirm they still pass:
- `tests/test_channels.py:25-26` (`CANONICAL_CHANNELS == tuple(utm...keys())`)
- `tests/test_queue.py:29-30` (`VALID_CHANNELS == frozenset(utm...keys())`)
- `tests/test_schedule.py:61-62` (`CANONICAL_CHANNELS == tuple(utm...keys())`)
- `tests/test_utm.py:42-44` (`ALLOWED_SOURCES == frozenset(...values())`)

### 4c. MUST STAY GREEN — pure iterations over the three literals (unaffected)
These loop `("instagram","youtube","linkedin")` explicitly and never assert the
FULL channel set, so a 4th channel does not touch them. The Evaluator confirms
none KeyErrors on a 4th channel:
- `tests/test_csvspec.py:32`, `tests/test_package.py:43/214/231`,
  `tests/test_scorecard.py:209`, `tests/test_captions.py:112`.

### 4d. NOT map-derived — confirmed unaffected
- `tests/test_ingest.py:37/52/64` assert the dict
  `{"instagram":None,"youtube":None,"linkedin":None,"site":None}`. `ingest.py`
  builds its source set from a HAND-AUTHORED literal
  `("instagram","youtube","linkedin","site")` (grep: `ingest.py:78/85/209`), NOT
  from `CHANNEL_SOURCE_MAP`. This is the Gap-3 analytics source set (includes
  `site`, has no notion of facebook). Appending facebook to the map does not
  touch it. These stay green.
- `tests/test_enqueue.py:44` (`test_tgrera_enqueues_three_rows`) asserts the
  enqueued channel set equals `["instagram","linkedin","youtube"]` (three
  channels). This test PASSES in the current baseline (§6 confirms 254 OK, zero
  failures). The real tgrera `meta.md` `Channels:` line is
  `IG reel, YT short (LinkedIn text post variant included)` — it does NOT mention
  Facebook, so the new `facebook`/`fb` alias cannot change what tgrera enqueues:
  it will continue to enqueue exactly three rows after Sprint 001. This test
  therefore stays GREEN and needs no edit — Facebook cannot alter its outcome.
  (Verified: `grep -in 'channels:' content/2026-07-03-tgrera-enforcement-wave/meta.md`.)

If BUILD reveals a channel-set assertion not listed here, it must be updated too
(B37: "enumerate all, do not stop at these") and recorded in the trace.

---

## 5. Empty / loading / success / error / invalid states

- **Success:** the five channel-map-touching test files are fully green with
  facebook present (§7 gate clause 1).
- **Invalid / KeyError guard:** no code path KeyErrors on a 4th channel —
  `slot_for(week,"facebook")`, `new_row(...,"facebook",...)`,
  `body_for(...,"facebook")` all succeed (§10.7 risk closed).
- **Unmapped-token behavior preserved:** a genuinely unknown platform (e.g.
  `Twitter`, `TikTok`) is STILL surfaced as unmapped by `channels.py` — adding
  facebook must not turn the unmapped-surfacing off for other tokens.
- **No new failure state:** both suites stay fully green (§6).

## 6. Baseline — both suites are green

As of orchestrator commit `201456c` (stray qa-verdict artifact removed from the
KILLED hyd asset; TGRERA's `qa-verdict.json` regenerated after the acceptance
re-render wiped it), both suites pass with zero failures:

```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'   # loops: 254 OK
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'   # (render suite: 266 OK)
```

The gate is therefore the simple one: **both suites stay green, or are
consciously extended.** The only conscious extensions this sprint authors are
the two exact-set literal updates in §4a plus the new facebook regression cases
in §2. Any test that goes red and is NOT one of those §4a updates is a
regression this sprint must fix, not accept.

## 7. Verification — commands the Evaluator runs

All from repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`.

**Gate clause 1 — channel-map-touching files fully green:**
```
python3 -m unittest -v \
  tools.marketing-loops.tests.test_utm \
  tools.marketing-loops.tests.test_channels \
  tools.marketing-loops.tests.test_schedule \
  tools.marketing-loops.tests.test_queue \
  tools.marketing-loops.tests.test_captions
```
(If the dotted path fails due to the hyphen in `marketing-loops`, use:
`python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_utm.py'`
and repeat per file, or run each file directly with
`python3 tools/marketing-loops/tests/test_utm.py`.) Expected: OK, 0 failures.

**Gate clause 2 — both suites stay green:**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'
```
Expected: `OK`, zero failures/errors. (Total test count may rise slightly from
the new regression cases; that is expected.) The render suite (266 OK) must
also remain green — Sprint 001 touches no renderer code, so confirm it is
untouched.

**Gate clause 3 — no KeyError / crash from a 4th channel; behaviors hold:**
```
python3 - <<'PY'
import sys; sys.path.insert(0, "tools/marketing-loops")
import utm, channels, schedule, queue, captions
assert list(utm.CHANNEL_SOURCE_MAP) == ["instagram","youtube","linkedin","facebook"]
assert "facebook" in utm.ALLOWED_SOURCES
assert channels.parse_channels_line("Facebook post") == (["facebook"], [])
assert channels.parse_channels_line("FB reel") == (["facebook"], [])
assert channels.CANONICAL_CHANNELS == ("instagram","youtube","linkedin","facebook")
assert schedule.slot_for("2026-W27","facebook").startswith("2026-W27/")
assert queue.new_row("2026-07-09-x","facebook","2026-W28")["state"] == "queued"
assert "facebook" in queue.VALID_CHANNELS
assert captions.body_for({}, "facebook") is None
assert captions.body_for({"all":"hi"}, "facebook") == "hi"
# ordinals preserved for the original three:
assert schedule.slot_for("2026-W27","instagram") == schedule.slot_for("2026-W27","instagram")
print("OK")
PY
```
Expected: prints `OK`, exit 0.

**Import-silence (no CLI side effect / stdout on import) — spec §9 discipline:**
```
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); import utm, channels, schedule" 
```
Expected: exit 0, empty stdout.

## 8. Non-goals (explicit)

- NO `publish_api.py`, transport seam, adapters, dry-run plan, or CLI flags
  (Sprints 002–006).
- NO Facebook adapter / photos+feed flow (Sprint 005; round-5 gap, gated).
- NO renderer / QA-gate / acceptance / content-asset changes; do not touch
  `enqueue.py`, `gate.py`, `package.py`, `acceptance.py`, `render.py`, or any
  real content asset. This sprint is confined to the channel-map seam (§2).
- NO queue-schema change, NO caption-authoring change.
- NO new dependency; stdlib only.
- NO wall-clock read anywhere.

## 9. Non-applicable sections

- Playwright / browser click paths: N/A — this sprint has no HTTP surface, no
  route, no rendered screen. Verification is unittest + the inline probe scripts
  in §7.
- Keyboard/focus/ARIA/contrast/responsive: N/A — no UI.
- Security/privacy: no secrets introduced this sprint; `.env` handling arrives
  in Sprint 002. Confirm `git status --porcelain` shows only the intended
  source/test edits and no secret/artifact files.

## 10. Security / hygiene assumptions

- No credentials, tokens, or `.env` values touched or created this sprint.
- `.gitignore` already covers `.env` (spec B18); unchanged here.
- The only writes are to source files under `tools/marketing-loops/` and their
  tests — no generated artifacts, no db, no uploads.

## 11. Acceptance summary (the contract's testable core)

Sprint 001 passes iff ALL hold:
1. `facebook` is the 4th key of `utm.CHANNEL_SOURCE_MAP` (ordinal 3), map is the
   sole source of truth (no forked list), ordinals 0/1/2 preserved.
2. `channels.parse_channels_line` maps `Facebook`/`FB` → `["facebook"]`; other
   unmapped platforms still surfaced.
3. `schedule.slot_for(week,"facebook")`, `queue.new_row(...,"facebook",...)`,
   `captions.body_for(...,"facebook")` all succeed without KeyError/ValueError.
4. The two exact-set literal assertions (§4a) are updated and green; the
   derived-map assertions (§4b) stay green with no edit.
5. Both suites stay fully green (loops 254 OK, render 266 OK), consciously
   extended only by the §4a updates and the new facebook regression cases.
6. Import is silent; no wall-clock; stdlib only; no scope creep beyond §2.

## 12. Risks

- **Re-render wipes qa-verdict (orchestrator note).** `render.py` re-rendering
  an asset wipes `render/qa-verdict.json`; any step that re-renders MUST
  re-validate (regenerate the verdict) afterward or the acceptance/gate suites
  go red. Sprint 001 does not re-render anything, so it is not exposed — but any
  later sprint or repair that touches rendering must honor this.
- **Ordinal preservation (§10.7).** `facebook` MUST be appended LAST so schedule
  bucket math for the existing three (ordinals 0/1/2) is byte-identical.
- **Hyphenated package path.** `tools/marketing-loops` is not a valid dotted
  module path; §7 gives `discover`/direct-run fallbacks.
