# Sprint 002 Contract — Transport seam + dry-run plan renderer + CLI skeleton

Scope: spec §11 Sprint 002. Builds the `publish_api.py` **skeleton**: the
injectable HTTP transport (single `urlopen` call site), the CLI argument surface
(all flags, frozen now), the `.env` loader, the `--live` precondition gate
(B12), row selection from the queue (B2/B3), the deterministic plan model +
`publish-plan.json` writer (B6/B7/B9), and the reusable placeholder (B10) and
redaction (B17) helpers. **No channel adapters this sprint** — Instagram (003),
LinkedIn (004), Facebook (005), live posting / queue transition / day-cap (006)
are explicitly out of scope (§8 below). The adapter registry ships EMPTY; a
selected row therefore renders in the plan with an empty step list.

Ground truth read: `RESEARCH.md` R4-B/R5, `PIPELINE-V2.md` §6, and the Sprint 001
frozen-module extension (facebook is a valid channel in the map now, but the FB
adapter is not built until 005). This is a stdlib CLI + JSON tool; there is no
browser surface (Playwright: N/A — see §11).

---

## 1. What this sprint delivers (the testable core)

A new file `tools/marketing-loops/publish_api.py`, stdlib-only, consistent with
the existing `tools/marketing-loops/` toolchain (`_HERE = Path(__file__)
.resolve().parent; sys.path.insert(0, str(_HERE))` import pattern, run-from-any-
cwd, exit-code convention `0/1/2`). It must be importable with silent stdout on
import and expose a `main(argv=None) -> int` and a testable `run(...)` seam
following the EXACT house pattern of `mark_posted.py` (verified: `mark_posted.run`
returns `(exit_code, stdout_lines, stderr_lines)` and `main` does all the
printing).

### 1.1 Module interface (exact signatures — resolves reviewer F-010, F-002)
The module exposes these two entry points, and NO others are relied on by tests:

```python
def run(
    week,                            # str, required, "YYYY-Www"
    slug=None,                       # str | None  scope narrow
    channel=None,                    # str | None  scope narrow (must be in queue.VALID_CHANNELS)
    mode="dry-run",                  # "dry-run" | "live"
    queue_path="content/publish-queue.json",
    date=None,                       # str | None  "YYYY-MM-DD"
    max_per_day=3,                   # int >= 1
    enable_facebook=False,           # bool
    linkedin_post_type="document",   # "document" | "multi-image"
    public_asset_base_url=None,      # str | None
    env_path=".env",                 # str
    i_have_verified_dry_run=False,   # bool
    transport=None,                  # Transport | None  (TEST SEAM — see s8.1)
):
    """Run the publish pipeline. Returns (exit_code:int, stdout_lines:list[str],
    stderr_lines:list[str]). Buffers all output as line lists (no direct print),
    exactly like mark_posted.run. When transport is None, run() constructs the
    default Transport(); tests pass RecordingTransport()/RaisingTransport()."""

def main(argv=None):
    """CLI entry point. Builds the argparse surface (s3.1), maps parsed args to
    run(...) keyword args (argparse dest names -> run params), then writes
    stdout_lines to sys.stdout and stderr_lines to sys.stderr and returns the
    exit code. main NEVER passes a transport (always the live default);
    transport injection is a run()-only test seam."""
```

- Tests invoke `run(...)` directly (with a `transport=` for the no-network
  proofs) OR invoke the CLI via `subprocess.run([... argv ...])` as `test_utm.py`
  does. Both are supported; the argparse dest→run-kwarg mapping is 1:1 by name.
- `main` returning `int` and `run` returning the 3-tuple is the frozen contract
  for downstream sprints; 003+ extend `run` internals, never its signature shape
  (adapter-specific knobs, if any later needed, arrive as new optional kwargs
  appended LAST, never reordering existing params).

Because no adapters exist yet, the observable behaviors this sprint locks are:
CLI parsing + validation, the live gate, queue row selection + scope filtering,
the empty-state message, the plan envelope + deterministic writer, the transport
seam (provably one `urlopen` call site, never touched in dry-run), and the
placeholder/redaction/image_url helper functions.

---

## 2. Files affected

Production (add):
- `tools/marketing-loops/publish_api.py` — the new CLI + transport + plan model
  + helpers. The ONLY production file added this sprint.

Tests (add):
- `tools/marketing-loops/tests/test_publish_api.py` — new suite covering every
  behavior in §3–§7 below, mocked transport only, following the existing test
  header convention (`_TESTS_DIR/_TOOL_DIR` sys.path insert; `subprocess.run`
  with `cwd=_REPO_ROOT` for CLI-level checks, as `test_utm.py` does).

No edits to any frozen module, no edits to any existing test, no content-asset
changes. If BUILD finds a frozen module needs a change to satisfy this contract,
that is a finding to disclose — none is expected.

---

## 3. CLI shape and argument validation (B1, B3, B42-subset)

### 3.1 Flags — the full surface, frozen now
`main`/`run` parse ALL of the following. Each flag is tagged **[F]** functional
this sprint or **[P]** parsed-and-validated now but only consumed by a later
sprint (still validated — an unvalidated parsed-only flag is a dead button):

| Flag | Kind | This sprint |
|---|---|---|
| `--week YYYY-Www` (required) | **[F]** | scope filter + format-validated |
| `--slug SLUG` | **[F]** | scope narrow |
| `--channel CHANNEL` | **[F]** | scope narrow; must be a member of `queue.VALID_CHANNELS` else exit 2 |
| `--dry-run` | **[F]** | default mode selector |
| `--live` | **[F]** | triggers the gate (§4) |
| `--queue PATH` | **[F]** | default `content/publish-queue.json` |
| `--date YYYY-MM-DD` | **[P]** | format-validated now (real calendar date, like `mark_posted`); required only in `--live` (§4); consumed for posting/day-cap in 006 |
| `--max-per-day N` | **[P]** | OPTIONAL; `argparse type=int, default=3`. If provided it must parse as int ≥ 1 else exit 2 ("--max-per-day must be an integer >= 1"). When omitted, `run` receives the default `3`. Day-cap enforced in 006 (resolves reviewer F-006) |
| `--enable-facebook` | **[P]** | boolean; FB adapter/skip logic in 005 |
| `--linkedin-post-type {document,multi-image}` | **[P]** | `argparse choices`; default `document`; junk value → exit 2; flow selection in 004 |
| `--public-asset-base-url URL` | **[F]** | used by the image_url helper (§8) + satisfies gate (b); optional in dry-run |
| `--env PATH` | **[F]** | default `./.env`; consumed by the loader + gate |
| `--i-have-verified-dry-run` | **[F]** | acknowledgment flag for the gate (§4) |

- `--dry-run` is the DEFAULT: when neither `--dry-run` nor `--live` is passed,
  the tool is in dry-run (B6). Passing BOTH `--dry-run` and `--live` is a usage
  error → exit 2, cited.
- `--help` documents every flag, tags [F]/[P] equivalently (e.g. "consumed in a
  later sprint"), and states the three `--live` preconditions (§4). No flag is
  undocumented.

### 3.2 `--week` validation (B3)
- `--week` is REQUIRED. Absent → argparse usage error (exit 2).
- Format must match `^\d{4}-W\d{2}$` (e.g. `2026-W28`). Malformed (`2026-28`,
  `2026-W5`, `garbage`) → exit 2 on stderr, cited, no write, no network.

### 3.3 `--date` validation (B42-subset, [P])
- When provided (any mode) it must match `^\d{4}-\d{2}-\d{2}$` AND be a real
  calendar date (`datetime.strptime(..., "%Y-%m-%d")`, parsing the SUPPLIED
  value only — never the wall clock, mirroring `mark_posted.py`). Malformed →
  exit 2, cited.
- Not required in dry-run. Required in `--live` (§4c precondition is the ack
  flag; `--date` requirement is enforced as its own exit-2 precondition in live,
  cited "--live requires --date YYYY-MM-DD"). In dry-run `--date` is optional and
  otherwise inert this sprint.

---

## 4. Live-mode precondition gate (B12, B13) — the safety core

`--live` requires ALL THREE below, each checked INDEPENDENTLY with its own cited
stderr message. If any fails: exit 2, ZERO network, ZERO queue write, ZERO
plan write. (The gate runs before any adapter dispatch; since no adapters exist,
a passing gate still posts nothing — see §5.)

- **(a) `.env` tokens.** A `.env` file (default `./.env`, `--env PATH`) must
  exist and hold the tokens required by the channels IN SCOPE for this run.

  **Definition of "in scope" (resolves reviewer F-005):** the set of DISTINCT
  `channel` values of the rows remaining AFTER scope filtering by
  `--week` + `--slug` + `--channel` (i.e. the exact rows this run would act on) —
  NOT all `queue.VALID_CHANNELS`, NOT every channel present in the queue file.
  Example: `--week 2026-W28 --channel linkedin` on a queue holding both an
  instagram and a linkedin queued row selects only the linkedin row, so the
  in-scope set is `{"linkedin"}` and ONLY `LI_PERSON_URN`/`LI_ACCESS_TOKEN` are
  required (instagram tokens are NOT required). Token requirements keyed on this
  set:
  - `"instagram"` in the in-scope set → require `IG_USER_ID`, `IG_ACCESS_TOKEN`
  - `"linkedin"` in the in-scope set → require `LI_PERSON_URN`, `LI_ACCESS_TOKEN`
  - `"facebook"` in the in-scope set AND `--enable-facebook` passed → require
    `FB_PAGE_ID`, `FB_PAGE_TOKEN`. A facebook row in scope WITHOUT
    `--enable-facebook` requires no FB tokens (that row's skip-with-notice is
    Sprint 005; it does not gate live tokens here).
  - Empty in-scope set (nothing queued for the scope) → the empty-state message
    (§6) fires BEFORE the gate; the gate requires no tokens.

  Missing file → exit 2 cited ("--live requires an env file at <path>"). File
  present but a required key missing/empty → exit 2 cited, naming the missing
  key(s) but NEVER echoing any value.
- **(b) `PUBLIC_ASSET_BASE_URL`.** Present via `.env` OR `--public-asset-base-url`
  (the flag takes precedence). Absent in `--live` → exit 2 cited.
- **(c) `--i-have-verified-dry-run`.** Absent in `--live` → exit 2 cited
  ("--live requires --i-have-verified-dry-run; run a --dry-run first").

Each precondition is checked and cited independently: the message must name WHICH
of (a)/(b)/(c) failed and WHAT to do.

**`.env` parsing algorithm — exact, frozen (resolves reviewer F-008):**
```
env = {}
for raw_line in file:
    line = raw_line.split('#', 1)[0]      # strip inline/full-line comment
    line = line.strip()                    # trim surrounding whitespace
    if not line:                           # blank / comment-only line
        continue
    if '=' not in line:                    # malformed KEY=VALUE line
        -> exit 2, cited ".env line N is not KEY=VALUE" (NEVER echo the line's value)
    key, value = line.split('=', 1)        # split on FIRST '=' only
    key = key.strip()
    value = value.strip()
    # single optional surrounding matching-quote pair is stripped:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]                # inner quotes/whitespace preserved verbatim
    env[key] = value                       # last assignment for a repeated key wins
```
Worked test cases (the frozen expectations):
- `FOO=bar` → `bar`
- `FOO="bar baz"` → `bar baz`
- `FOO='bar'` → `bar`
- `FOO='bar"baz'` → `bar"baz` (unmatched inner quote preserved)
- `FOO=bar baz` → `bar baz` (unquoted internal space preserved)
- `FOO="bar` → `"bar` (single leading quote, no matching pair → kept literally)
- `FOO=bar # note` → `bar` (trailing comment stripped, then trimmed)
- `FOO=` → `""` (empty string; treated as a MISSING/empty required key by gate (a))
- a line without `=` → exit 2, cited, no value echoed.

Because comments are stripped on `#`, a `#` inside a value is NOT supported this
sprint (documented limitation; no token in SETUP-CHECKLIST contains `#`). Values
are held in memory only and NEVER printed (B13, B17).

Dry-run NEVER runs this gate: no `.env`, no base URL, no ack flag is required to
preview (B6, spec §3 "full value from the dry-run without any credentials").

---

## 5. Row selection + mode dispatch (B2, B3) and the no-adapter honesty rule

### 5.1 Selection (both modes)
- Load the queue via `queue.load_queue(--queue)`. An unreadable/invalid queue →
  exit 2 cited (reuse `queue.load_queue`'s `ValueError`). A missing queue file
  is treated by `load_queue` as an empty queue → empty scope (§6).
- Select rows with `state == queue.STATE_QUEUED` (`posted` rows are never
  selected — B2).
- Scope filter: keep rows whose `week == --week`; if `--slug` given, `slug ==`;
  if `--channel` given, `channel ==`. `--channel` value must be in
  `queue.VALID_CHANNELS` or exit 2 (§3.1).
- Deterministic processing order: ascending `(slug, channel)` (B3). The plan's
  `rows` array is in this order.

### 5.1a Package existence validation (B4 — resolves reviewer F-001)
Spec §5.1 B4 binds the tool to treat a missing/unreadable package as an exit-2
precondition. This sprint honors B4 at the EXISTENCE/READABILITY level only:
- For each selected row, the tool opens `row["package_path"]` and parses it as
  JSON (`json.loads(Path(package_path).read_text())`) purely to CONFIRM it exists
  and is valid JSON. It does NOT consume/return any field (caption, attachments,
  channel, schedule_slot) — field consumption is deferred to the adapter sprints
  (003+). The parsed object is discarded.
- If the package file is missing, unreadable, or not valid JSON → exit 2, cited,
  naming the offending file and the reason (e.g. "ERROR: package not found for
  (slug, channel): <path>" / "... is not valid JSON: <err>"). On this failure NO
  `publish-plan.json` is written and NO queue is touched (precondition error).
- Validation runs in `(slug, channel)` order; the FIRST failing package aborts
  the run with exit 2 (a selected row with a broken package never appears in the
  plan — the run does not produce a partial plan). This applies in BOTH dry-run
  and (post-gate) live.
- `package_path` is still copied VERBATIM from the queue row into the plan
  envelope; the validation is existence+parseability only, deliberately not a
  content/shape check.

### 5.2 Dry-run dispatch (the default)
- For each selected row, the tool builds a plan entry (§7). It looks up the
  channel in the adapter registry. **This sprint the registry is EMPTY**, so
  every entry has `steps: []` and an explicit `note` field
  `"no adapter registered for channel '<channel>' (lands in Sprint <NNN+>)"`,
  where `<NNN+>` comes from a fixed channel→sprint map BUILD hardcodes:
  `{"instagram": "003+", "linkedin": "004+", "facebook": "005+",
  "youtube": "003+"}` (youtube has no queued asset but is a valid channel; if
  ever selected it shares the generic `003+` marker). This map is the SINGLE
  source for both the machine-plan `note` and the stdout `note` line, so they
  never drift. This is the "empty-but-valid plan" of the §11 acceptance phrase —
  a real,
  correctly-shaped, byte-deterministic envelope with one entry per selected row
  and zero steps. When adapters land (003+) the SAME code path fills `steps`.
- Dry-run makes ZERO network calls, does NOT transition state, does NOT write the
  queue (B8). Its only write is `publish-plan.json` (§7).
- Exit 0.

### 5.3 Live dispatch when the gate PASSES but no adapter exists (honesty rule)
- After a passing gate, the per-row loop looks up the adapter; finding NONE, it
  makes ZERO network calls, does NOT write the queue, and emits a cited stderr
  notice `"no adapter registered for channel '<channel>' (live posting lands in
  Sprint 003+); nothing posted"`. It MUST NOT print a fake "posted" line, MUST
  NOT invent a permalink, MUST NOT flip any row.
- With every in-scope channel lacking an adapter, `--live` posts nothing and
  exits 0 (a clean no-op, not a false success, not an error). Actual live
  posting + `queued→posted` transition + day-cap are Sprint 006 (§8).

---

## 6. Empty state (§6 spec "Empty")
- No `queued` rows match `--week`/scope → exit 0 with a clear stderr message
  `"nothing queued for <week>"` (include the active `--slug`/`--channel` filters
  in the message when set).
- In this empty case the tool does NOT write `publish-plan.json` (spec §6 Empty:
  "plan/queue unchanged"). Any pre-existing `publish-plan.json` is left byte-
  identical (verifiable: hash before == after). This is a deliberate choice
  (disclosed here) over writing an empty-rows plan.
- Queue file is never written in dry-run regardless.

---

## 7. Plan model + deterministic writer (B6, B7, B9, B10, B17)

### 7.1 Envelope shape (frozen now so 003+ conform without reshaping)
```json
{
  "schema_version": "1",
  "week": "2026-W28",
  "mode": "dry-run",
  "rows": [
    {
      "slug": "2026-07-09-anarock-vs-propequity",
      "channel": "instagram",
      "package_path": "content/2026-07-09-anarock-vs-propequity/publish/instagram.json",
      "note": "no adapter registered for channel 'instagram' (lands in Sprint 003+)",
      "steps": []
    }
  ]
}
```
- `rows` is ordered by `(slug, channel)`. `package_path` is copied verbatim from
  the queue row. (The package file IS opened this sprint for existence/JSON-
  parseability validation — §5.1a, B4 — but NO fields are consumed; field usage
  is deferred to the adapter sprints.)
- Each future step object has EXACTLY these keys (fixed now for 003+):
  `channel`, `label` (human step label, e.g. "IG · create child container 1/3"),
  `method`, `url`, `params`, `headers`, `payload`. `steps` is an emission-ordered
  array (its element order is NOT sorted by `sort_keys`; only object keys are).
- No `mode` value other than `"dry-run"` is written this sprint (live writes no
  plan; the field exists for forward-compat and is set to the active mode).

### 7.2 Determinism (B9)
- The machine plan is written to `content/publish-plan.json` (next to the queue,
  path = queue dir + `publish-plan.json`) with `json.dumps(..., sort_keys=True,
  indent=2) + "\n"` — a single trailing newline, mirroring `queue.dumps` style.
- NO wall-clock anywhere. The only dates in the plan come from `--week`/`--date`
  args. Same inputs ⇒ byte-identical file (testable: run twice, `filecmp`/hash
  equal).
- The plan is ALSO written to stdout in a human-readable form (B7), in the EXACT
  format frozen below (resolves reviewer F-004). It is deterministic (no clock,
  no dict-ordering nondeterminism — built from the same sorted structures as the
  machine plan) and the Evaluator MAY assert it line-for-line.

**Exact stdout template (dry-run, the real 2-row asset `--week 2026-W28`):**
```
Publishing plan for week 2026-W28 (mode: dry-run)

Row 1/2: 2026-07-09-anarock-vs-propequity (instagram)
  package: content/2026-07-09-anarock-vs-propequity/publish/instagram.json
  steps: 0
  note: no adapter registered for channel 'instagram' (lands in Sprint 003+)

Row 2/2: 2026-07-09-anarock-vs-propequity (linkedin)
  package: content/2026-07-09-anarock-vs-propequity/publish/linkedin.json
  steps: 0
  note: no adapter registered for channel 'linkedin' (lands in Sprint 004+)

Plan written to content/publish-plan.json
```
Format rules (frozen):
- Line 1: `Publishing plan for week <week> (mode: <mode>)`.
- One blank line, then a per-row block for each row in `(slug, channel)` order.
- Row block header: `Row <i>/<n>: <slug> (<channel>)` (1-indexed `i`, `n` = row
  count). Then three 2-space-indented lines in this fixed order: `package: <path>`,
  `steps: <len(steps)>`, `note: <note>`. When `steps` is non-empty (003+) each
  step is additionally listed under `steps:` — that per-step rendering is defined
  with the adapters; this sprint always emits `steps: 0` and the `note`.
- Blocks separated by exactly one blank line.
- Final line after a blank line: `Plan written to <plan_path>`.
- The `note` text is the SAME string as the row's `note` field in the machine
  plan (so stdout and JSON never drift). Per-channel sprint numbers in the note
  (`003+` for instagram/facebook-family, `004+` for linkedin) follow §5.2's
  `note` construction, which BUILD fixes as a channel→sprint map so the two rows
  differ deterministically.
- Empty-scope (§6) prints NO plan block; only the "nothing queued" message goes
  to stderr and the "Plan written" line is NOT printed (no plan file written).

### 7.3 Placeholder helper (B10) — generic convention only
- A pure helper renders named deterministic placeholders of the shape
  `<name>` or `<name-N>` (1-indexed), e.g. `placeholder("ig-child-container-id",
  2) == "<ig-child-container-id-2>"`, `placeholder("ig-parent-creation-id") ==
  "<ig-parent-creation-id>"`. Unit-tested directly. The SPECIFIC placeholder
  names each adapter uses are defined WITH that adapter in 003/004 — this sprint
  ships only the reusable formatter, no dead adapter-specific constants.

### 7.4 Redaction helper (B17)
- A pure helper returns the redaction token `<REDACTED>` and a convenience that
  redacts a secret inside a header/param string (e.g.
  `redact_bearer("Bearer sk-real") == "Bearer <REDACTED>"`,
  `redact_token_param("access_token=sk-real") == "access_token=<REDACTED>"`).
  Unit-tested directly. GUARANTEE this sprint can prove: no `.env` secret VALUE
  ever appears in stdout or `publish-plan.json` (this sprint emits no adapter
  steps, so the strongest available proof is: with a `.env` containing a sentinel
  token and a passing `--live` gate, the sentinel string is absent from all
  emitted stdout/stderr; the full step-level redaction proof lands with adapters).

### 7.5 image_url join helper (B11)
- A pure helper implements the FIXED join rule: `image_url(base, slug, filename)
  == "<base>/<slug>/<filename>"` (trailing slash on `base` collapsed to one).
  When `base` is `None`/absent it returns the literal placeholder
  `<PUBLIC_ASSET_BASE_URL>` joined the same way:
  `"<PUBLIC_ASSET_BASE_URL>/<slug>/<filename>"`. Documented in the module.
  Unit-tested directly. (Adapters call it in 003/005.)

---

## 8. Transport seam + no-network proof (B38, B39)

- A single `Transport` class wraps the ONE `urllib.request.urlopen` call site in
  the module. It exposes `request(method, url, headers=None, body=None) ->
  Response` (see §8.2 for the Response shape) — but this sprint no adapter calls
  it.
- A `RecordingTransport` (fake: records each call, returns canned responses,
  opens no socket) and a `RaisingTransport` (every `request` call raises
  `AssertionError("no network in dry-run/tests")`) are provided FOR TESTS. They
  live in the module (so the interface is frozen and importable), are import-
  silent, and open no socket.

### 8.1 Transport injection mechanism (constructor/param injection — resolves reviewer F-002)
- Injection is via the `run(..., transport=None)` keyword arg (§1.1), NOT
  monkeypatching. When `transport is None`, `run` constructs the default
  `Transport()`. When a test passes `transport=RecordingTransport()` or
  `transport=RaisingTransport()`, `run` uses that instance for every network
  call (this sprint: none). `main` NEVER sets `transport` (always the live
  default). This is the single, unambiguous swap mechanism; no module-global
  transport variable exists.
- Because the adapter registry is empty this sprint, `run` holds the transport
  but invokes it zero times; the injection path is exercised (a test asserts the
  passed transport's recorded-call count is 0 after a dry-run and after a passing
  live no-op).

### 8.2 Response shape returned by `Transport.request` (frozen now — resolves reviewer F-003)
`request(...)` returns a small `Response` object (a stdlib `dataclass`-free
plain class or `types.SimpleNamespace`) with EXACTLY these attributes:
```python
class Response:
    status   # int   HTTP status code, e.g. 200
    headers  # dict[str, str]  response headers (lower-cased keys)
    body     # bytes           raw response body
    def json(self):  # -> parsed JSON (json.loads(self.body)); raises ValueError on non-JSON
        ...
```
- Adapters (003+) call `resp = transport.request(...)` then `resp.json()["id"]`
  etc. This interface is FROZEN this sprint so adapters conform without reshaping.
- `RecordingTransport.request` returns a `Response` built from a per-call queue of
  canned payloads the test supplies at construction, e.g.
  `RecordingTransport(responses=[{"id": "child_1"}, {"id": "parent_1"}, ...])`;
  each `request` pops the next payload and returns
  `Response(status=200, headers={}, body=json.dumps(payload).encode(), )`. With no
  responses configured it returns `Response(status=200, headers={}, body=b"{}")`
  (`json()` → `{}`). It records `(method, url, headers, body)` tuples in
  `.calls` for assertions. It opens NO socket.
- `RaisingTransport.request` raises immediately (never returns a Response),
  proving dry-run never reaches the transport.
- The LIVE `Transport.request` is the ONLY place `urllib.request.urlopen` is
  called; it builds a `urllib.request.Request(url, data=body, headers=headers,
  method=method)`, calls `urlopen`, and packs the result into a `Response`
  (`status = resp.status`, `headers = dict(resp.headers)`, `body = resp.read()`).

- **AST no-network test (B38 — resolves reviewer F-007)** in
  `test_publish_api.py`, an INVERSION of the existing `test_utm.py` AST test:
  parse `publish_api.py`; count `urlopen` references in BOTH import forms so the
  test is robust to either style —
  (i) attribute form `urllib.request.urlopen(...)` → `ast.Attribute` with
  `.attr == "urlopen"`, and (ii) bare-name form
  `from urllib.request import urlopen; urlopen(...)` → `ast.Name` with
  `.id == "urlopen"`. The UNION count of such nodes that are the `.func` of an
  `ast.Call` must equal EXACTLY 1, and that single node must be lexically INSIDE
  the `Transport` class body. Assert no other function/method calls `urlopen`.
  (Not count==0 as in utm — count==1 + location, both import forms covered.)
  BUILD SHOULD use the attribute form (`urllib.request.urlopen`) for a single
  obvious seam, but the test passes for either form.
- **Raising-transport dry-run proof (B8/B39):** running a full dry-run with a
  `RaisingTransport` injected must exit 0 and produce the full valid plan. Since
  the registry is empty the transport is never invoked; the test asserts the
  transport's call-count is 0 after a dry-run (the correct property: dry-run
  touches no transport) AND that a `RaisingTransport` therefore cannot break the
  run. No test and no dry-run opens a real socket (B39).

---

## 9. Exit codes (B40–B42, subset in scope this sprint)
- `0` — dry-run plan emitted (rows with empty steps, or empty-scope message); OR
  a passing `--live` gate that finds no adapter and cleanly posts nothing.
- `1` — reserved for domain refusals (already-posted, container ERROR, rate
  limit, day-cap). NONE are reachable this sprint (no adapters, no posting). The
  code path/convention is present; no `1` is emitted by any 002 behavior.
- `2` — usage/precondition: malformed `--week`/`--date`; unknown `--channel`;
  invalid `--max-per-day`; invalid `--linkedin-post-type`; both `--dry-run` and
  `--live`; invalid/unreadable queue; `--live` failing gate (a)/(b)/(c) or
  missing `--date`. Cited on stderr, no write, no network.

---

## 10. Verification — commands the Evaluator runs

All from repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`.

**Precondition — frozen test asset (resolves reviewer F-009).** Gate clauses 3,
4, 7, 8 depend on this asset; verify it before running them:
- `content/publish-queue.json` holds at least 2 `state=="queued"` rows for week
  `2026-W28`: `(slug="2026-07-09-anarock-vs-propequity", channel="instagram")`
  and `(slug="2026-07-09-anarock-vs-propequity", channel="linkedin")`.
- `content/2026-07-09-anarock-vs-propequity/publish/instagram.json` exists and is
  valid JSON.
- `content/2026-07-09-anarock-vs-propequity/publish/linkedin.json` exists and is
  valid JSON.
Confirm with:
```
python3 -c "import json;d=json.load(open('content/publish-queue.json'));r=[(x['slug'],x['channel']) for x in d['rows'] if x['state']=='queued' and x['week']=='2026-W28'];print(sorted(r))"
python3 -c "import json;json.load(open('content/2026-07-09-anarock-vs-propequity/publish/instagram.json'));json.load(open('content/2026-07-09-anarock-vs-propequity/publish/linkedin.json'));print('PACKAGES-OK')"
```
Expected: the pair-list contains both `(…,'instagram')` and `(…,'linkedin')`;
`PACKAGES-OK`. If any precondition fails, gates 3/4/7/8 are INAPPLICABLE —
record as "SKIP: frozen asset missing/modified" rather than a code failure.
(Verified present at contract time: both queued rows and both package files
exist.)

**Gate clause 1 — new suite green:**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_publish_api.py'
```
Expected: `OK`, 0 failures.

**Gate clause 2 — no regression, both suites stay green:**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'
```
Expected: `OK` (prior 271 + new publish_api cases), zero failures/errors.

**Gate clause 3 — dry-run against the REAL asset emits a valid 2-row plan, no network, no queue change:**
```
cp content/publish-queue.json /tmp/q.before
python3 tools/marketing-loops/publish_api.py --week 2026-W28 ; echo "exit=$?"
python3 -c "import json;d=json.load(open('content/publish-plan.json'));print(d['mode'],len(d['rows']),[ (r['slug'],r['channel'],len(r['steps'])) for r in d['rows']])"
diff content/publish-queue.json /tmp/q.before && echo QUEUE-UNCHANGED
```
Expected: exit 0; plan `mode == "dry-run"`, 2 rows `(…,instagram,0)`,
`(…,linkedin,0)` in that order, each with a `note`; `QUEUE-UNCHANGED`.

**Gate clause 4 — determinism (byte-identical on repeat):**
```
python3 tools/marketing-loops/publish_api.py --week 2026-W28 && cp content/publish-plan.json /tmp/p1
python3 tools/marketing-loops/publish_api.py --week 2026-W28 && diff content/publish-plan.json /tmp/p1 && echo DETERMINISTIC
```
Expected: `DETERMINISTIC`.

**Gate clause 5 — empty scope leaves plan/queue unchanged:**
```
python3 tools/marketing-loops/publish_api.py --week 2026-W01 ; echo "exit=$?"
```
Expected: exit 0, stderr "nothing queued for 2026-W01", `publish-plan.json`
NOT created/modified (if it exists from a prior run its hash is unchanged).

**Gate clause 6 — malformed input → exit 2, cited, no write:**
```
python3 tools/marketing-loops/publish_api.py --week 2026-28 ; echo "exit=$?"        # bad week
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --channel twitter ; echo "exit=$?"
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --dry-run --live ; echo "exit=$?"
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --date 2026-13-40 ; echo "exit=$?"
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --linkedin-post-type bogus ; echo "exit=$?"
```
Expected: each exits 2 with a cited ERROR on stderr and no `publish-plan.json`
write from the failing invocation.

**Gate clause 7 — live gate refuses without credentials (no network, no write):**
```
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --live ; echo "exit=$?"   # no .env, no ack
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --live --i-have-verified-dry-run ; echo "exit=$?"  # still no env/base url
```
Expected: exit 2 each; stderr cites the specific failing precondition
(a/b/c and/or missing `--date`); no plan/queue write; NO token value ever
printed.

**Gate clause 8 — live gate PASS but no adapter is an honest no-op (not a false success):**
Evaluator writes a throwaway `/tmp/live.env` with sentinel tokens
(`IG_USER_ID=SENTINEL_IGID`, `IG_ACCESS_TOKEN=SENTINEL_IGTOKEN`,
`LI_PERSON_URN=urn:li:person:SENTINEL`, `LI_ACCESS_TOKEN=SENTINEL_LITOKEN`,
`PUBLIC_ASSET_BASE_URL=https://assets.example/social-assets`) and runs:
```
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --live \
  --env /tmp/live.env --date 2026-07-09 --i-have-verified-dry-run 2>&1 | tee /tmp/live.out ; echo "exit=${PIPESTATUS[0]}"
grep -c 'SENTINEL' /tmp/live.out        # must be 0 — no secret echoed
grep -Ei 'posted|permalink' /tmp/live.out   # must find NO fake success line
diff content/publish-queue.json /tmp/q.before && echo QUEUE-UNCHANGED
```
Expected: exit 0; a cited "no adapter registered … nothing posted" notice per
in-scope channel; ZERO `SENTINEL` occurrences; NO "posted"/"permalink" success
line; `QUEUE-UNCHANGED`.

**Gate clause 9 — no-network AST + raising-transport proof (in the suite):**
Covered by `test_publish_api.py` (§8, §8.2). Evaluator may additionally confirm
(counts BOTH import forms — attribute `urllib.request.urlopen` and bare-name
`urlopen` — as the frozen test does):
```
python3 -c "import ast; t=ast.parse(open('tools/marketing-loops/publish_api.py').read()); \
refs=[n for n in ast.walk(t) if (isinstance(n,ast.Attribute) and n.attr=='urlopen') or (isinstance(n,ast.Name) and n.id=='urlopen')]; \
calls=[n for n in ast.walk(t) if isinstance(n,ast.Call) and n.func in refs]; \
print(len(calls))"
```
Expected: prints `1` (exactly one `urlopen` call site — the single seam, in
whichever import form BUILD chose).

**Gate clause 10 — import silence + stdlib only:**
```
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); import publish_api"
```
Expected: exit 0, empty stdout. No third-party import anywhere in the module
(stdlib only: `argparse`, `json`, `re`, `sys`, `pathlib`, `urllib.*`,
`datetime` for parsing supplied dates only).

**Gate clause 11 — hygiene:**
```
git status --porcelain
```
Expected: only `tools/marketing-loops/publish_api.py` and
`tools/marketing-loops/tests/test_publish_api.py` added (plus, if a verification
run created it, an untracked `content/publish-plan.json` — which must NOT be
committed; see §12). No `.env`, no secret, no db/upload artifact staged.

---

## 11. Non-applicable sections
- Playwright / browser click paths: N/A — no HTTP surface, no route, no rendered
  screen. Verification is unittest + the CLI probes in §10.
- Keyboard/focus/ARIA/contrast/responsive: N/A — no UI. "Design" here = output
  legibility (the stdout plan is plain, wrappable text; the machine plan is
  stable-sorted for diffing — spec §7).

## 12. Security / hygiene assumptions
- Secrets come ONLY from an untracked `.env`; loaded to memory, NEVER printed,
  NEVER written to any tracked file (B13, B17, B18). `.gitignore` already covers
  `.env` (verified line `.env`).
- `content/publish-plan.json` is a generated dry-run artifact. It is NOT a
  secret (redaction guarantees no token reaches it) but it is a build output;
  BUILD must add `content/publish-plan.json` to `.gitignore` so verification runs
  do not stage it, and must confirm `git status --porcelain` is clean of it and
  of `.env`.
- The only writes this sprint: `content/publish-plan.json` (dry-run). The queue
  file is never written this sprint (live posting is Sprint 006).

## 13. Non-goals (explicit)
- NO channel adapters (Instagram 003, LinkedIn 004, Facebook 005): no
  `/media`, `/rest/*`, `/photos`, `/feed` calls; the adapter registry ships
  empty and every selected row renders with `steps: []`.
- NO live posting, NO `queued→posted` transition, NO permalink recording, NO
  `queue.write_queue` call — all Sprint 006.
- NO day-cap enforcement (`--max-per-day` parsed/validated only) — Sprint 006.
- NO facebook skip-with-notice adapter behavior (`--enable-facebook` parsed
  only) — Sprint 005.
- NO package-CONTENT CONSUMPTION: the package FILE at `row["package_path"]` IS
  opened this sprint but ONLY to validate existence + JSON-parseability (§5.1a,
  B4). NO field (caption, attachments, channel, schedule_slot) is read/returned/
  rendered — B5 field consumption moves to the adapter sprints (003+). (This
  reconciles the prior draft with spec B4: the missing-package exit-2 precondition
  is honored NOW; only field consumption is deferred.)
- NO specific adapter placeholder-name constants (only the generic formatter).
- NO frozen-module edits, NO existing-test edits, NO content-asset changes.
- NO wall-clock read anywhere; NO third-party dependency; stdlib only.
- NO real network in any test or in dry-run — provable (§8).

## 14. Acceptance summary (the contract's testable core)
Sprint 002 passes iff ALL hold:
1. `publish_api.py` exists, stdlib-only, import-silent, `_HERE` pattern, exposes
   `main`/`run`; new `test_publish_api.py` suite green; both full suites stay
   green (no regression to the 271).
2. Dry-run (default) against the real asset emits `mode=="dry-run"`, a 2-row
   `(instagram,linkedin)`-ordered plan with `steps: []` + a `note` per row, to
   stdout AND `content/publish-plan.json`; byte-identical on repeat; queue
   unchanged; zero network.
3. Empty scope → exit 0, "nothing queued", plan/queue unchanged (not written).
4. `--week` required + format-validated; `--date`/`--channel`/`--max-per-day`
   (optional, default 3)/`--linkedin-post-type` validated; both-modes and
   unknown-channel → exit 2 cited, no write. Each selected row's package file is
   validated for existence + JSON-parseability (B4, §5.1a); a missing/unreadable/
   invalid package → exit 2 cited, no plan/queue write (no field consumption).
5. `--live` gate enforces (a) `.env` tokens for in-scope channels, (b)
   `PUBLIC_ASSET_BASE_URL`, (c) `--i-have-verified-dry-run` (+ `--date`), each
   cited independently; failure → exit 2, no network, no write, no secret echoed.
6. `--live` with a PASSING gate but no adapter is an honest no-op: exit 0, cited
   "nothing posted", NO fake posted/permalink line, queue unchanged, no secret
   echoed.
7. Transport seam: exactly ONE `urlopen` call site inside the `Transport` class
   (AST-proven); dry-run invokes the transport ZERO times; a `RaisingTransport`
   cannot break dry-run; no test/dry-run opens a socket.
8. Placeholder, redaction, and image_url helpers are pure, deterministic, and
   unit-tested; no `.env` secret value ever appears in any emitted output.
9. Hygiene: `.env` gitignored (unchanged); `content/publish-plan.json`
   gitignored; `git status --porcelain` clean of secrets/artifacts.
