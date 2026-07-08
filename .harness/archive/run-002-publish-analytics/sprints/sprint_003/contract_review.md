VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Contract Review — Sprint 003: Publish Packages + Schedule Slot + Mark-posted + Skill

### Summary

This contract is **clear, testable, and complete**. It closes the second half of Gap 2 (publish layer) by specifying package generation, schedule-slot assignment, mark-posted transition, and the `/loop-publish` skill. All behaviors are atomic, deterministically specified, and anchored to real-asset ground truth.

---

### Verification Against Harsh Pass Standard

#### 1. Exact CLI commands and exit codes
**Status: Pass**

- §8 provides full bash commands with expected exit codes (0/1/2) and output expectations for each scenario.
- §3.6 documents exit code semantics explicitly: 0 success, 1 domain failure, 2 usage/precondition error.
- §9 adversarial checklist specifies 14 precise probes, each with exact expected behavior.

#### 2. Deterministic schemas with examples
**Status: Pass**

- PACKAGE schema (§3.3, tgered from spec §5.4): JSON with 8 named fields, `sort_keys=True, indent=2`, trailing newline. Example output provided.
- QUEUE schema: inherited from Sprint-002 (frozen, re-verified to match contract).
- Schedule slot format (§3.2): worked table for `--week 2026-W27` with all three channels, formula verified for consistency (W=27: instagram (27+0)%2=1→evening/18:00 ✓, youtube (27+1)%2=0→morning/11:00 ✓, linkedin (27+2)%2=1→evening/17:30 ✓).

#### 3. Per-channel UTM link construction clarity
**Status: Pass (advisor reconciliation)**

§3.3 step 7 had apparent ambiguity about extra query params. **Literal reading resolves it:** "where `<scheme>://<host><path>` is taken from the validated flywheel URL" — only BASE is extracted. The query is **built fresh** with exactly three named params: `?utm_source=<channel>&utm_medium=social&utm_campaign=<campaign>`. No merge, no preservation of source query. PACKAGE schema confirms output has only three params. Canonical rebuild means normalized order, not param fusion. Extra params cannot survive because the query string is constructed, not inherited.

#### 4. Caption resolution with fallback
**Status: Pass**

- §3.1 specifies `captions.md` with `<!-- caption:<channel>:start/end -->` markers.
- Resolution order is explicit: try channel-specific block, fall back to `caption:all`, return None if neither exists.
- Malformed blocks (`:start` without `:end`) raise ValueError → exit 2. Duplicates also raise ValueError.
- Body extraction is deterministic: text strictly between markers, interior whitespace preserved byte-for-byte.
- Absence is an error, never an invention (B-P5). §3.3 step 8 enforces this: any missing channel body → exit 2, names the channel(s), writes nothing.

#### 5. Real-asset ground truth
**Status: Pass**

- Real tgrera (`2026-07-03-tgrera-enforcement-wave`, week 2026-W27): expected 3 packages (instagram/youtube/linkedin), 3 queued rows with non-null schedule_slot + package_path, specific slot values per §3.2 table.
- Real hyd (`2026-07-03-hyd-premium-vs-budget`): gate refuses with cited reasons `[missing-verdict, killed]`, exit 1, no write.
- Real asset caption provenance: `content/2026-07-03-tgrera-enforcement-wave/captions.md` carries the Hook line verbatim (from `meta.md` line 6) — no new claim introduced, sourced from existing authored copy.

#### 6. Idempotency and no-regress guarantees
**Status: Pass**

- **Idempotency of package.py**: re-running same command on same inputs → byte-identical PACKAGE files + QUEUE file + stdout (§3.3, §4). Proof via §8 shasum test.
- **Idempotency of mark-posted**: deliberately **non-idempotent** (contrast stated explicitly). Marking the same row twice → exit 1 "already posted", no write. This is the design, not a bug.
- **No-regress of posted rows**: re-running package.py after a row is marked `posted` → stdout `kept-posted <slug> <channel>`, package file **not rewritten**, posted row untouched (§3.3 step 9, §4). Proof via mtime/shasum probe 10 in §9.

#### 7. State space coverage
**Status: Pass**

- §4 enumerates all states: Empty (valid empty-rows QUEUE), Success (packages + queue rows), Gate refusal (exit 1, cited), Missing caption (exit 2, named, no write), Invalid UTM (exit 2, no write), Manifest guards, Idempotency, No-regress, Mark-posted transitions, Non-idempotency, Offline.
- Every state has explicit entry/exit conditions and file-write guarantees.

#### 8. Security and constraint compliance
**Status: Pass**

- §6 Security: stdlib only (json, re, argparse, pathlib, datetime for parsing supplied dates only). No requests, urllib fetch, socket, or network. No secrets, no personal data.
- §7 Non-goals: explicitly excludes analytics, changes to gate, live posting APIs, credential handling.
- Frozen modules: utm.py, gate.py, queue.py, channels.py are imported read-only, never modified (verifiable via git diff).
- No `datetime.now()` anywhere (only `strptime` for supplied `--posted-on` validation, and `urllib.parse` for query handling — safe use).

#### 9. Fixture matrix and adversarial coverage
**Status: Pass**

§9 lists 10 required fixture intents with expected behavior:
- `pkg-pass`: positive control, 3 packages, 3 queued rows.
- `pkg-multi-surface`: manifest with ≥2 surfaces → ordered attachment list.
- `pkg-per-channel-caption`: [all] + [instagram] override → correct per-channel resolution.
- `pkg-no-captions`: no file → exit 2, named, no write.
- `pkg-missing-channel-caption`: only [instagram] but youtube in Channels → exit 2, no write.
- `pkg-bad-utm`: gate PASS but campaign mismatch → exit 2, Sprint-001 violation code cited.
- `pkg-no-manifest`: exit 2, no write.
- `pkg-empty-surfaces`: exit 2, no write.
- Reused `killed` and `verdict-fail` fixtures (exit 1, no write).

Each fixture has clear expected result and violation code. Fixtures live under `tools/` (not `content/`).

#### 10. Adversarial probe completeness
**Status: Pass**

§9 adversarial checklist covers 14 probes:
1. Real tgrera package values (byte assertions).
2. Idempotency (shasum).
3. Per-channel link correctness (utm_source matches channel).
4. Gate never bypassed (hyd → exit 1, no write).
5. Missing caption (exit 2, no write).
6. Invalid UTM (exit 2, violation code cited).
7. Manifest guards (exit 2).
8. Mark-posted happy path (queued → posted).
9. Mark-posted refusals (already-posted, not-found, bad-args, bad-date, bad-permalink).
10. No-regress (posted row + package file untouched, others re-packaged).
11. Cross-sprint regression (Sprint-002 queue survives package.py merge).
12. Import safety + determinism (silence on import, channel map from Sprint-001).
13. No network / no wall-clock (grep proof).
14. Frozen modules (git diff proof).

#### 11. Downstream testability
**Status: Pass**

- Evaluator can run exact commands from §8 and verify outputs bit-for-bit.
- Fixtures are deterministically specified in §9 matrix.
- Real assets are accessible on disk.
- Exit codes and stdout/stderr messages are pinned.
- Schedule formula is verifiable against the worked table.

---

### Consistency Check

**Schedule formula verification** (§3.2 vs worked table):

| Channel | Ordinal | Week (27) | (WW+ord) | Bucket | Time | Expected slot |
|---|---|---|---|---|---|---|
| instagram | 0 | 27 | 27 (odd) | evening | 18:00 | ✓ |
| youtube | 1 | 27 | 28 (even) | morning | 11:00 | ✓ |
| linkedin | 2 | 27 | 29 (odd) | evening | 17:30 | ✓ |

Formula `bucket = "morning" if (WW + ordinal) % 2 == 0 else "evening"` matches all rows. No contradiction.

---

### Definition of Done Alignment

Every clause in §10 "Definition of Done" is covered:
- ✓ captions.py module, fallback resolution, absent-body error
- ✓ schedule.py deterministic slot formula, wall-clock-free, W27 table exact
- ✓ package.py gate re-run, preconditions exit 2, deterministic writes, idempotent
- ✓ mark_posted.py transitions, validations, non-idempotent by design
- ✓ /loop-publish skill doc mirrors loop-qa, no bypass, no copy
- ✓ Real tgrera packages at exit 0, real hyd at exit 1 with cited reasons
- ✓ Fixtures under tools/ per §9 matrix
- ✓ Unit tests + cross-command regression proof
- ✓ Evidence (commands, exits, shasums, sample JSON, grep-clean proof) logged in generator_trace.log

---

### Conclusion

This contract exhibits the **DNA of deterministic CLI work**: explicit schemas with version, exit codes tied to semantics, real-asset ground truth, adversarial fixture matrix, frozen-module re-use, and offline constraints. There is no vagueness that prevents implementation, no state missing from the map, and no escape hatch from the gate. The real assets are accessible on disk and the expected outputs are byte-level pinned.

**Recommend proceed to implementation immediately.**
