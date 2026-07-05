#!/usr/bin/env python3
"""Deterministic schedule-slot function for the publish toolchain.

Sprint 003 (spec s5.1 B-P6 / A-4; contract s3.2). Assigns a content asset's
per-channel posting **slot** purely from the operator-supplied ``--week`` and
fixed documented constants — **never** the wall clock. Posting times are still an
open A/B hypothesis (``PLAN.md`` Loop 5), so the slot encodes a deterministic
morning/evening A/B *bucket* (which alternates by week so the weeks-1..8 A/B data
the Gap-3 scorecard reads is populated), not a real posting time. Real times are
filled by the human via ``mark_posted.py``.

Slot string format: ``<week>/<bucket>/<HH:MM>``.

Pure library. Never reads the wall clock (no current-time call of any kind), no
network, no writes, no CLI side effects on import. Stdlib only.
"""

import re
import sys
from pathlib import Path

# Import the shared Sprint-001 map from beside this file (runs from any cwd) so
# the canonical channel order is DERIVED, never a forked literal (probe #12).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import utm  # noqa: E402

# Canonical channel order, derived from the shared map: instagram, youtube,
# linkedin. The channel *ordinal* used below is this tuple's index — no fork.
CANONICAL_CHANNELS = tuple(utm.CHANNEL_SOURCE_MAP.keys())

_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")

# A/B bucket names.
BUCKET_MORNING = "morning"
BUCKET_EVENING = "evening"

# Per-channel default times — arbitrary A/B-hypothesis defaults, NOT real posting
# times (A-4). This morning/evening table is the one new declaration this module
# authors; it is local A/B data, not a channel-map fork. (contract s3.2 table)
_TIMES = {
    "instagram": {BUCKET_MORNING: "09:00", BUCKET_EVENING: "18:00"},
    "youtube":   {BUCKET_MORNING: "11:00", BUCKET_EVENING: "20:00"},
    "linkedin":  {BUCKET_MORNING: "08:30", BUCKET_EVENING: "17:30"},
}


def _week_number(week):
    """Return the integer WW from a validated ``YYYY-Www`` string."""
    return int(week.split("-W", 1)[1])


def bucket_for(week, channel):
    """Return the A/B bucket ('morning'|'evening') for (week, channel). Pure.

    ``bucket = morning if (WW + ordinal) % 2 == 0 else evening`` where ``ordinal``
    is the channel's index in the canonical order (contract s3.2).
    """
    ww = _week_number(week)
    ordinal = CANONICAL_CHANNELS.index(channel)
    return BUCKET_MORNING if (ww + ordinal) % 2 == 0 else BUCKET_EVENING


def slot_for(week, channel):
    """Return the deterministic slot string ``<week>/<bucket>/<HH:MM>``. Pure.

    Raises ``ValueError`` on a malformed ``week`` (not ``^\\d{4}-W\\d{2}$``) or an
    unknown ``channel`` (the CLI turns these into exit 2). No wall-clock.
    """
    if not isinstance(week, str) or not _WEEK_RE.match(week):
        raise ValueError(
            "week must be ISO 'YYYY-Www' (e.g. 2026-W27); got {!r}".format(week))
    if channel not in CANONICAL_CHANNELS:
        raise ValueError(
            "unknown channel {!r} (expected one of {})".format(
                channel, list(CANONICAL_CHANNELS)))
    bucket = bucket_for(week, channel)
    return "{}/{}/{}".format(week, bucket, _TIMES[channel][bucket])
