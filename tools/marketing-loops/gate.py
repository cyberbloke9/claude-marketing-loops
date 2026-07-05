#!/usr/bin/env python3
"""Publish gate for the TERREM marketing-loop publish toolchain.

Sprint 002 (spec s5.1 B-P1/B-P2; contract s3.1). This is the *single* decision
point that says whether one content asset folder may be queued for publishing.
Sprint 003's package-generation and the ``/loop-publish`` skill re-run this exact
function (B-P9 "never bypasses the gate") — one function to import, not logic to
duplicate.

The four refusal conditions (B-P1/B-P2), each with an EXACT cited reason code the
Evaluator asserts on:

    missing-verdict          render/qa-verdict.json absent, unparseable, or
                             missing the verdict/failed_checks keys.
    verdict-not-pass         verdict field is not exactly "PASS".
    failed-checks-nonempty   verdict == "PASS" but failed_checks is non-empty
                             (the second half of a FAIL-free PASS).
    killed                   meta.md contains a KILLED marker.

Terminal vs independent structure (mirrors Sprint 001's UTM taxonomy):
    * missing-verdict is TERMINAL for the verdict branch — if it fires, neither
      verdict-not-pass nor failed-checks-nonempty is additionally emitted (there
      is no trustworthy data to check them against).
    * When the verdict parses, verdict-not-pass and failed-checks-nonempty are
      evaluated INDEPENDENTLY.
    * killed is ALWAYS evaluated independently off meta.md, regardless of verdict.
    * Codes are emitted in the fixed order:
        missing-verdict, verdict-not-pass, failed-checks-nonempty, killed.

Pure library. No writes, no wall-clock, no network, no CLI side effects on
import. Stdlib only. The gate does NOT check UTM validity — that is the Sprint
001 verifier's job (B-U4 / B-A11), not one of the four B-P1 conditions.
"""

import json
import re
from pathlib import Path

# --- Reason codes — the Evaluator asserts on these EXACT strings (contract s3.1)
CODE_MISSING_VERDICT = "missing-verdict"
CODE_VERDICT_NOT_PASS = "verdict-not-pass"
CODE_FAILED_CHECKS_NONEMPTY = "failed-checks-nonempty"
CODE_KILLED = "killed"

# The exact PASS string required (case-sensitive, spec B-P1).
_PASS = "PASS"

# KILLED marker (B-P2): a meta.md line whose QA: field begins with KILLED. Match
# is case-sensitive on KILLED, tolerates 0-2 leading asterisks (real form is
# ``QA: **KILLED 2026-07-03** — ...``). Must NOT match ``QA: PASS`` nor lowercase
# prose such as ``killed assets are data``.
_KILLED_RE = re.compile(r"QA:\s*\*{0,2}KILLED")


def _reason(code, message):
    return {"code": code, "message": message}


def _killed_line(meta_text):
    """Return the stripped meta.md line that trips the KILLED marker, or None."""
    for raw in meta_text.splitlines():
        if _KILLED_RE.search(raw):
            return raw.strip()
    return None


def _verdict_reasons(verdict_path):
    """Evaluate the verdict branch. Returns an ordered list of reason dicts.

    missing-verdict is terminal for this branch: if the file is absent,
    unparseable, or missing keys, only missing-verdict is returned.
    """
    if not verdict_path.is_file():
        return [_reason(
            CODE_MISSING_VERDICT,
            "qa-verdict.json not found at {}".format(verdict_path),
        )]
    try:
        raw = verdict_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError) as exc:
        return [_reason(
            CODE_MISSING_VERDICT,
            "qa-verdict.json at {} is not valid JSON: {}".format(verdict_path, exc),
        )]
    if not isinstance(data, dict) or "verdict" not in data or "failed_checks" not in data:
        return [_reason(
            CODE_MISSING_VERDICT,
            "qa-verdict.json at {} is missing required key(s): "
            "expected both 'verdict' and 'failed_checks'".format(verdict_path),
        )]

    reasons = []
    verdict = data["verdict"]
    if verdict != _PASS:
        shown = "absent" if verdict is None else repr(verdict)
        reasons.append(_reason(
            CODE_VERDICT_NOT_PASS,
            "verdict was {}, expected 'PASS'".format(shown),
        ))
    failed = data["failed_checks"]
    if failed:
        count = len(failed) if isinstance(failed, (list, tuple)) else "some"
        reasons.append(_reason(
            CODE_FAILED_CHECKS_NONEMPTY,
            "failed_checks is non-empty ({} failed check(s)); a FAIL-free PASS "
            "is required".format(count),
        ))
    return reasons


def gate_asset(asset_dir):
    """Decide whether one asset folder may be queued (B-P1/B-P2). Pure.

    ``asset_dir`` points at a ``content/<slug>/`` style folder with a ``meta.md``
    and (normally) a ``render/qa-verdict.json``. Returns:

        {"slug": <str>, "ok": <bool>, "reasons": [ {code, message}, ... ]}

    ``ok`` is True iff ``reasons`` is empty. Raises ``FileNotFoundError`` if the
    folder has no ``meta.md`` (a precondition the CLI translates into exit 2,
    distinct from a domain refusal). No writes, no wall-clock, no network.
    """
    asset_dir = Path(asset_dir)
    slug = asset_dir.name
    meta_path = asset_dir / "meta.md"
    if not meta_path.is_file():
        raise FileNotFoundError("no meta.md in {}".format(asset_dir))
    meta_text = meta_path.read_text(encoding="utf-8")

    reasons = []
    # Fixed emission order: verdict branch first (terminal internally), then the
    # independent killed check.
    reasons.extend(_verdict_reasons(asset_dir / "render" / "qa-verdict.json"))

    killed_line = _killed_line(meta_text)
    if killed_line is not None:
        reasons.append(_reason(
            CODE_KILLED,
            "meta.md contains a KILLED marker (line: {!r})".format(killed_line),
        ))

    return {"slug": slug, "ok": not reasons, "reasons": reasons}
