#!/usr/bin/env python3
"""Shared UTM module for the TERREM marketing-loop toolchains.

Sprint 001 (spec s5.0, B-U1..B-U4). This is the *foundation seam* that BOTH the
Gap 2 publish toolchain and the Gap 3 analytics toolchain import — the single
source of truth for the channel<->utm_source map and for what makes a Flywheel
link scheme-valid. There must never be a second copy of the channel map.

Documented UTM scheme (spec B-U2):
    utm_source=<channel>&utm_medium=social&utm_campaign=<slug>
A link is valid iff:
    * a ``Flywheel target:`` line exists and its URL has a parseable query;
    * ``utm_medium == "social"`` exactly;
    * ``utm_campaign`` equals the folder slug with a leading ``YYYY-MM-DD-``
      date prefix removed (A-1);
    * ``utm_source`` is one of the CHANNEL_SOURCE_MAP values (B-U3).

Pure library. No CLI side effects on import, never reads the wall clock, no
network, no file writes beyond what a caller passes in. ``urllib.parse`` is used
for query-string parsing ONLY (never to fetch). Stdlib only.
"""

import re
from pathlib import Path
from urllib.parse import urlparse, parse_qsl

# --- Canonical channel <-> utm_source map (spec B-U3) --------------------------
# The single source of truth. The allowed-source SET is derived from the values
# below (see ALLOWED_SOURCES) — do NOT hand-maintain a second copy.
CHANNEL_SOURCE_MAP = {
    "instagram": "instagram",
    "youtube": "youtube",   # "YouTube community" maps to utm_source=youtube (A-2)
    "linkedin": "linkedin",
}

# Allowed utm_source values, derived (never a second literal list).
ALLOWED_SOURCES = frozenset(CHANNEL_SOURCE_MAP.values())

# Violation codes — the Evaluator asserts on these EXACT strings (contract s3.3).
CODE_MISSING_LINE = "missing-flywheel-line"
CODE_MALFORMED_QUERY = "malformed-query"
CODE_WRONG_MEDIUM = "wrong-medium"
CODE_CAMPAIGN_MISMATCH = "campaign-mismatch"
CODE_UNKNOWN_SOURCE = "unknown-source"

# Fixed evaluation order for the independent value checks (contract s3.3).
_VALUE_CHECK_ORDER = (CODE_WRONG_MEDIUM, CODE_CAMPAIGN_MISMATCH, CODE_UNKNOWN_SOURCE)

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_FLYWHEEL_RE = re.compile(r"Flywheel target:\s*(?P<rest>.*)$")


def campaign_from_slug(folder_name):
    """Return the utm_campaign a folder slug should carry (B-U2 / A-1).

    Strips a leading ``YYYY-MM-DD-`` date prefix; returns the name unchanged if
    there is no such prefix. Accepts a str or a Path (uses its final name).
    """
    name = Path(folder_name).name if isinstance(folder_name, Path) else str(folder_name)
    return _DATE_PREFIX_RE.sub("", name, count=1)


def parse_flywheel_line(meta_text):
    """Parse the ``Flywheel target:`` line of a meta.md text (B-U1).

    Returns ``None`` distinctly when no ``Flywheel target:`` line exists at all.
    Otherwise returns a dict:
        {
          "url": <str>,            # the primary URL token on the line
          "query_parsed": <bool>,  # True iff the URL has a parseable query
          "utm_source":   <str|None>,
          "utm_medium":   <str|None>,
          "utm_campaign": <str|None>,
        }
    Only the PRIMARY URL on the ``Flywheel target:`` line is parsed; any human
    ``(per-channel: ...)`` continuation line below it is ignored (contract s3.2).
    """
    line = None
    for raw in meta_text.splitlines():
        m = _FLYWHEEL_RE.search(raw)
        if m:
            line = m.group("rest").strip()
            break
    if line is None:
        return None

    # First whitespace-delimited token after the label is the primary URL.
    url = line.split()[0] if line.split() else ""
    query = urlparse(url).query
    pairs = parse_qsl(query, keep_blank_values=True)
    query_parsed = bool(pairs)
    params = dict(pairs)
    return {
        "url": url,
        "query_parsed": query_parsed,
        "utm_source": params.get("utm_source"),
        "utm_medium": params.get("utm_medium"),
        "utm_campaign": params.get("utm_campaign"),
    }


def _violation(code, message):
    return {"code": code, "message": message}


def validate_flywheel(parsed, expected_campaign):
    """Validate a parsed flywheel dict (or None) against the scheme (B-U2).

    Returns an ordered list of violation dicts (empty == valid). Pure function.
    ``parsed`` is the output of :func:`parse_flywheel_line`; ``expected_campaign``
    is :func:`campaign_from_slug` of the asset folder.
    """
    if parsed is None:
        return [_violation(
            CODE_MISSING_LINE,
            "no 'Flywheel target:' line found in meta.md",
        )]
    if not parsed["query_parsed"]:
        return [_violation(
            CODE_MALFORMED_QUERY,
            "'Flywheel target:' URL {!r} has no parseable query string "
            "(expected ?utm_source=...&utm_medium=social&utm_campaign=...)".format(
                parsed["url"]),
        )]

    # Query parsed: evaluate the three value checks INDEPENDENTLY, fixed order.
    found = {}
    medium = parsed["utm_medium"]
    if medium != "social":
        shown = "absent" if medium is None else repr(medium)
        found[CODE_WRONG_MEDIUM] = _violation(
            CODE_WRONG_MEDIUM,
            "utm_medium was {}, expected 'social'".format(shown),
        )
    campaign = parsed["utm_campaign"]
    if campaign != expected_campaign:
        shown = "absent" if campaign is None else repr(campaign)
        found[CODE_CAMPAIGN_MISMATCH] = _violation(
            CODE_CAMPAIGN_MISMATCH,
            "utm_campaign was {}, expected {!r} (date-stripped folder slug)".format(
                shown, expected_campaign),
        )
    source = parsed["utm_source"]
    if source not in ALLOWED_SOURCES:
        shown = "absent" if source is None else repr(source)
        found[CODE_UNKNOWN_SOURCE] = _violation(
            CODE_UNKNOWN_SOURCE,
            "utm_source was {}, expected one of {}".format(
                shown, sorted(ALLOWED_SOURCES)),
        )
    return [found[c] for c in _VALUE_CHECK_ORDER if c in found]


def validate_asset(asset_dir):
    """Validate one asset folder's Flywheel UTM link (B-U2 / B-U4).

    ``asset_dir`` is a path to a ``content/<slug>/`` style folder containing a
    ``meta.md``. Returns a structured result dict:
        {"slug": <str>, "ok": <bool>, "violations": [ {code, message}, ... ]}
    Pure function: no writes, no wall-clock, no network. Raises
    ``FileNotFoundError`` if the folder has no ``meta.md`` (a precondition the
    CLI translates into exit code 2).
    """
    asset_dir = Path(asset_dir)
    slug = asset_dir.name
    meta_path = asset_dir / "meta.md"
    if not meta_path.is_file():
        raise FileNotFoundError("no meta.md in {}".format(asset_dir))
    meta_text = meta_path.read_text(encoding="utf-8")
    parsed = parse_flywheel_line(meta_text)
    expected_campaign = campaign_from_slug(slug)
    violations = validate_flywheel(parsed, expected_campaign)
    return {"slug": slug, "ok": not violations, "violations": violations}
