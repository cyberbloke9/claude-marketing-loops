#!/usr/bin/env python3
"""Cross-gap end-to-end acceptance runner for the TERREM marketing-loops toolchains.

Sprint 006 (spec s11 final sprint; contract sprint_006). Proves BOTH gaps in one
deterministic, no-network run by invoking the frozen Sprint-001..005 CLIs as
subprocesses -- exactly as an operator / the ``/loop-publish`` + ``/loop-measure``
skills do (exit codes and emitted strings included). It invents no metric, defines
no schema, adds no CLI behavior, and never modifies a frozen module.

Three proofs:

  1. A NORMATIVE expectation table over every committed Sprint-001..005 fixture in
     the three families (UTM assets, ``fixtures/publish/``, ``fixtures/metrics/``).
     A refusal row is met ONLY when the exit code matches AND the CLI's *cited
     reason* substring is present -- a nonzero exit for the wrong reason does NOT
     satisfy a row (contract s3.3 / attack #2). Reason substrings are pinned to the
     ACTUAL strings the frozen CLIs emit (confirmed by invoking them; A-6.1).

  2. An end-to-end CROSS-GAP seam chain on the real PASS asset
     ``content/2026-07-03-tgrera-enforcement-wave``:
     ``verify_utm -> enqueue -> package -> mark_posted -> scorecard``, where the
     scorecard's Posting-time A/B bucket is driven by the ``schedule_slot`` the
     PUBLISH layer wrote into the generated queue (verified genuine: forcing the
     queue slot to a different bucket moves the scorecard column). This is the load-
     bearing "both gaps" assertion -- the scorecard consumes the publish output.

  3. TABLE COVERAGE: every committed fixture directory in each family is named by
     exactly one table row, so a hostile Evaluator cannot drop in an unchecked
     fixture and a deleted fixture surfaces immediately (contract s3.5 / attack #8).

Why generated artifacts are NOT byte-compared (contract s7): ``package.py`` stores
``package_path`` repo-relative when under the repo root else absolute-resolved.
The runner writes the queue/packages into a throwaway ``tempfile.mkdtemp()`` OUTSIDE
the repo, so those paths are absolute + non-portable. Therefore generated publish
artifacts (queue, packages) are verified by PATH-INDEPENDENT JSON-field invariants
(per-channel ``utm_link``, ``caption`` bytes, ``attachments`` order, ``schedule_slot``,
``state`` transitions, no-duplicate rows on re-run) -- never whole-file byte-equality.
Scorecards from FIXED fixtures are path-independent (Sprint-005 proven) and ARE
byte-golden-compared against ``fixtures/metrics/expected/<name>.md``.

Every mutable write is redirected into the temp working area, which is removed on
exit (success or failure): the runner never dirties the repo (no publish-queue,
no real ``content/*/publish/``, no new ``metrics/*``).

Exit codes:
    0  every table row met AND the chain held AND coverage is exact.
    1  one or more rows unmet, the chain failed, or coverage is incomplete.
    2  the runner's own precondition error (a frozen CLI file or the real PASS
       asset is missing). Message on stderr.

Frozen-module integrity: the runner imports NOTHING from the frozen tools except
``schedule`` -- read-only, solely to read the documented ``schedule.slot_for``
constant used in the seam assertion (disclosed in the generator trace). Everything
else is invoked as a subprocess.

Stdlib only. No wall-clock / date-time module anywhere (no output field derives
from the clock). No network import. Paths resolved from ``__file__`` (any cwd).
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Paths (resolved from this file, so the runner works from any cwd) --------
SCRIPT_DIR = Path(__file__).resolve().parent          # tools/marketing-loops/
REPO_ROOT = SCRIPT_DIR.parents[1]                      # repo root
FIXTURES = SCRIPT_DIR / "fixtures"
FX_METRICS = FIXTURES / "metrics"
FX_PUBLISH = FIXTURES / "publish"
FX_EXPECTED = FX_METRICS / "expected"
CONTENT_FULL = FX_METRICS / "full" / "content"

VERIFY_UTM = SCRIPT_DIR / "verify_utm.py"
ENQUEUE = SCRIPT_DIR / "enqueue.py"
PACKAGE = SCRIPT_DIR / "package.py"
MARK_POSTED = SCRIPT_DIR / "mark_posted.py"
SCORECARD = SCRIPT_DIR / "scorecard.py"

FROZEN_CLIS = [VERIFY_UTM, ENQUEUE, PACKAGE, MARK_POSTED, SCORECARD]

TGRERA_SLUG = "2026-07-03-tgrera-enforcement-wave"
TGRERA_DIR = REPO_ROOT / "content" / TGRERA_SLUG
CHAIN_WEEK = "2026-W27"   # A-6.2: canonical acceptance week (matches goldens/slots)

# Read-only import of a frozen module: ONLY to read the documented slot_for
# constant for the seam assertion (contract s5, disclosed in the trace). No
# mutation, no other frozen module imported.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import schedule  # noqa: E402


# =============================================================================
# Normative expectation tables (each row pinned to the FROZEN CLI's real output)
# =============================================================================

# --- Gap 0: UTM verifier (verify_utm.py <asset>) -----------------------------
# Each row: fixture dir under fixtures/, expected exit, and the discriminating
# reason substring(s) that prove the NAMED violation fired. unknown-source and
# absent-source share the code "unknown-source", so they are pinned to their
# distinct messages ("'tiktok'" vs "was absent") -- attack #2.
UTM_TABLE = [
    {"fixture": "2026-07-03-valid-asset",       "exit": 0, "reasons": ["OK"]},
    {"fixture": "2026-07-03-wrong-medium",      "exit": 1, "reasons": ["wrong-medium"]},
    {"fixture": "2026-07-03-campaign-mismatch", "exit": 1, "reasons": ["campaign-mismatch"]},
    {"fixture": "2026-07-03-unknown-source",    "exit": 1, "reasons": ["utm_source was 'tiktok'"]},
    {"fixture": "2026-07-03-absent-source",     "exit": 1, "reasons": ["utm_source was absent"]},
    {"fixture": "2026-07-03-malformed-query",   "exit": 1, "reasons": ["malformed-query"]},
    {"fixture": "2026-07-03-missing-line",      "exit": 1, "reasons": ["missing-flywheel-line"]},
    {"fixture": "2026-07-03-multi-defect",      "exit": 1, "reasons": ["wrong-medium", "unknown-source"]},
]

# --- Gap 2: publish gate + enqueue (enqueue.py <asset> --week --queue <TMP>) --
# reason: substring that must appear in the combined stdout+stderr. write=True
# means a queue file MUST exist after the run; write=False (refusal) means the
# TMP queue file must be ABSENT (no-write-on-refusal, attack #3).
GATE_TABLE = [
    {"fixture": "pass-one-channel",           "exit": 0, "reason": "queued",                    "write": True},
    {"fixture": "pass-three-channels",        "exit": 0, "reason": "queued",                    "write": True},
    {"fixture": "missing-verdict",            "exit": 1, "reason": "[missing-verdict]",          "write": False},
    {"fixture": "verdict-fail",               "exit": 1, "reason": "[verdict-not-pass]",         "write": False},
    {"fixture": "failed-checks-nonempty",     "exit": 1, "reason": "[failed-checks-nonempty]",   "write": False},
    {"fixture": "killed",                     "exit": 1, "reason": "[killed]",                   "write": False},
    {"fixture": "missing-verdict-and-killed", "exit": 1, "reason": "[missing-verdict]",          "write": False},
    {"fixture": "unparseable-verdict",        "exit": 1, "reason": "is not valid JSON",          "write": False},
    {"fixture": "no-channel",                 "exit": 2, "reason": "names no known channel",     "write": False},
    {"fixture": "unmapped-channel",           "exit": 2, "reason": "unmapped platform token",    "write": False},
]

# --- Gap 2: package generation -----------------------------------------------
# kind="pass": exit 0, packages written, per-channel invariants checked.
# kind="refuse": exit 2, cited reason, NO package dir written.
PACKAGE_TABLE = [
    {"fixture": "pkg-pass",                   "kind": "pass",   "campaign": "pkg-pass"},
    {"fixture": "pkg-multi-surface",          "kind": "pass",   "campaign": "pkg-multi-surface"},
    {"fixture": "pkg-per-channel-caption",    "kind": "pass",   "campaign": "pkg-per-channel-caption"},
    {"fixture": "pkg-no-captions",            "kind": "refuse", "exit": 2, "reason": "no captions.md"},
    {"fixture": "pkg-missing-channel-caption","kind": "refuse", "exit": 2, "reason": "no caption body for channel"},
    {"fixture": "pkg-bad-utm",                "kind": "refuse", "exit": 2, "reason": "Flywheel UTM invalid"},
    {"fixture": "pkg-empty-surfaces",         "kind": "refuse", "exit": 2, "reason": "empty or absent 'surfaces'"},
    {"fixture": "pkg-no-manifest",            "kind": "refuse", "exit": 2, "reason": "manifest.json not found"},
]

# Canonical per-channel utm_source strings (must equal utm.CHANNEL_SOURCE_MAP).
CHANNEL_SOURCE = {"instagram": "instagram", "youtube": "youtube", "linkedin": "linkedin"}


# --- Gap 3: analytics scorecard ----------------------------------------------
# Each row builds its own scorecard.py args from (FX_METRICS, out_path). kind:
#   "golden": exit 0, produced bytes == expected/<golden>; optional forbidden
#             substrings must be ABSENT and required substrings PRESENT.
#   "reject": exit 2, cited reason in stderr, out file ABSENT (no scorecard).
#   "valid" : exit 0, out present, required substrings present in the scorecard.
# fixture=None marks the dir-less "empty (no sources)" case (excluded from the
# metrics coverage set, which compares on-disk dirs to named dirs).

def _sc(*extra):
    """Base scorecard argv (week fixed) plus per-row extra flags; --out appended
    by the runner."""
    return ["--week", CHAIN_WEEK] + list(extra)


METRICS_TABLE = [
    {"fixture": "full", "kind": "golden", "golden": "full.md",
     "args": _sc("--instagram", str(FX_METRICS / "full/ig.csv"),
                 "--youtube", str(FX_METRICS / "full/yt.csv"),
                 "--linkedin", str(FX_METRICS / "full/li.csv"),
                 "--site", str(FX_METRICS / "full/site.csv"),
                 "--content-dir", str(CONTENT_FULL),
                 "--queue", str(FX_METRICS / "full/queue.json"))},
    {"fixture": None, "coverage_name": "empty", "kind": "golden", "golden": "empty.md",
     "args": _sc("--content-dir", str(CONTENT_FULL))},
    {"fixture": "wrr-partial", "kind": "golden", "golden": "wrr-partial.md",
     "forbidden": ["147", "252", "295"], "required": ["WRR component", "absent"],
     "args": _sc("--site", str(FX_METRICS / "wrr-partial/site.csv"),
                 "--content-dir", str(CONTENT_FULL))},
    {"fixture": "wrong-utm", "kind": "golden", "golden": "wrong-utm.md",
     "required": ["wrong-UTM asset 2026-07-03-bad-utm-asset"],
     "args": _sc("--instagram", str(FX_METRICS / "wrong-utm/ig.csv"),
                 "--content-dir", str(FX_METRICS / "wrong-utm/content"))},
    {"fixture": "unmatched", "kind": "golden", "golden": "unmatched.md",
     "args": _sc("--instagram", str(FX_METRICS / "unmatched/ig.csv"),
                 "--content-dir", str(CONTENT_FULL))},
    {"fixture": "truncated", "kind": "reject", "exit": 2, "reason": "expected 7",
     "args": _sc("--site", str(FX_METRICS / "truncated/site.csv"))},
    {"fixture": "wrong-header", "kind": "reject", "exit": 2, "reason": "missing required header",
     "args": _sc("--site", str(FX_METRICS / "wrong-header/site.csv"))},
    {"fixture": "wrong-colcount", "kind": "reject", "exit": 2, "reason": "expected 5",
     "args": _sc("--instagram", str(FX_METRICS / "wrong-colcount/ig.csv"))},
    {"fixture": "non-numeric", "kind": "reject", "exit": 2, "reason": "is not an integer",
     "args": _sc("--instagram", str(FX_METRICS / "non-numeric/ig.csv"))},
    {"fixture": "blank-join", "kind": "reject", "exit": 2, "reason": "blank join value",
     "args": _sc("--site", str(FX_METRICS / "blank-join/site.csv"),
                 "--content-dir", str(CONTENT_FULL))},
    {"fixture": "blank-cell", "kind": "valid",
     "required": ["| 2026-07-03-tgrera-enforcement-wave | instagram | 31 | 26 | 4 | | 11 |",
                  "craft Clicks absent for 2026-07-03-tgrera-enforcement-wave (instagram)"],
     "args": _sc("--instagram", str(FX_METRICS / "blank-cell/ig.csv"),
                 "--content-dir", str(CONTENT_FULL))},
    {"fixture": "zero-cell", "kind": "valid",
     "required": ["| 2026-07-03-tgrera-enforcement-wave | instagram | 31 | 26 | 4 | 0 | 11 |"],
     "args": _sc("--instagram", str(FX_METRICS / "zero-cell/ig.csv"),
                 "--content-dir", str(CONTENT_FULL))},
    {"fixture": "header-only", "kind": "valid",
     "required": ["WRR component 'digest_opens' absent"],
     "args": _sc("--site", str(FX_METRICS / "header-only/site.csv"),
                 "--content-dir", str(CONTENT_FULL))},
]


# =============================================================================
# Pure decision logic (unit-tested in isolation from subprocess timing)
# =============================================================================

def reason_row_ok(expected_exit, reasons, actual_exit, text):
    """(ok, detail) for a row asserted by exit code + required reason substrings.

    ``reasons`` is a list; EVERY entry must appear in ``text`` (combined
    stdout+stderr). This enforces the NAMED condition -- a nonzero exit for the
    wrong reason fails the row.
    """
    if actual_exit != expected_exit:
        return False, "exit {} != expected {}".format(actual_exit, expected_exit)
    for sub in reasons:
        if sub not in text:
            return False, "cited reason {!r} not found in output".format(sub)
    return True, "exit {} with cited reason(s) {}".format(actual_exit, reasons)


def golden_ok(produced, golden):
    """(ok, detail) for byte-for-byte scorecard equality against a golden."""
    if produced == golden:
        return True, "byte-equal golden"
    return False, "scorecard differs from golden ({} vs {} bytes)".format(
        len(produced), len(golden))


def content_invariants_ok(text, required=None, forbidden=None):
    """(ok, detail): every ``required`` substring present, every ``forbidden`` absent."""
    for sub in (forbidden or []):
        if sub in text:
            return False, "forbidden substring {!r} present (partial-sum/leak)".format(sub)
    for sub in (required or []):
        if sub not in text:
            return False, "required substring {!r} absent".format(sub)
    return True, "content invariants held"


def package_invariants_ok(pkg, channel, campaign, manifest_pngs):
    """(ok, detail) for one PACKAGE JSON, path-independent (contract s7).

    Asserts: the per-channel UTM triplet is in utm_link; the caption ends with
    that link (authored body + link); attachments' basenames match the manifest
    surface PNG order.
    """
    if not isinstance(pkg, dict):
        return False, "package is not a JSON object"
    if pkg.get("channel") != channel:
        return False, "channel {!r} != {!r}".format(pkg.get("channel"), channel)
    src = CHANNEL_SOURCE[channel]
    triplet = "utm_source={}&utm_medium=social&utm_campaign={}".format(src, campaign)
    link = pkg.get("utm_link") or ""
    if triplet not in link:
        return False, "utm_link {!r} missing triplet {!r}".format(link, triplet)
    caption = pkg.get("caption") or ""
    if not caption.endswith(link):
        return False, "caption does not end with the channel utm_link"
    attachments = pkg.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        return False, "attachments empty/absent"
    got = [Path(a).name for a in attachments]
    if got != manifest_pngs:
        return False, "attachments {} != manifest order {}".format(got, manifest_pngs)
    return True, "package invariants held"


def parse_ab_row(text, channel):
    """Return (morning_cell, evening_cell) of the Posting-time A/B row for
    ``channel``, or None if not found. The A/B row starts ``| <channel> |`` (4
    data cells); craft-diagnostics rows start with an asset slug, so no collision.
    """
    prefix = "| {} |".format(channel)
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 4:  # channel | morning | evening | verdict
                return cells[1], cells[2]
    return None


def bucket_from_slot(slot):
    """'morning' or 'evening' from a schedule slot 'YYYY-Www/<bucket>/HH:MM'."""
    parts = (slot or "").split("/")
    return parts[1] if len(parts) >= 2 else ""


def seam_ab_ok(scorecard_text, channel, queue_slot):
    """(ok, detail): the scorecard's A/B column populated for ``channel`` is the
    bucket the PUBLISH layer wrote into the queue (the load-bearing cross-gap
    assertion). Driven by the generated queue slot, NOT a hardcoded value.
    """
    bucket = bucket_from_slot(queue_slot)
    if bucket not in ("morning", "evening"):
        return False, "queue slot {!r} has no morning/evening bucket".format(queue_slot)
    row = parse_ab_row(scorecard_text, channel)
    if row is None:
        return False, "no A/B row for {}".format(channel)
    morning, evening = row
    if bucket == "morning":
        if morning and not evening:
            return True, "A/B morning column driven by queue slot"
        return False, "queue bucket morning but A/B row is (m={!r}, e={!r})".format(morning, evening)
    # evening
    if evening and not morning:
        return True, "A/B evening column driven by queue slot"
    return False, "queue bucket evening but A/B row is (m={!r}, e={!r})".format(morning, evening)


def table_coverage_error(on_disk, in_table, family):
    """None if the table names exactly the on-disk fixture dirs, else a message.
    Guards against a stray unchecked fixture or a deleted named one (attack #8).
    """
    on_disk = set(on_disk)
    in_table = set(in_table)
    missing_from_table = sorted(on_disk - in_table)
    if missing_from_table:
        return "{}: fixture dir(s) on disk not named by any table row: {}".format(
            family, missing_from_table)
    missing_from_disk = sorted(in_table - on_disk)
    if missing_from_disk:
        return "{}: table row(s) name a missing fixture dir: {}".format(
            family, missing_from_disk)
    return None


# =============================================================================
# Subprocess invocation (the real shell contract)
# =============================================================================

def _run(cmd):
    """Run a subprocess from the repo root; return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _emit_verbose(out, err, lines, tmp=None):
    """Echo a CLI's stdout/stderr under a row. The throwaway temp dir path is
    normalized to ``<TMP>`` so ``--verbose`` output is byte-identical across runs
    (the mkdtemp name is random; contract s3.1 determinism claim)."""
    tmp_str = str(tmp) if tmp is not None else None

    def norm(s):
        return s.replace(tmp_str, "<TMP>") if tmp_str else s

    for raw in (out or "").splitlines():
        lines.append("    | out: {}".format(norm(raw)))
    for raw in (err or "").splitlines():
        lines.append("    | err: {}".format(norm(raw)))


def _manifest_pngs(asset_dir):
    """Ordered surface PNG basenames from an asset's render/manifest.json."""
    data = json.loads((asset_dir / "render" / "manifest.json").read_text(encoding="utf-8"))
    return [Path(s["png"]).name for s in data["surfaces"]]


# =============================================================================
# Family runners
# =============================================================================

def run_utm(lines, verbose):
    met = 0
    for row in UTM_TABLE:
        fx = FIXTURES / row["fixture"]
        code, out, err = _run([sys.executable, VERIFY_UTM, fx])
        ok, detail = reason_row_ok(row["exit"], row["reasons"], code, out + err)
        lines.append("{} utm/{} — {}".format("PASS" if ok else "FAIL", row["fixture"], detail))
        if verbose:
            _emit_verbose(out, err, lines, None)
        met += 1 if ok else 0
    return met, len(UTM_TABLE)


def run_gate(tmp, lines, verbose):
    met = 0
    for row in GATE_TABLE:
        fx = FX_PUBLISH / row["fixture"]
        qpath = tmp / "gate-{}-q.json".format(row["fixture"])
        code, out, err = _run([sys.executable, ENQUEUE, fx,
                               "--week", CHAIN_WEEK, "--queue", qpath])
        ok, detail = reason_row_ok(row["exit"], [row["reason"]], code, out + err)
        if ok:
            wrote = qpath.exists()
            if wrote != row["write"]:
                ok = False
                detail = "queue write={} but expected write={}".format(wrote, row["write"])
            elif not row["write"]:
                detail += "; no-write-on-refusal confirmed"
        lines.append("{} gate/{} — {}".format("PASS" if ok else "FAIL", row["fixture"], detail))
        if verbose:
            _emit_verbose(out, err, lines, tmp)
        met += 1 if ok else 0
    return met, len(GATE_TABLE)


def run_package(tmp, lines, verbose):
    met = 0
    for row in PACKAGE_TABLE:
        fx = FX_PUBLISH / row["fixture"]
        qpath = tmp / "pkg-{}-q.json".format(row["fixture"])
        pubdir = tmp / "pkg-{}-pub".format(row["fixture"])
        code, out, err = _run([sys.executable, PACKAGE, fx, "--week", CHAIN_WEEK,
                               "--queue", qpath, "--publish-dir", pubdir])
        if row["kind"] == "refuse":
            ok, detail = reason_row_ok(row["exit"], [row["reason"]], code, out + err)
            if ok and pubdir.exists():
                ok, detail = False, "package dir written despite refusal (no-write violated)"
            elif ok:
                detail += "; no package written"
        else:  # pass: exit 0 + per-channel invariants
            ok, detail = reason_row_ok(0, [], code, out + err)
            if ok:
                try:
                    manifest_pngs = _manifest_pngs(fx)
                    for chan in ("instagram", "youtube", "linkedin"):
                        pkg_file = pubdir / "{}.json".format(chan)
                        if not pkg_file.exists():
                            ok, detail = False, "missing package {}".format(pkg_file.name)
                            break
                        pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
                        pok, pdetail = package_invariants_ok(pkg, chan, row["campaign"], manifest_pngs)
                        if not pok:
                            ok, detail = False, "{}: {}".format(chan, pdetail)
                            break
                    else:
                        detail = "3 packages, per-channel utm_link/caption/attachments invariants held"
                except (OSError, ValueError, KeyError) as exc:
                    ok, detail = False, "package read error: {}".format(exc)
        lines.append("{} package/{} — {}".format("PASS" if ok else "FAIL", row["fixture"], detail))
        if verbose:
            _emit_verbose(out, err, lines, tmp)
        met += 1 if ok else 0
    return met, len(PACKAGE_TABLE)


def run_mark_posted(tmp, lines, verbose):
    """mark_posted rows over a freshly-prepared queue (pass fixture enqueued).

    These rows have no fixture DIR (they act on a slug in a queue), so they are
    NOT part of coverage -- they are extra transition assertions.
    """
    # Prepare a queue with a queued instagram row via the frozen enqueue.
    qpath = tmp / "mp-q.json"
    fx = FX_PUBLISH / "pass-three-channels"
    _run([sys.executable, ENQUEUE, fx, "--week", CHAIN_WEEK, "--queue", qpath])
    slug = "pass-three-channels"

    checks = [
        {"name": "posted-ok", "argv": [slug, "instagram", "--posted-on", "2026-07-06",
                                       "--permalink", "https://instagram.com/p/EXAMPLE"],
         "exit": 0, "reason": "posted"},
        {"name": "already-posted", "argv": [slug, "instagram", "--posted-on", "2026-07-06",
                                            "--permalink", "https://instagram.com/p/EXAMPLE"],
         "exit": 1, "reason": "already posted"},
        {"name": "empty-permalink", "argv": [slug, "youtube", "--posted-on", "2026-07-06",
                                             "--permalink", ""],
         "exit": 2, "reason": "permalink must be non-empty"},
        {"name": "unknown-channel", "argv": [slug, "tiktok", "--posted-on", "2026-07-06",
                                             "--permalink", "https://x.example/p"],
         "exit": 2, "reason": "unknown channel"},
        {"name": "missing-slug", "argv": ["no-such-slug", "instagram", "--posted-on", "2026-07-06",
                                          "--permalink", "https://x.example/p"],
         "exit": 2, "reason": "no queue row for"},
    ]
    met = 0
    for chk in checks:
        code, out, err = _run([sys.executable, MARK_POSTED] + chk["argv"] + ["--queue", qpath])
        ok, detail = reason_row_ok(chk["exit"], [chk["reason"]], code, out + err)
        lines.append("{} mark_posted/{} — {}".format("PASS" if ok else "FAIL", chk["name"], detail))
        if verbose:
            _emit_verbose(out, err, lines, tmp)
        met += 1 if ok else 0
    return met, len(checks)


def run_metrics(tmp, lines, verbose):
    met = 0
    for i, row in enumerate(METRICS_TABLE):
        name = row["fixture"] or row.get("coverage_name", "empty")
        out_path = tmp / "sc-{}-{}.md".format(i, name)
        code, out, err = _run([sys.executable, SCORECARD] + row["args"] + ["--out", out_path])
        if row["kind"] == "reject":
            ok, detail = reason_row_ok(row["exit"], [row["reason"]], code, out + err)
            if ok and out_path.exists():
                ok, detail = False, "scorecard written despite malformed-CSV rejection"
            elif ok:
                detail += "; no scorecard written"
        elif row["kind"] == "golden":
            ok, detail = reason_row_ok(0, [], code, out + err)
            if ok:
                if not out_path.exists():
                    ok, detail = False, "no scorecard produced"
                else:
                    produced = out_path.read_text(encoding="utf-8")
                    golden = (FX_EXPECTED / row["golden"]).read_text(encoding="utf-8")
                    ok, detail = golden_ok(produced, golden)
                    if ok:
                        cok, cdetail = content_invariants_ok(
                            produced, row.get("required"), row.get("forbidden"))
                        if not cok:
                            ok, detail = False, cdetail
        else:  # valid
            ok, detail = reason_row_ok(0, [], code, out + err)
            if ok:
                if not out_path.exists():
                    ok, detail = False, "no scorecard produced"
                else:
                    produced = out_path.read_text(encoding="utf-8")
                    ok, detail = content_invariants_ok(produced, row.get("required"))
        lines.append("{} metrics/{} — {}".format("PASS" if ok else "FAIL", name, detail))
        if verbose:
            _emit_verbose(out, err, lines, tmp)
        met += 1 if ok else 0
    return met, len(METRICS_TABLE)


# =============================================================================
# Cross-gap seam chain (the "both gaps" proof)
# =============================================================================

def run_chain(tmp, lines, verbose):
    """verify_utm -> enqueue -> package -> mark_posted -> scorecard on the real
    PASS asset, all writes into TMP, seam bucket driven by the generated queue.
    Returns (met, total). Fails fast at the first broken step.
    """
    total = 6
    q = tmp / "chain-q.json"
    pub = tmp / "chain-pub"

    def fail(step, why):
        lines.append("FAIL chain/{} — {}".format(step, why))
        return 0, total

    # 1. verify_utm
    code, out, err = _run([sys.executable, VERIFY_UTM, TGRERA_DIR])
    if verbose:
        _emit_verbose(out, err, lines, tmp)
    if code != 0 or "OK" not in out:
        return fail("verify_utm", "exit {} (expected 0/OK)".format(code))
    lines.append("PASS chain/verify_utm — OK")

    # 2. enqueue -> 3 queued rows sorted (instagram, linkedin, youtube)
    code, out, err = _run([sys.executable, ENQUEUE, TGRERA_DIR,
                           "--week", CHAIN_WEEK, "--queue", q])
    if verbose:
        _emit_verbose(out, err, lines, tmp)
    if code != 0 or not q.exists():
        return fail("enqueue", "exit {} or no queue".format(code))
    rows = json.loads(q.read_text(encoding="utf-8"))["rows"]
    ordered = [(r["slug"], r["channel"], r["state"]) for r in rows]
    expect = [(TGRERA_SLUG, c, "queued") for c in ("instagram", "linkedin", "youtube")]
    if ordered != expect:
        return fail("enqueue", "rows {} != {}".format(ordered, expect))
    lines.append("PASS chain/enqueue — 3 queued rows, canonical (slug,channel) order")

    # 3. package -> 3 PACKAGE JSONs; invariants + generated slots == slot_for
    code, out, err = _run([sys.executable, PACKAGE, TGRERA_DIR, "--week", CHAIN_WEEK,
                           "--queue", q, "--publish-dir", pub])
    if verbose:
        _emit_verbose(out, err, lines, tmp)
    if code != 0:
        return fail("package", "exit {}".format(code))
    manifest_pngs = _manifest_pngs(TGRERA_DIR)
    campaign = "tgrera-enforcement-wave"
    for chan in ("instagram", "youtube", "linkedin"):
        pkg_file = pub / "{}.json".format(chan)
        if not pkg_file.exists():
            return fail("package", "missing {}".format(pkg_file.name))
        pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
        pok, pdetail = package_invariants_ok(pkg, chan, campaign, manifest_pngs)
        if not pok:
            return fail("package", "{}: {}".format(chan, pdetail))
    gen_rows = {r["channel"]: r for r in json.loads(q.read_text(encoding="utf-8"))["rows"]}
    for chan in ("instagram", "youtube", "linkedin"):
        want = schedule.slot_for(CHAIN_WEEK, chan)
        got = gen_rows[chan]["schedule_slot"]
        if got != want:
            return fail("package", "{} slot {!r} != slot_for {!r}".format(chan, got, want))
    lines.append("PASS chain/package — 3 packages; utm_link/caption/attachments + "
                 "generated slots == schedule.slot_for")

    # 4. mark_posted instagram -> posted; others stay queued
    code, out, err = _run([sys.executable, MARK_POSTED, TGRERA_SLUG, "instagram",
                           "--posted-on", "2026-07-06",
                           "--permalink", "https://instagram.com/p/EXAMPLE",
                           "--queue", q])
    if verbose:
        _emit_verbose(out, err, lines, tmp)
    if code != 0:
        return fail("mark_posted", "exit {}".format(code))
    states = {r["channel"]: r["state"] for r in json.loads(q.read_text(encoding="utf-8"))["rows"]}
    if states.get("instagram") != "posted" or states.get("youtube") != "queued" \
            or states.get("linkedin") != "queued":
        return fail("mark_posted", "states {}".format(states))
    lines.append("PASS chain/mark_posted — instagram posted; youtube/linkedin still queued")

    # 5. scorecard reads the GENERATED queue -> A/B bucket driven by its slot
    ig_slot = {r["channel"]: r["schedule_slot"]
               for r in json.loads(q.read_text(encoding="utf-8"))["rows"]}["instagram"]
    s_out = tmp / "chain-sc.md"
    code, out, err = _run([sys.executable, SCORECARD, "--week", CHAIN_WEEK,
                           "--instagram", str(FX_METRICS / "full/ig.csv"),
                           "--youtube", str(FX_METRICS / "full/yt.csv"),
                           "--linkedin", str(FX_METRICS / "full/li.csv"),
                           "--site", str(FX_METRICS / "full/site.csv"),
                           "--content-dir", str(REPO_ROOT / "content"),
                           "--queue", q, "--out", s_out])
    if verbose:
        _emit_verbose(out, err, lines, tmp)
    if code != 0 or not s_out.exists():
        return fail("scorecard", "exit {} or no scorecard".format(code))
    sc_text = s_out.read_text(encoding="utf-8")
    sok, sdetail = seam_ab_ok(sc_text, "instagram", ig_slot)
    if not sok:
        return fail("scorecard-seam", sdetail)
    lines.append("PASS chain/scorecard-seam — {} (queue slot {})".format(sdetail, ig_slot))

    # 6. idempotency: re-run enqueue+package, no dup rows, no posted regression
    _run([sys.executable, ENQUEUE, TGRERA_DIR, "--week", CHAIN_WEEK, "--queue", q])
    code, out, err = _run([sys.executable, PACKAGE, TGRERA_DIR, "--week", CHAIN_WEEK,
                           "--queue", q, "--publish-dir", pub])
    if verbose:
        _emit_verbose(out, err, lines, tmp)
    rows2 = json.loads(q.read_text(encoding="utf-8"))["rows"]
    states2 = {r["channel"]: r["state"] for r in rows2}
    if len(rows2) != 3:
        return fail("idempotency", "rowcount {} != 3 (duplicate rows)".format(len(rows2)))
    if states2.get("instagram") != "posted":
        return fail("idempotency", "instagram regressed from posted to {}".format(
            states2.get("instagram")))
    lines.append("PASS chain/idempotency — 3 rows on re-run, instagram stays posted")

    return total, total


# =============================================================================
# Orchestration
# =============================================================================

def precondition_error():
    """Return a message (exit-2) if a frozen CLI file or the real PASS asset is
    missing, else None."""
    for cli in FROZEN_CLIS:
        if not cli.is_file():
            return "frozen CLI missing: {}".format(cli)
    if not (TGRERA_DIR / "meta.md").is_file():
        return "real PASS asset missing: {}".format(TGRERA_DIR)
    if not FX_EXPECTED.is_dir():
        return "golden scorecard dir missing: {}".format(FX_EXPECTED)
    return None


def coverage_errors():
    """Return a list of coverage error messages (empty if all three families are
    exactly covered)."""
    errs = []
    # UTM family: fixtures/ immediate dirs with a date prefix (excludes metrics/, publish/).
    utm_disk = [p.name for p in FIXTURES.iterdir()
                if p.is_dir() and len(p.name) > 11 and p.name[:4].isdigit()
                and p.name[4] == "-" and p.name[7] == "-" and p.name[10] == "-"]
    utm_named = [r["fixture"] for r in UTM_TABLE]
    e = table_coverage_error(utm_disk, utm_named, "utm")
    if e:
        errs.append(e)
    # Publish family: fixtures/publish/ immediate dirs (gate + package rows).
    pub_disk = [p.name for p in FX_PUBLISH.iterdir() if p.is_dir()]
    pub_named = [r["fixture"] for r in GATE_TABLE] + [r["fixture"] for r in PACKAGE_TABLE]
    e = table_coverage_error(pub_disk, pub_named, "publish")
    if e:
        errs.append(e)
    # Metrics family: fixtures/metrics/ immediate dirs minus expected/ (goldens).
    met_disk = [p.name for p in FX_METRICS.iterdir()
                if p.is_dir() and p.name != "expected"]
    met_named = [r["fixture"] for r in METRICS_TABLE if r["fixture"] is not None]
    e = table_coverage_error(met_disk, met_named, "metrics")
    if e:
        errs.append(e)
    return errs


def run_all(verbose=False):
    """Run the whole contract. Return (exit_code, report_lines)."""
    lines = []

    pre = precondition_error()
    if pre:
        lines.append("PRECONDITION FAIL — {}".format(pre))
        return 2, lines

    cov_errs = coverage_errors()
    if cov_errs:
        for e in cov_errs:
            lines.append("FAIL coverage — {}".format(e))
        lines.append("ACCEPTANCE: FAIL (table coverage incomplete) — first unmet: "
                     "coverage — {}".format(cov_errs[0]))
        return 1, lines

    tmp = Path(tempfile.mkdtemp(prefix="mktg-loops-accept-"))
    try:
        met = 0
        total = 0
        for runner in (run_utm,):
            m, t = runner(lines, verbose)
            met += m
            total += t
        for runner in (run_gate, run_package, run_mark_posted, run_metrics):
            m, t = runner(tmp, lines, verbose)
            met += m
            total += t
        cm, ct = run_chain(tmp, lines, verbose)
        met += cm
        total += ct
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if met == total:
        lines.append("ACCEPTANCE: PASS ({}/{} expectations met)".format(met, total))
        return 0, lines
    first = next((ln[len("FAIL "):] for ln in lines if ln.startswith("FAIL ")), "unknown")
    lines.append("ACCEPTANCE: FAIL ({}/{} expectations met) — first unmet: {}".format(
        met, total, first))
    return 1, lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Cross-gap end-to-end acceptance for the marketing-loops "
                    "publish + analytics toolchains (spec s11). Exit 0 iff both "
                    "gaps hold over the committed fixtures and the seam chain.")
    parser.add_argument("--verbose", action="store_true",
                        help="under each row, echo the invoked CLI's stdout/stderr; "
                             "the terse row summary is unchanged")
    args = parser.parse_args(argv)

    exit_code, lines = run_all(args.verbose)
    for ln in lines:
        print(ln)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
