# Contract — Sprint 002: Publish gate + QUEUE schema + enqueue

> Closes the first half of Gap 2 (spec §5.1): the four-condition publish **gate**
> (B-P1/B-P2), the versioned **QUEUE** schema + API seam (B-P8, §5.4 QUEUE), and
> **idempotent enqueue** (B-P3). This is a **CLI / library** deliverable, not a
> web app — there are no routes, screens, or Playwright paths. Verification is
> exact CLI invocations + exit codes + stdout/stderr substrings + on-disk JSON
> assertions, mirroring the DNA of `tools/marketing-render/` (`validate.py`,
> `acceptance.py`) and Sprint 001 (`utm.py`/`verify_utm.py`).

## 1. Scope (this sprint only)

Deliver the gate + enqueue foundation of the publish toolchain:

- An importable **gate** function that decides whether one asset folder may be
  queued, returning a structured result with exact cited reason codes (pure,
  no writes).
- The **QUEUE** schema materialized as a versioned JSON document (§5.4 QUEUE) —
  the single source of truth `/loop-publish` (Sprint 003) will consume.
- A thin **enqueue** CLI that runs the gate, refuses on failure with cited
  reasons and **no write**, and on a passing asset appends/updates one queue row
  per declared channel in state `queued` — idempotently.
- Unit tests + fixtures covering the passing path, every refusal condition, the
  multi-reason case, channel parsing, and idempotency/no-regress.

**Explicitly OUT of this sprint** (Sprint 003): publish package **file**
generation (caption assembly, PNG-path resolution from manifest), schedule-slot
computation (B-P6), mark-posted transition (B-P7), and the `/loop-publish`
skill (B-P9). See §7.

## 2. Files created / affected

Suggested layout (Generator may adjust names but MUST honor the behaviors, the
importable-gate requirement, and the fixtures-live-under-`tools/` rule):

- `tools/marketing-loops/gate.py` — **importable module**: a pure
  `gate_asset(asset_dir) -> result` function + reason-code constants. No CLI
  side effects on import. Sprint 003's package-gen and skill re-run this exact
  function (B-P9 "never bypasses the gate") — one function to import, not logic
  to duplicate.
- `tools/marketing-loops/queue.py` — **importable module**: QUEUE schema
  constants (`SCHEMA_VERSION`, state enum), plus pure load/merge/serialize
  helpers (deterministic ordering + JSON writing). No CLI side effects on
  import.
- `tools/marketing-loops/enqueue.py` — thin CLI importing `gate` + `queue` +
  the Sprint-001 `utm` channel map. Runs the gate, refuses or enqueues.
- `tools/marketing-loops/channels.py` — **importable module**: the free-text
  `Channels:` line parser (A-7), pinned in §3.5. (May instead live inside
  `queue.py`/`utm.py`; Generator chooses, but the alias table is authored once
  and imported, never duplicated.)
- `tools/marketing-loops/tests/test_gate.py`, `test_queue.py`,
  `test_channels.py`, `test_enqueue.py` — unit tests.
- `tools/marketing-loops/fixtures/publish/<fx-name>/` — gate/enqueue fixtures,
  each a full asset folder (`meta.md` + `render/qa-verdict.json` +
  `render/manifest.json` as applicable). Fixtures are asset folders **under
  `tools/`, never under `content/`** (putting them in `content/` would pollute
  real content and be picked up by the real toolchain).

Read-only (do NOT modify): `content/*`, `tools/marketing-render/*`,
`tools/marketing-loops/utm.py` (import it; the channel↔source map is the single
source of truth — do not fork it).

The default production queue path is `content/publish-queue.json` (created on
first real enqueue). It is a tracked source-of-truth artifact, not a secret; it
is NOT written during tests (tests pass `--queue <tmp>`; see §3.6).

## 3. Exact behaviors

### 3.1 The gate (`gate_asset`, importable) — B-P1 / B-P2

`gate_asset(asset_dir)` is a **pure** function (no writes, no wall-clock, no
network) returning a structured result:

```
{"slug": <str>, "ok": <bool>, "reasons": [ {code, message}, ... ]}
```

`ok` is `True` iff `reasons` is empty. An asset is refused (`ok=False`) if ANY
gate condition fails. The four conditions map to these **exact cited reason
codes** (the Evaluator asserts on the literal strings, mirroring Sprint 001's
violation taxonomy):

| Code | Trigger (spec B-P1/B-P2) |
|---|---|
| `missing-verdict` | `<asset>/render/qa-verdict.json` is absent, unparseable JSON, or missing the `verdict`/`failed_checks` keys. A corrupt/unreadable verdict is a **refusal**, never a silently-skipped pass. |
| `verdict-not-pass` | `qa-verdict.json` parses but its `verdict` field is not exactly `"PASS"` (string, case-sensitive). |
| `failed-checks-nonempty` | `qa-verdict.json` parses, `verdict == "PASS"`, but its `failed_checks` array is non-empty. (This is the second half of "FAIL-free PASS" — BOTH `verdict` and `failed_checks` are checked.) |
| `killed` | `<asset>/meta.md` contains a KILLED marker: a line matching `QA:\s*\*{0,2}KILLED` (case-sensitive `KILLED`). Presence anywhere in `meta.md` triggers refusal. |

**Terminal vs independent structure (mirrors Sprint 001):**

- If `qa-verdict.json` is absent/unparseable/missing keys → emit
  `missing-verdict` and do **not** additionally emit `verdict-not-pass` or
  `failed-checks-nonempty` (there is no trustworthy data to check those against).
- When the verdict parses, `verdict-not-pass` and `failed-checks-nonempty` are
  evaluated **independently** (a verdict that is both non-PASS and has failed
  checks reports both — though in practice a non-PASS verdict usually also has
  failed checks; the fixtures pin at least the two isolated cases).
- `killed` is **always** evaluated independently off `meta.md`, regardless of
  verdict state.
- Codes are emitted in this fixed order:
  `missing-verdict`, `verdict-not-pass`, `failed-checks-nonempty`, `killed`
  (deterministic; the Evaluator asserts order for multi-reason cases).

**Real-asset ground truth (the Evaluator will check these exactly):**

- `content/2026-07-03-tgrera-enforcement-wave` → `ok=True` (verdict PASS,
  `failed_checks: []`, meta not killed). Passes the gate.
- `content/2026-07-03-hyd-premium-vs-budget` → `ok=False`, reasons
  `[missing-verdict, killed]` (its `render/` has **no** `qa-verdict.json`, and
  its `meta.md` line 14 is `QA: **KILLED 2026-07-03** — ...`). Both codes, in
  order.

The gate must NOT enforce UTM validity — that is the Sprint-001 verifier /
B-A11's job, not one of the four B-P1 conditions. Keep the gate to exactly the
four conditions above.

Precondition (not a gate reason): if `asset_dir` does not exist or has no
`meta.md`, the gate cannot run → the CLI reports a usage error (exit 2, §3.6),
distinct from a domain refusal.

### 3.2 The QUEUE schema (§5.4 QUEUE, materialized) — B-P8

The single publish-queue document (default `content/publish-queue.json`):

```json
{
  "schema_version": "1",
  "rows": [
    {
      "slug": "<content folder slug>",
      "channel": "instagram|youtube|linkedin",
      "state": "queued|posted",
      "week": "YYYY-Www",
      "schedule_slot": null,
      "package_path": null,
      "posted_date": null,
      "permalink": null
    }
  ]
}
```

- `schema_version` is a fixed string constant (`"1"`), exactly like
  `manifest.json`/`qa-verdict.json`. This is the versioned seam.
- `state` is from the fixed enum `{queued, posted}` — the **API seam** (B-P8): a
  future live-posting adapter flips `state` and fills `posted_date`/`permalink`
  without reshaping the file. No posting-API field names are invented now.
- `channel` is one of the canonical `{instagram, youtube, linkedin}` values from
  the Sprint-001 `CHANNEL_SOURCE_MAP` keys (imported, not re-declared).
- **`schedule_slot` and `package_path` are nullable and are `null` at enqueue
  time this sprint.** Rationale (state this so the Evaluator reads it as
  deliberate schema authoring, not omission): §5.4 sketches these fields without
  `|null`, but they belong to a later lifecycle stage — `package_path`'s input
  is the package **file** written by B-P4 (Sprint 003), and `schedule_slot` is
  computed by B-P6 (Sprint 003). Writing a "planned" package path to a file that
  does not exist yet would be a dead reference; both fields are therefore
  correctly `null` until Sprint 003's package step populates them on the same
  rows. A queued-but-not-yet-packaged row is an honest lifecycle state, not a
  stub.
- `posted_date`/`permalink` are `null` until a human posts (mark-posted, B-P7,
  Sprint 003).
- **Row ordering is deterministic:** rows sorted by `(slug, channel)`
  ascending. **Row identity** is the `(slug, channel)` pair — at most one row
  per pair.
- Serialization is deterministic: JSON with `sort_keys=True`, `indent=2`, and a
  single trailing newline. Same inputs → byte-identical file.

### 3.3 Enqueue behavior (`enqueue.py` CLI) — B-P3

`python3 tools/marketing-loops/enqueue.py <asset_dir> --week YYYY-Www [--queue PATH]`

1. **Gate first.** Run `gate_asset(<asset_dir>)`.
   - If `ok=False` → print each cited reason (code + message) to **stderr**,
     write **nothing** to the queue (or create it), exit **1**. (B-P1: refusal =
     nonzero exit + cited reason + no write.)
   - If `ok=True` → proceed.
2. **Parse channels** from `<asset_dir>/meta.md` `Channels:` line per §3.5,
   producing an ordered, de-duplicated set of canonical channels.
3. **Load-or-init the queue** at `--queue` (default `content/publish-queue.json`).
   A missing file initializes to `{"schema_version":"1","rows":[]}`.
4. **Merge one row per channel** with `state="queued"`, `week=<--week>`,
   `schedule_slot=null`, `package_path=null`, `posted_date=null`,
   `permalink=null`:
   - If no row with this `(slug, channel)` exists → append it.
   - If a `queued` row already exists → leave it unchanged (idempotent; same
     bytes out).
   - If a `posted` row already exists → **do not regress it to `queued`** and do
     not clear its `posted_date`/`permalink`; leave it as-is (B-P3 no-regress).
5. **Write** the queue back deterministically (§3.2 serialization). Print a
   short summary to stdout, one stable line per row written/kept:
   `queued <slug> <channel>` (or `kept-posted <slug> <channel>` for a preserved
   posted row). Exit **0**.

Re-running the exact same command on the same asset + queue produces a
**byte-identical** queue file and identical stdout (idempotency).

`--week` is validated to match `^\d{4}-W\d{2}$` (ISO week). A missing or
malformed `--week` is a usage error (exit 2, §3.6). No `datetime.now()` anywhere.

### 3.4 KILLED marker match (B-P2)

- Match regex (case-sensitive `KILLED`): `QA:\s*\*{0,2}KILLED`.
- Matches the real hyd line `QA: **KILLED 2026-07-03** — ...` (meta.md line 14).
- Must **not** false-match: the tgrera `QA: PASS` line, nor lowercase prose such
  as `killed assets are data` (hyd line 25), nor `KILLED` appearing outside a
  `QA:` line context per the regex.

### 3.5 Channel parsing (A-7) — pinned

Parse the `Channels:` line of `meta.md` into the canonical set. **Alias table**
(case-insensitive token match), the ONLY tokens that map to a channel:

| Free-text token | Canonical channel |
|---|---|
| `IG`, `Instagram` | `instagram` |
| `YT`, `YouTube` | `youtube` |
| `LinkedIn` | `linkedin` |

Rules:

- **Format words are NOT channels and must NOT error:** `reel`, `short`,
  `carousel`, `PDF`, `text`, `post`, `variant`, `included`, and punctuation/join
  words (`+`, `,`, `(`, `)`) are ignored — they neither map nor trigger an
  "unmapped token" error.
- **Dedup:** each canonical channel yields exactly one entry regardless of how
  many aliases/format-variants mention it. `IG carousel + reel` → one
  `instagram`, not two.
- **Canonical order:** the resulting channel list is emitted in the fixed
  canonical order `instagram, youtube, linkedin` (deterministic; queue rows are
  then further sorted by `(slug, channel)` per §3.2).
- **Genuinely-unmappable channel-like token:** only a token that looks like a
  platform name but is not in the alias table (e.g. `Twitter`, `TikTok`,
  `Threads`) is surfaced — the CLI prints it and treats an asset whose
  `Channels:` line yields **at least one** unmapped platform token as a usage
  error (exit 2) rather than silently guessing or dropping it (A-7 "surfaced,
  not guessed"). Format words never count as unmapped.
- **Empty result:** if the `Channels:` line is absent, or yields **zero**
  canonical channels and zero unmapped platform tokens (nothing channel-like at
  all), that is a usage/precondition error (exit 2), never a silent zero-row
  enqueue.

**Real-asset ground truth:**

- tgrera `Channels: IG reel, YT short (LinkedIn text post variant included)` →
  `{instagram, youtube, linkedin}` (3 rows). `reel/short/text/post/variant/
  included` ignored.
- hyd `Channels: IG carousel + reel, YT short, LinkedIn PDF` →
  `{instagram, youtube, linkedin}` (but hyd is gate-refused, so never reached).

### 3.6 Exit codes (match render/Sprint-001 convention)

- `0` — success (gate passed and enqueue completed; idempotent re-run also 0).
- `1` — **domain failure**: gate refused the asset (one or more B-P1 reasons
  cited on stderr). No queue write.
- `2` — **usage / precondition error**: `<asset_dir>` missing or has no
  `meta.md`; `--week` missing or malformed; `Channels:` line yields an unmapped
  platform token or zero channels. Message on stderr, no queue write, empty
  stdout.

## 4. States

- **Empty:** enqueuing against a non-existent `--queue` path creates a valid
  `{"schema_version":"1","rows":[...]}` document (not left as a missing file);
  a hand-created queue may legitimately have `rows: []` and load cleanly.
- **Success (enqueue):** gate passes → one `queued` row per canonical channel,
  `schedule_slot`/`package_path`/`posted_date`/`permalink` all `null`.
- **Gate refusal:** missing/corrupt verdict, non-PASS verdict, non-empty
  `failed_checks`, or KILLED → exit 1, cited reason(s) on stderr, no write.
- **Idempotency:** re-run enqueue on same asset + queue → byte-identical file,
  no duplicate `(slug, channel)` rows.
- **No-regress:** a pre-existing `posted` row for `(slug, channel)` survives a
  re-enqueue unchanged (state stays `posted`, `posted_date`/`permalink` kept).
- **Invalid input:** malformed `--week`, missing `meta.md`, unmapped channel
  token → exit 2.
- **Offline:** no network; any network import is a defect.

## 5. Non-UI expectations (a11y / responsive / contrast do not apply)

Headless CLI. In place of keyboard/focus/ARIA/contrast/responsive:

- **Usability:** refusal and error messages are specific and recoverable — each
  names the asset, the reason code, and the concrete fact (e.g. `verdict was
  'FAIL', expected 'PASS'`; `qa-verdict.json not found at <path>`), never a bare
  "refused".
- **Runs from any cwd:** paths resolved from `__file__` (as `validate.py` and
  Sprint-001 tools do); `<asset_dir>` and `--queue` accept absolute or relative
  paths and work from repo root or elsewhere.
- **Import safety:** importing `gate`, `queue`, or `channels` has no side
  effects and prints nothing.
- **Single source of truth:** channel↔source map imported from Sprint-001
  `utm.CHANNEL_SOURCE_MAP`; the schema version constant lives once in `queue.py`.

## 6. Security / privacy

- Stdlib only (`json`, `re`, `pathlib`, `argparse`). No third-party deps. No
  network. No secrets. No personal data written. `qa-verdict.json`/`meta.md`
  inputs treated as untrusted text (unparseable verdict → `missing-verdict`
  refusal, never a crash). No dependency on the globally-installed
  `pmp-gywd@5.0.0` npm package.
- The default `content/publish-queue.json` is a tracked, non-secret artifact.
  Tests write only to temp `--queue` paths and never mutate real `content/`.

## 7. Explicit non-goals (this sprint)

- **No package file generation** (B-P4/B-P5): no caption assembly, no per-channel
  UTM-link substitution, no PNG-path resolution from `manifest.json`, no package
  `.json`/`.md` files written. `package_path` stays `null`. (Sprint 003.)
- **No schedule-slot computation** (B-P6): `schedule_slot` stays `null`; the
  A/B-bucket / per-channel-time rule is NOT defined or pinned here. (Sprint 003.)
- **No mark-posted** (B-P7): no `queued → posted` transition command. This
  sprint only *preserves* a pre-existing `posted` row; it never creates one.
- **No `/loop-publish` skill** (B-P9). (Sprint 003.)
- **No UTM validity in the gate** — the four B-P1 conditions only.
- **No analytics / CSV / scorecard** (Sprints 004–006).
- **No modification** of `content/*`, `tools/marketing-render/*`, or
  `tools/marketing-loops/utm.py` behavior/contract.

## 8. Commands to run

```bash
cd /Users/prithviputta/Downloads/terrem-marketing-loops
TMPQ="$(mktemp -d)/queue.json"

# Unit tests (must pass)
python3 -m unittest discover -s tools/marketing-loops/tests -v

# Real PASS asset enqueues 3 channel rows -> exit 0
python3 tools/marketing-loops/enqueue.py \
  content/2026-07-03-tgrera-enforcement-wave --week 2026-W27 --queue "$TMPQ" ; echo "exit=$?"
cat "$TMPQ"    # expect schema_version "1"; 3 rows (instagram/linkedin/youtube), state queued, slot+package null

# Idempotency: re-run -> byte-identical file, exit 0
shasum "$TMPQ"; python3 tools/marketing-loops/enqueue.py \
  content/2026-07-03-tgrera-enforcement-wave --week 2026-W27 --queue "$TMPQ" ; shasum "$TMPQ"

# Real KILLED + missing-verdict asset refused -> exit 1, reasons [missing-verdict, killed], no write
python3 tools/marketing-loops/enqueue.py \
  content/2026-07-03-hyd-premium-vs-budget --week 2026-W27 --queue "$TMPQ" ; echo "exit=$?"

# Usage errors -> exit 2
python3 tools/marketing-loops/enqueue.py content/does-not-exist --week 2026-W27 ; echo "exit=$?"
python3 tools/marketing-loops/enqueue.py \
  content/2026-07-03-tgrera-enforcement-wave --week 2026-Q3 --queue "$TMPQ" ; echo "exit=$?"

# Import-safety: gate/queue import prints nothing
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); import gate, queue; print(queue.SCHEMA_VERSION)"
```

## 9. Evaluator attack checklist (CLI, not Playwright)

Fixtures shipped under `tools/marketing-loops/fixtures/publish/` (each a full
asset folder). Required fixtures + expected result:

| Fixture intent | Expected |
|---|---|
| PASS asset, 3 channels (positive control) | gate `ok`; enqueue writes 3 rows, exit 0 |
| verdict PASS, one channel | gate `ok`; enqueue writes 1 row, exit 0 |
| `render/qa-verdict.json` absent | refuse `missing-verdict`, exit 1, no write |
| `qa-verdict.json` present, unparseable JSON | refuse `missing-verdict`, exit 1 |
| `verdict: "FAIL"` | refuse `verdict-not-pass`, exit 1 |
| `verdict: "PASS"`, `failed_checks: [{...}]` non-empty | refuse `failed-checks-nonempty`, exit 1 |
| `meta.md` with `QA: **KILLED ...**` marker | refuse `killed`, exit 1 |
| missing verdict **and** KILLED (mirrors real hyd) | refuse `[missing-verdict, killed]` in order, exit 1 |
| `Channels:` mentions `Twitter` (unmapped platform) | usage error, exit 2 |
| `Channels:` with only format words / no channel | usage error, exit 2 |

Adversarial probes the Evaluator should run:

1. Enqueue real tgrera to a temp queue → exit 0; assert exactly 3 rows,
   channels `{instagram, youtube, linkedin}`, every row `state=queued`,
   `schedule_slot=null`, `package_path=null`, `posted_date=null`,
   `permalink=null`, `schema_version="1"`.
2. Re-run the same enqueue → `shasum` byte-identical; no duplicate rows.
3. Pre-seed a queue with a `posted` row for `(tgrera, instagram)` (date +
   permalink filled), re-enqueue → that row stays `posted` with its fields
   intact; the other two channels are added as `queued`.
4. Real hyd → exit 1, stderr cites `missing-verdict` then `killed`, and the temp
   queue file is **unchanged / not created** (assert no write on refusal).
5. Each single-defect fixture → exit 1 with its exact code; assert no write.
6. `failed-checks-nonempty` fixture proves BOTH halves of FAIL-free PASS are
   checked (verdict PASS but failed_checks populated still refuses).
7. Malformed `--week` and missing `meta.md` and unmapped-channel fixture → exit
   2, stderr message, empty stdout, no write.
8. Determinism: enqueue two different assets into one queue in either order →
   identical final file (rows sorted by `(slug, channel)`).
9. Import `gate`/`queue`/`channels` → no stdout; `queue.SCHEMA_VERSION == "1"`;
   channel map is the imported Sprint-001 `CHANNEL_SOURCE_MAP` (no forked copy).
10. Grep the source for `datetime.now`, `requests`, `urlopen`, `socket`, network
    `urllib` → none present (behavioral: no wall-clock in any output, no network).

## 10. Definition of done

- `gate.py` exposes an importable pure `gate_asset()` returning `{slug, ok,
  reasons}` with the four exact reason codes and the terminal/independent
  structure of §3.1; no import side effects.
- `queue.py` materializes the versioned QUEUE schema (§3.2) with deterministic
  ordering + serialization; `SCHEMA_VERSION` lives here once.
- `channels.py` (or equivalent) implements the pinned §3.5 alias table, dedup,
  format-word tolerance, unmapped-token surfacing, and empty→exit-2 rule.
- `enqueue.py` runs gate → refuse(1)/usage(2)/enqueue(0), idempotent and
  no-regress per §3.3, writing deterministic queue JSON.
- Fixtures for every §9 row shipped under `tools/marketing-loops/fixtures/publish/`.
- Unit tests prove each reason code fires on its fixture, the multi-reason order,
  channel parsing (incl. real tgrera → 3 channels), idempotency, no-regress, and
  the three exit codes; all pass.
- Real tgrera enqueues (temp queue) at exit 0 with 3 correct rows; real hyd is
  refused at exit 1 with `[missing-verdict, killed]` and no write.
- Evidence (command output, exit codes, before/after `shasum`, sample queue
  JSON) logged in `generator_trace.log`.
