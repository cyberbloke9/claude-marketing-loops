#!/usr/bin/env python3
"""Asset resolver + join key for the Gap-3 analytics toolchain.

Sprint 004 (spec s5.2 B-A2/B-A11; contract s3.3). Scans a content directory of
``<slug>/meta.md`` asset folders and builds the ``campaign -> asset-record`` map
that CSV metrics rows join on. The join key and per-asset UTM validity come
SOLELY from the frozen Sprint-001 ``utm`` module (``campaign_from_slug``,
``validate_asset``) — there is no forked channel map and no re-declared
date-stripping regex here.

Asset record shape (contract s3.3):
    {
      "slug": "<folder name, date prefix intact>",
      "campaign": "<utm.campaign_from_slug(slug)>",   # the join key (B-A2)
      "hook_number": <int|null>,                       # first #<n> on Hook: line
      "utm_valid": <bool>,                             # utm.validate_asset().ok
      "utm_violations": [<code>, ...],                 # Sprint-001 violation codes
    }

Pure library: no writes, no wall clock, no network, no CLI side effects on
import. Stdlib only (``re``, ``pathlib``).
"""

import re
import sys
from pathlib import Path

# Import the frozen Sprint-001 module from beside this file (runs from any cwd).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import utm  # noqa: E402

_HOOK_LINE_RE = re.compile(r"^\s*Hook:\s*(?P<rest>.*)$")
_HOOK_NUM_RE = re.compile(r"#(\d+)")


def hook_number_from_meta(meta_text):
    """Return the first ``#<n>`` on the ``Hook:`` line, or ``None`` (contract s3.3).

    ``Hook: hook-bank #11 adapted ...`` -> ``11``; ``... #13 ... #21`` -> ``13``.
    No ``Hook:`` line, or no ``#<n>`` on it -> ``None`` (never invents a number).
    """
    for raw in meta_text.splitlines():
        m = _HOOK_LINE_RE.match(raw)
        if m:
            num = _HOOK_NUM_RE.search(m.group("rest"))
            return int(num.group(1)) if num else None
    return None


def _asset_record(asset_dir):
    slug = asset_dir.name
    meta_text = (asset_dir / "meta.md").read_text(encoding="utf-8")
    result = utm.validate_asset(asset_dir)  # frozen Sprint-001 validity (B-A11)
    return {
        "slug": slug,
        "campaign": utm.campaign_from_slug(slug),  # the join key (B-A2)
        "hook_number": hook_number_from_meta(meta_text),
        "utm_valid": result["ok"],
        "utm_violations": [v["code"] for v in result["violations"]],
    }


def build_asset_map(content_dir):
    """Return ``{campaign: asset_record}`` for every ``meta.md``-bearing subdir.

    Skips the ``TEMPLATE.md`` file and any subdir lacking a ``meta.md`` (not an
    error). Two assets whose slugs map to the SAME campaign raise ``ValueError``
    (an authoring collision the operator must fix — surfaced, never silently
    coalesced). Pure: no writes, no wall clock, no network.
    """
    content_dir = Path(content_dir)
    result = {}
    origins = {}
    for child in sorted(content_dir.iterdir(), key=lambda c: c.name):
        if not child.is_dir():
            continue
        if not (child / "meta.md").is_file():
            continue
        record = _asset_record(child)
        campaign = record["campaign"]
        if campaign in result:
            raise ValueError(
                "campaign collision: {!r} maps to both {!r} and {!r}".format(
                    campaign, origins[campaign], record["slug"]))
        result[campaign] = record
        origins[campaign] = record["slug"]
    return result
