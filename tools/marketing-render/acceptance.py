#!/usr/bin/env python3
"""End-to-end acceptance runner for the Asset Renderer + QA Gate (Sprint 005).

Proves the whole gate in one deterministic, no-network run:

  1. TGRERA positive end-to-end + determinism proof (v2 carousel baseline,
     Sprint-006 conscious re-point — Risk 2/C). TGRERA moved from a frozen
     1080x1920 chart-card to a 1080x1350 format-slide carousel + carousel.pdf:
     - render the asset via render.py; assert it emits format-*.png +
       carousel.pdf + a schema-"2" manifest whose surfaces are all
       format-slide, and NO chart-card.png,
     - hash each format PNG by DECODED-RGBA (R8) and carousel.pdf by raw
       BYTES (R16),
     - delete render/ and re-render; assert decoded-RGBA PNGs pixel-identical
       (R8) AND carousel.pdf byte-identical (R16),
     - validate.py the asset -> exit 0, verdict PASS, no failed checks.
     Reactive-single (chart-card) render+validate coverage is retained via the
     frozen fx-good-min fixture, so it is not lost by this re-point.

  2. Every committed fixture reaches its expected verdict on the RIGHT check
     with the RIGHT rule cited (not merely "some FAIL"). The expectation table
     below uses the exact id/rule strings validate.py emits; the runner reads
     the real emitted strings from qa-verdict.json at run time.

This runner invokes the real CLIs as subprocesses (not by importing their
main()), so it exercises the exact shell contract an operator or the /loop-qa
skill uses -- exit codes and JSON output included.

Stdlib only. No network. See contract sprint_005 s6.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# --- Paths (resolved from this file, so the runner works from any cwd) -------
SCRIPT_DIR = Path(__file__).resolve().parent           # tools/marketing-render/
REPO_ROOT = SCRIPT_DIR.parents[1]                      # repo root
FIXTURES_DIR = SCRIPT_DIR / "fixtures"
RENDER_PY = SCRIPT_DIR / "render.py"
VALIDATE_PY = SCRIPT_DIR / "validate.py"
TGRERA_SLUG = "2026-07-03-tgrera-enforcement-wave"
TGRERA_DIR = REPO_ROOT / "content" / TGRERA_SLUG

DEFAULT_CHECKED_ON = "2026-07-04"  # sprint baseline (contract s6, H-001 Option B)

# --- Normative expectation table (contract s6.2) -----------------------------
# Every row is mandatory. expected_check_id is a literal, full check-id string
# (exact-id equality, no wildcards). expected_rule_substring is a substring test
# on the emitted `rule` field. fx-good-min is the positive control (exit 0).
EXPECTATIONS = [
    {"fixture": "fx-11-word-hook",   "expected_exit": 1, "expected_check_id": "V7-hook-words",       "expected_rule_substring": "qa-checklist.md §Carousel"},
    {"fixture": "fx-truncated-axis", "expected_exit": 1, "expected_check_id": "V10-chart-integrity", "expected_rule_substring": "qa-checklist.md §Chart integrity"},
    {"fixture": "fx-low-contrast",   "expected_exit": 1, "expected_check_id": "V4-contrast",         "expected_rule_substring": "brand-kit.md §3"},
    {"fixture": "fx-missing-source", "expected_exit": 1, "expected_check_id": "V8-source-stamp",     "expected_rule_substring": "qa-checklist.md §Chart integrity"},
    {"fixture": "fx-blank-png",      "expected_exit": 1, "expected_check_id": "V3-ink",              "expected_rule_substring": "spec §5.2 V3"},
    {"fixture": "fx-good-min",       "expected_exit": 0, "expected_check_id": None,                  "expected_rule_substring": None},
    {"fixture": "fx-size-lie",       "expected_exit": 1, "expected_check_id": "V5-crosscheck",       "expected_rule_substring": "spec §5.2 V5"},
    {"fixture": "fx-small-headline", "expected_exit": 1, "expected_check_id": "V5-floor",            "expected_rule_substring": "qa-checklist.md §Typography"},
    {"fixture": "fx-out-of-safezone","expected_exit": 1, "expected_check_id": "V6-safezone",         "expected_rule_substring": "qa-checklist.md §Layout"},
    {"fixture": "fx-blacklist",      "expected_exit": 1, "expected_check_id": "V9-blacklist",        "expected_rule_substring": "brand-kit.md §8"},
    {"fixture": "fx-no-provenance",  "expected_exit": 1, "expected_check_id": "V11-provenance",      "expected_rule_substring": "qa-checklist.md §Data provenance"},
    {"fixture": "fx-canvas-mismatch","expected_exit": 1, "expected_check_id": "V2-canvas",           "expected_rule_substring": "qa-checklist.md §Layout"},
    # --- Sprint 005 (run 003) v2 format-slide rows (contract s6.2). v1 rows above
    # are byte-identical; these 9 add the QA Gate V2 coverage. Each adversarial
    # fixture fires EXACTLY its one named check (one-fixture-one-check). ---
    {"fixture": "fx-v2-good",          "expected_exit": 0, "expected_check_id": None,                 "expected_rule_substring": None},
    {"fixture": "fx-v2-dominant-small","expected_exit": 1, "expected_check_id": "V13-dominant-ratio", "expected_rule_substring": "PIPELINE-V2.md §4"},
    {"fixture": "fx-v2-body-24",       "expected_exit": 1, "expected_check_id": "V14-type-floor",     "expected_rule_substring": "qa-checklist.md §Typography"},
    {"fixture": "fx-v2-no-wordmark",   "expected_exit": 1, "expected_check_id": "V14-wordmark",       "expected_rule_substring": "qa-checklist.md §Typography"},
    {"fixture": "fx-v2-thumb-illegible","expected_exit": 1, "expected_check_id": "V15-thumbnail",     "expected_rule_substring": "PIPELINE-V2.md §4"},
    {"fixture": "fx-v2-no-so-what",    "expected_exit": 1, "expected_check_id": "V16-so-what",        "expected_rule_substring": "PIPELINE-V2.md §4"},
    {"fixture": "fx-v2-bad-cover",     "expected_exit": 1, "expected_check_id": "V17-cover-pattern",  "expected_rule_substring": "PIPELINE-V2.md §4"},
    {"fixture": "fx-v2-no-dataset",    "expected_exit": 1, "expected_check_id": "V19-one-dataset",    "expected_rule_substring": "PIPELINE-V2.md §4"},
    {"fixture": "fx-v2-11-slides",     "expected_exit": 1, "expected_check_id": "V18-slide-count",    "expected_rule_substring": "PIPELINE-V2.md §4"},
]


# --- Pure decision logic (unit-tested in isolation, contract s3) -------------

def verdict_is_pass(verdict):
    """True iff the parsed qa-verdict.json dict is a clean PASS."""
    if not isinstance(verdict, dict):
        return False
    return verdict.get("verdict") == "PASS" and verdict.get("failed_checks") == []


def failed_check_matches(verdict, expected_check_id, expected_rule_substring):
    """True iff failed_checks contains an entry whose id == expected_check_id
    AND whose rule contains expected_rule_substring. This enforces the NAMED
    check firing -- "some FAIL" is not accepted."""
    if not isinstance(verdict, dict):
        return False
    for entry in verdict.get("failed_checks", []):
        if (entry.get("id") == expected_check_id
                and expected_rule_substring in (entry.get("rule") or "")):
            return True
    return False


def evaluate_row(row, exit_code, verdict):
    """Return (ok: bool, detail: str) for one fixture expectation.

    A row is met only when the exit code matches AND (for FAIL rows) the named
    check fired with the cited rule, or (for the PASS row) the verdict is a
    clean PASS. A wrong-check FAIL, a PASS where FAIL was expected, or a
    mismatched exit code all make ok=False.
    """
    exp_exit = row["expected_exit"]
    if exit_code != exp_exit:
        return False, "exit {} != expected {}".format(exit_code, exp_exit)

    if exp_exit == 0:
        if verdict_is_pass(verdict):
            return True, "PASS (verdict PASS, no failed checks)"
        return False, "exit 0 but verdict is not a clean PASS: {}".format(
            (verdict or {}).get("verdict"))

    # FAIL expectation: the NAMED check must fire cited by its rule.
    cid = row["expected_check_id"]
    rule = row["expected_rule_substring"]
    if failed_check_matches(verdict, cid, rule):
        return True, "{} ({}) fired as expected".format(cid, rule)
    got = [(e.get("id"), e.get("rule")) for e in (verdict or {}).get("failed_checks", [])]
    return False, "expected {} ({}) not in failed_checks; got {}".format(cid, rule, got)


def table_coverage_error(fixtures_dir, table=EXPECTATIONS):
    """Return None if the table covers exactly the committed fixture dirs, else
    a message. A fixture directory not in the table (or a table row with no
    directory) is an error -- the table must cover the full committed set."""
    on_disk = {p.name for p in Path(fixtures_dir).iterdir()
               if p.is_dir() and p.name.startswith("fx-")}
    in_table = {row["fixture"] for row in table}
    missing_from_table = sorted(on_disk - in_table)
    if missing_from_table:
        return "fixture(s) on disk not in expectation table: {}".format(missing_from_table)
    missing_from_disk = sorted(in_table - on_disk)
    if missing_from_disk:
        return "expectation table row(s) with no fixture directory: {}".format(missing_from_disk)
    return None


# --- Subprocess invocation (real shell contract) -----------------------------

def _run(cmd):
    """Run a subprocess, return (returncode, stdout, stderr). No network."""
    proc = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_render(asset_folder):
    return _run([sys.executable, RENDER_PY, asset_folder])[0]


def run_validate(asset_folder, checked_on):
    """Invoke validate.py; return (exit_code, verdict_dict_or_None, stdout)."""
    exit_code, out, _err = _run(
        [sys.executable, VALIDATE_PY, asset_folder, "--checked-on", checked_on])
    verdict_path = Path(asset_folder) / "render" / "qa-verdict.json"
    verdict = None
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text())
        except (ValueError, OSError):
            verdict = None
    return exit_code, verdict, out


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Orchestration -----------------------------------------------------------

def _emit_validate_stdout(out, lines):
    """When --verbose, echo the invoked validate.py stdout indented under a row."""
    for raw in (out or "").splitlines():
        lines.append("    | {}".format(raw))


TGRERA_EXPECTATIONS = 4  # render-shape, PNG determinism, PDF determinism, validate


def _decoded_rgba_sha(png_path):
    """SHA-256 of a PNG's decoded RGBA pixels (R8 pixel-identity, not file bytes)."""
    import hashlib
    from PIL import Image
    with Image.open(png_path) as img:
        return hashlib.sha256(img.convert("RGBA").tobytes()).hexdigest()


def _render_dir():
    return TGRERA_DIR / "render"


def _tgrera_baseline():
    """Render TGRERA and return (ok, err, png_shas, pdf_sha) for the v2 carousel.

    ok is False (with err set) if the render shape is wrong: a chart-card.png
    present, a manifest not schema "2", any non-format-slide surface, or a
    missing carousel.pdf. png_shas maps each format PNG name -> decoded-RGBA SHA
    (derived from the manifest surfaces, never hardcoded to a slide count)."""
    render_dir = _render_dir()
    if run_render(str(TGRERA_DIR)) != 0:
        return False, "render.py exited non-zero", {}, None
    manifest_path = render_dir / "manifest.json"
    if not manifest_path.exists():
        return False, "no manifest.json emitted", {}, None
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != "2":
        return False, "manifest schema_version != '2' (got {!r})".format(
            manifest.get("schema_version")), {}, None
    if (render_dir / "chart-card.png").exists():
        return False, "chart-card.png present — TGRERA must render a pure carousel (Risk B)", {}, None
    roles = [s.get("role") for s in manifest.get("surfaces", [])]
    if not roles or any(r != "format-slide" for r in roles):
        return False, "surfaces not all format-slide (got {})".format(roles), {}, None
    pdf_name = manifest.get("pdf")
    if not pdf_name or not (render_dir / pdf_name).exists():
        return False, "carousel.pdf missing (manifest pdf={!r})".format(pdf_name), {}, None
    png_shas = {}
    for s in manifest["surfaces"]:
        png = render_dir / s["png"]
        if not png.exists():
            return False, "declared PNG not emitted: {}".format(s["png"]), {}, None
        png_shas[s["png"]] = _decoded_rgba_sha(png)
    pdf_sha = _sha256(render_dir / pdf_name)
    return True, None, png_shas, pdf_sha


def run_tgrera(checked_on, lines, verbose=False):
    """Positive end-to-end + determinism on the v2 carousel baseline (Risk 2/C).

    Four expectations, each an explicit PASS/FAIL line (kept in sync with
    TGRERA_EXPECTATIONS): render-shape, PNG decoded-RGBA determinism (R8),
    carousel.pdf byte determinism (R16), full-gate validate PASS (exit 0).
    Returns True iff all four hold."""
    import shutil

    # Expectation 1 — render shape: format-*.png + carousel.pdf + schema "2",
    # all surfaces format-slide, NO chart-card.png.
    if _render_dir().exists():
        shutil.rmtree(_render_dir())
    ok, err, base_pngs, base_pdf = _tgrera_baseline()
    if not ok:
        lines.append("FAIL tgrera-render — {}".format(err))
        return False
    lines.append(
        "PASS tgrera-render — {} format-slide PNG(s) + carousel.pdf, schema \"2\", "
        "no chart-card.png".format(len(base_pngs)))

    # Expectations 2 & 3 — determinism: re-render and compare.
    shutil.rmtree(_render_dir())
    ok, err, re_pngs, re_pdf = _tgrera_baseline()
    if not ok:
        lines.append("FAIL tgrera-render — re-render shape changed: {}".format(err))
        return False
    if re_pngs != base_pngs:
        diff = [n for n in base_pngs if re_pngs.get(n) != base_pngs[n]]
        lines.append("FAIL tgrera-determinism-png — decoded-RGBA SHA changed on "
                     "re-render for {} (R8)".format(diff or "png set mismatch"))
        return False
    lines.append("PASS tgrera-determinism-png — {} format PNG(s) decoded-RGBA "
                 "pixel-identical on re-render (R8)".format(len(base_pngs)))
    if re_pdf != base_pdf:
        lines.append("FAIL tgrera-determinism-pdf — carousel.pdf bytes changed "
                     "on re-render {} != {} (R16)".format(re_pdf[:12], base_pdf[:12]))
        return False
    lines.append("PASS tgrera-determinism-pdf — carousel.pdf byte-identical on "
                 "re-render (R16)")

    # Expectation 4 — full V2 gate PASS.
    exit_code, verdict, out = run_validate(str(TGRERA_DIR), checked_on)
    ok, detail = evaluate_row(
        {"expected_exit": 0, "expected_check_id": None, "expected_rule_substring": None},
        exit_code, verdict)
    status = "PASS" if ok else "FAIL"
    lines.append("{} tgrera-validate — exit {}, {}".format(status, exit_code, detail))
    if verbose:
        _emit_validate_stdout(out, lines)
    return ok


def run_fixtures(checked_on, lines, verbose=False):
    """Run all 12 fixtures. Return (all_ok, met, total)."""
    met = 0
    total = len(EXPECTATIONS)
    all_ok = True
    for row in EXPECTATIONS:
        fx_dir = FIXTURES_DIR / row["fixture"]
        if not fx_dir.is_dir():
            lines.append("FAIL {} — fixture directory not found: {}".format(
                row["fixture"], fx_dir))
            all_ok = False
            continue
        exit_code, verdict, out = run_validate(str(fx_dir), checked_on)
        ok, detail = evaluate_row(row, exit_code, verdict)
        cited = row["expected_check_id"] or "PASS"
        rule = row["expected_rule_substring"] or "-"
        status = "PASS" if ok else "FAIL"
        lines.append("{} {} — exit {}, {} ({}) [expected exit {}] {}".format(
            status, row["fixture"], exit_code, cited, rule,
            row["expected_exit"], "" if ok else "<< " + detail))
        if verbose:
            _emit_validate_stdout(out, lines)
        if ok:
            met += 1
        else:
            all_ok = False
    return all_ok, met, total


def run_gate(checked_on, verbose=False):
    """Run the full gate. Return (exit_code, summary_lines)."""
    lines = []

    cov_err = table_coverage_error(FIXTURES_DIR)
    if cov_err:
        lines.append("FAIL table-coverage — {}".format(cov_err))
        lines.append("ACCEPTANCE: FAIL (expectation table does not cover committed fixtures)")
        return 1, lines

    tgrera_ok = run_tgrera(checked_on, lines, verbose)
    fixtures_ok, met, total = run_fixtures(checked_on, lines, verbose)

    # met/total counts fixtures; TGRERA's v2 baseline adds TGRERA_EXPECTATIONS
    # (render-shape, PNG determinism, PDF determinism, validate) — Risk 2/C.
    tgrera_expectations = TGRERA_EXPECTATIONS
    tgrera_met = tgrera_expectations if tgrera_ok else 0
    # If tgrera partially failed, run_tgrera returns False on first failure; be honest:
    if not tgrera_ok:
        # count how many tgrera PASS lines we actually printed
        tgrera_met = sum(1 for ln in lines if ln.startswith("PASS tgrera"))
    grand_met = met + tgrera_met
    grand_total = total + tgrera_expectations

    if tgrera_ok and fixtures_ok:
        lines.append("ACCEPTANCE: PASS ({}/{} expectations met)".format(grand_met, grand_total))
        return 0, lines

    first_fail = next((ln for ln in lines if ln.startswith("FAIL")), "unknown")
    lines.append("ACCEPTANCE: FAIL ({}/{} expectations met) — first unmet: {}".format(
        grand_met, grand_total, first_fail[len("FAIL "):]))
    return 1, lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="End-to-end acceptance for the Asset Renderer + QA Gate: "
                    "TGRERA renders+validates PASS deterministically, and every "
                    "committed fixture reaches its expected verdict on the named check.")
    parser.add_argument("--checked-on", default=DEFAULT_CHECKED_ON,
                        help="verdict date YYYY-MM-DD (default: %(default)s, the sprint baseline)")
    parser.add_argument("--verbose", action="store_true",
                        help="under each row, echo the invoked validate.py stdout "
                             "(the per-check PASS/FAIL lines); the terse row summary is unchanged")
    args = parser.parse_args(argv)

    exit_code, lines = run_gate(args.checked_on, args.verbose)
    for ln in lines:
        print(ln)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
