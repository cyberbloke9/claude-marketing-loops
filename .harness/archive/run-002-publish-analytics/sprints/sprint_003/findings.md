VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 003 Evaluation — Publish packages + schedule slot + mark-posted + `/loop-publish`

CLI / library + one skill deliverable (no web UI; Playwright N/A per contract).
Verification is exact CLI invocations, exit codes, stdout/stderr substrings, on-disk
JSON byte assertions, and source greps — all re-run independently by the Evaluator
from a clean state, not read from the Generator's trace.

## Evidence summary (all re-executed by the Evaluator)

| Probe (contract §9) | Result | Verdict |
|---|---|---|
| Unit suite `unittest discover` | Ran 151 tests — OK (S001+S002+S003) | PASS |
| 1. Real tgrera `--week 2026-W27` | exit 0; 3 packages; `schema_version "1"`; per-channel `utm_source` correct; `utm_campaign=tgrera-enforcement-wave`; `attachments == ["content/2026-07-03-tgrera-enforcement-wave/render/chart-card.png"]`; slots IG `evening/18:00`, YT `morning/11:00`, LI `evening/17:30` (matches §3.2 W27 table); caption = body + `\n\n` + link; 3 `queued` rows w/ non-null slot+package_path | PASS |
| 2. Idempotency | re-run → byte-identical shasum for all 3 packages AND queue; identical stdout | PASS |
| 3. Per-channel link correctness | IG/YT/LI carry `utm_source=instagram\|youtube\|linkedin`, same campaign, all `utm_medium=social` | PASS |
| 4. Gate never bypassed (real hyd) | exit 1; stderr `[missing-verdict] [killed]`; temp queue **not created**, publish-dir **not created** | PASS |
| 5. Missing caption | `pkg-no-captions` / `pkg-missing-channel-caption` → exit 2; names channel(s) lacking a body (`youtube`, no `[all]` fallback); no write | PASS |
| 6. Invalid UTM (`pkg-bad-utm`) | exit 2; cites Sprint-001 `campaign-mismatch`; no write (UTM enforced at publish, not folded into gate) | PASS |
| 7. Manifest guards | `pkg-no-manifest` / `pkg-empty-surfaces` → exit 2; no write | PASS |
| 8. Mark-posted happy path | `queued`→`posted` exit 0; row records date + permalink; others untouched | PASS |
| 9. Mark-posted refusals | 2nd mark → exit 1 "already posted"; not-found → 2; non-URL permalink → 2; `2026-13-40` → 2; unknown channel `twitter` → 2; each no write | PASS |
| 10. No-regress / no-overwrite | after posting IG, re-package → `kept-posted ... instagram`, YT/LI re-packaged; posted row intact | PASS |
| 11. Cross-command regression | enqueue (null slots) → package (fills) → enqueue again → slots survive; queue byte-stable; 3 rows, no dup | PASS |
| 12. Import safety + determinism source | modules import silently; `slot_for('2026-W27','instagram')=='2026-W27/evening/18:00'`; `CHANNEL_SOURCE_MAP` imported (no fork) | PASS |
| 13. No network / no wall-clock | grep of 4 new sources → zero hits for `datetime.now\|utcnow\|time.time\|requests\|urlopen\|urlretrieve\|socket`; only `strptime` + `urlparse` present | PASS |
| 14. Frozen modules untouched | mtimes: `utm.py` 14:04, `gate.py` 14:32, `channels.py` 14:32, `queue.py` 14:33 — all predate the Sprint-003 build (`captions.py` 15:58, `schedule.py`/`mark_posted.py` 16:04, `package.py` 16:09); S001+S002 suites green inside the 151 (no git in workspace, so mtime + suite-pass is the observable proof) | PASS |
| Malformed `captions.md` (unclosed block) | exit 2, cited "never closed (missing :end)", no write | PASS |
| Per-channel caption override | IG uses `[instagram]` override; YT/LI fall back to `[all]` | PASS |
| Multi-surface attachments | ordered ≥2 repo-relative POSIX PNG list, `surfaces[]` order | PASS |
| `/loop-publish` SKILL.md | frontmatter (`name`+`description`) + gate→package→post→mark-posted steps; "never bypasses the gate", "writes no marketing copy", exit-code map; matches `loop-qa`'s frontmatter shape + "mechanical" framing (verified by reading `loop-qa/SKILL.md`) | PASS |
| content/ leakage (contract §6) | after all temp-queue runs, `content/` holds only the two real assets + TEMPLATE.md + the committed `captions.md`; no `publish-queue.json`, no `publish/` dir leaked | PASS |

## Findings

### Finding F-001: Whitespace-only caption block yields a link-only caption instead of erroring

Severity: Low
Category: Functionality
Status: Low (non-blocking; does not sink PASS)

**Contract Clause.** §3.1: "if `captions.md` … has no resolvable body for a channel …
`package.py` exits 2 … The tool NEVER substitutes, defaults, or generates caption
text." §3.1 defines "absent" as *neither* the `caption:<c>` nor `caption:all` block
existing.

**Reproduction.** A `captions.md` with a present-but-empty `caption:all` block
(`<!-- caption:all:start -->` immediately followed by a blank line then
`:end`). `_strip_blank_edges` yields `""`, `body_for` returns `""` (key present, not
`None`), and `package.py`'s `is None` check does not flag it.

**Expected (spec north star).** An empty authored body should be treated like an
absent one → exit 2, "no caption body for channel(s)…", no write.

**Actual.** exit 0; the packaged `caption` field is `"\n\n<utm_link>"` — a bare-URL,
copy-less caption is shipped.

**Why Low, not High/Blocker.** It is strictly contract-compliant (§3.1 defines absent
as block-nonexistence, and the block exists). It requires deliberately malformed
authored input; it is unreachable with any shipped fixture or the real committed
`captions.md` (which carries a real body). No spec behavior the contract pins is
broken. Documented so a future author does not read a link-only caption as intended.

**Required Fix (defer-safe, not required for this PASS).** In `captions.body_for` or
`package.py`, treat a body that is empty after `.strip()` as `None`.

**Pass Condition.** A present-but-empty caption block for a to-be-packaged channel →
exit 2 with the missing-caption message, no write.

## Harsh-pass standard

- No dead controls; every path has a real effect or a cited refusal.
- Error messages are specific and recoverable (name asset + channel + concrete fact).
- No fabricated content: absent caption → exit 2, never invented; real caption body is the verbatim `meta.md` Hook line.
- Deterministic, byte-identical on re-run; no wall-clock, no network.
- Atomicity: on every exit-1/2 path, zero package files and zero queue writes (temp queue/publish-dir confirmed absent).

## Trace review

`generator_trace.log` complete and honest; claims map to reproducible artifacts.
The two refinement entries are narrow and justified. The "grep-hardening" docstring
edit is cosmetic and does not mask behavior — clean state re-confirmed against actual
code here. No skipped failures, no premature-completion language, no claim without an artifact.

## Scoring

Weights (CLI/infra): Functionality 30%, Craft 25%, Evidence 25%, Design(schema/seam) 15%, Originality 5%.
- Functionality 5.0 — every probe/fixture reproduces the contract's exact exit code, stdout/stderr, and on-disk bytes; gate never bypassed; atomic; idempotent; deterministic. (F-001 is a Low outside the contract's pinned behavior.)
- Craft 5.0 — pure importable modules, no import side effects; order-independent UTM-link rebuild; specific messages; frozen modules untouched; single-source channel map.
- Evidence 5.0 — trace claims independently reproduced end-to-end from a clean state.
- Design 4.5 — versioned PACKAGE schema; `{queued,posted}` seam preserved; slot feeds later Gap-3 A/B table.
- Originality 4.0 — domain-specific, no slop/filler.

Weighted = 0.30·5 + 0.25·5 + 0.25·5 + 0.15·4.5 + 0.05·4 = **4.83 → 4.8**.
Evidence ≥ 4 ✓, Functionality ≥ 4 ✓, no Blockers, no High (F-001 is Low), weighted ≥ 4 ✓.

## Verdict

**PASS.** Sprint 003 delivers the package + posting-transition layer exactly to
contract: deterministic per-channel PACKAGE files, a wall-clock-free schedule slot
matching the §3.2 table, an atomic gate-respecting packager, a non-idempotent
mark-posted transition with full refusal coverage, and a `/loop-publish` skill that
never bypasses the gate and writes no copy. Frozen Sprint-001/002 modules are
untouched and their suites remain green. One Low (F-001, empty caption block →
link-only caption) is documented but does not block — it is contract-compliant and
unreachable with shipped fixtures/content.
