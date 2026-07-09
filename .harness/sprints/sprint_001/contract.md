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
- `tests/test_enqueue.py:44` (`test_tgrera_enqueues_three_rows`) is ALREADY in
  the pre-existing failing baseline (§6, content drift). The tgrera `meta.md`
  `Channels:` line does not mention Facebook, so the new alias cannot change its
  enqueued channels — this sprint neither fixes nor further breaks it.

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
- **No new failure state:** the pre-existing failing set (§6) must not grow.

## 6. Frozen baseline — pre-existing failures (NOT this sprint's responsibility)

Captured before any Sprint-001 edit. Command:

```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'
```

Result: `Ran 254 tests … FAILED (failures=8, errors=1)`. The 9 failing tests:

```
ERROR: test_idempotent_byte_identical (test_enqueue.TestSuccessPath)
FAIL:  test_runner_exits_zero (test_acceptance.SmokeTest)
FAIL:  test_real_hyd_two_reasons_in_order (test_enqueue.TestGateRefusalNoWrite)
FAIL:  test_no_regress_posted_row (test_enqueue.TestSuccessPath)
FAIL:  test_tgrera_enqueues_three_rows (test_enqueue.TestSuccessPath)
FAIL:  test_populated_needs_review_and_checks_are_ignored (test_gate.TestPassingGate)
FAIL:  test_real_tgrera_passes (test_gate.TestPassingGate)
FAIL:  test_real_hyd_ground_truth (test_gate.TestTerminalAndOrder)
FAIL:  test_real_hyd_missing_verdict_and_killed (test_package.TestGateNeverBypassed)
```

Cause: real-content data drift — the `hyd-premium-vs-budget` asset is now
`KILLED`, `tgrera-enforcement-wave` was re-rendered (v2), and the new
`2026-07-09-anarock-vs-propequity` asset was added. None involve the channel
map. These are OUT OF SCOPE for Sprint 001 (see §8 Non-goals) and must NOT be
"fixed" by widening scope. The gate (§7) is defined as a DIFF against this
frozen set, not an absolute "green".

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

**Gate clause 2 — failing set does not grow (`after ⊆ before`):**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'
```
Expected: the ONLY failing tests are a subset of the 9 in §6. No new failing
test may appear. (Total test count may rise slightly from the new regression
cases; that is expected.)

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
- NO fixing the 9 pre-existing content-drift failures in §6 (out of scope; do
  not widen scope to touch `enqueue.py`, `gate.py`, `package.py`, `acceptance.py`
  or the real content assets).
- NO queue-schema change, NO renderer/QA-gate/caption-authoring change.
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
5. Full-suite run shows `failing(after) ⊆ failing(before)` (§6) — zero NEW
   failures.
6. Import is silent; no wall-clock; stdlib only; no scope creep beyond §2.
