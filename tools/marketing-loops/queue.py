#!/usr/bin/env python3
"""Publish QUEUE schema + deterministic helpers for the publish toolchain.

Sprint 002 (spec s5.4 QUEUE, B-P8; contract s3.2). Materializes the single
publish-queue document — the source of truth ``/loop-publish`` (Sprint 003) will
consume — and the pure load / merge / serialize helpers that keep it byte-stable.

QUEUE schema (the versioned seam):

    {
      "schema_version": "1",
      "rows": [
        {
          "slug": "<content folder slug>",     # full folder name (date prefix intact)
          "channel": "instagram|youtube|linkedin",
          "state": "queued|posted",            # the API seam (B-P8)
          "week": "YYYY-Www",
          "schedule_slot": null,               # populated by Sprint 003 (B-P6)
          "package_path": null,                # populated by Sprint 003 (B-P4)
          "posted_date": null,                 # filled by a human post (B-P7)
          "permalink": null                    # filled by a human post (B-P7)
        }
      ]
    }

The API seam (B-P8): ``state`` is a fixed enum {queued, posted}; a future
live-posting adapter flips ``state`` and fills ``posted_date``/``permalink``
without reshaping the file. No posting-API field names are invented now.

Row identity is the ``(slug, channel)`` pair (at most one row per pair). Rows are
serialized in ascending ``(slug, channel)`` order with ``sort_keys=True``,
``indent=2`` and a single trailing newline — same inputs => byte-identical file.

Pure library. No wall-clock, no network, no CLI side effects on import. The only
write is via :func:`write_queue`, which a caller invokes explicitly. Stdlib only.
"""

import json
import sys
from pathlib import Path

# Import the shared channel map from beside this file (runs from any cwd) so the
# valid-channel set is never a forked copy.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import utm  # noqa: E402

# The versioned seam. Lives here ONCE (contract s5 "schema version constant lives
# once in queue.py"), exactly like manifest.json / qa-verdict.json.
SCHEMA_VERSION = "1"

# State enum — the API seam (B-P8).
STATE_QUEUED = "queued"
STATE_POSTED = "posted"
STATES = frozenset({STATE_QUEUED, STATE_POSTED})

# Valid channels, derived from the shared Sprint-001 map (no fork).
VALID_CHANNELS = frozenset(utm.CHANNEL_SOURCE_MAP.keys())

# The full set of row keys, so a row is authored in exactly one place.
ROW_KEYS = (
    "slug", "channel", "state", "week",
    "schedule_slot", "package_path", "posted_date", "permalink",
)


def empty_queue():
    """Return a fresh, valid empty queue document."""
    return {"schema_version": SCHEMA_VERSION, "rows": []}


def load_queue(path):
    """Load a queue document from ``path``; a missing file => empty queue.

    Raises ``ValueError`` if the file exists but is not a valid queue document
    (unparseable JSON, or missing ``rows``). Pure w.r.t. the filesystem (read
    only).
    """
    path = Path(path)
    if not path.exists():
        return empty_queue()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError("queue file {} is not valid JSON: {}".format(path, exc))
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError(
            "queue file {} is not a valid QUEUE document (expected an object "
            "with a 'rows' list)".format(path))
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def new_row(slug, channel, week):
    """Build one fresh queued row (all lifecycle fields null)."""
    if channel not in VALID_CHANNELS:
        raise ValueError("unknown channel {!r} (expected one of {})".format(
            channel, sorted(VALID_CHANNELS)))
    return {
        "slug": slug,
        "channel": channel,
        "state": STATE_QUEUED,
        "week": week,
        "schedule_slot": None,
        "package_path": None,
        "posted_date": None,
        "permalink": None,
    }


def _row_key(row):
    return (row["slug"], row["channel"])


def sort_rows(rows):
    """Return rows sorted deterministically by ``(slug, channel)``."""
    return sorted(rows, key=_row_key)


def merge_rows(queue, incoming_rows):
    """Merge ``incoming_rows`` into ``queue`` idempotently (B-P3). Pure.

    Returns ``(merged_queue, actions)`` where ``actions`` is an ordered list of
    ``(action, slug, channel)`` for each incoming row, in ``(slug, channel)``
    order, with ``action`` in {``queued``, ``kept-posted``}:

        * no existing row for the pair            -> append; action "queued"
        * an existing ``queued`` row              -> leave unchanged; "queued"
        * an existing ``posted`` row              -> leave unchanged, do NOT
          regress state or clear posted fields;   action "kept-posted"

    The input ``queue`` is not mutated; a new document is returned.
    """
    by_key = {_row_key(r): dict(r) for r in queue["rows"]}
    actions = []
    for row in incoming_rows:
        key = _row_key(row)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = dict(row)
            actions.append(("queued", row["slug"], row["channel"]))
        elif existing.get("state") == STATE_POSTED:
            # No-regress: keep the posted row and its posted_date/permalink.
            actions.append(("kept-posted", row["slug"], row["channel"]))
        else:
            # Already queued (or any non-posted state): leave as-is, idempotent.
            actions.append(("queued", row["slug"], row["channel"]))
    merged = {
        "schema_version": queue.get("schema_version", SCHEMA_VERSION),
        "rows": sort_rows(by_key.values()),
    }
    actions.sort(key=lambda a: (a[1], a[2]))
    return merged, actions


def dumps(queue):
    """Serialize a queue document deterministically (contract s3.2).

    JSON with ``sort_keys=True``, ``indent=2``, rows in ``(slug, channel)``
    order, and a single trailing newline. Same inputs => byte-identical string.
    """
    doc = {
        "schema_version": queue.get("schema_version", SCHEMA_VERSION),
        "rows": sort_rows(queue["rows"]),
    }
    return json.dumps(doc, sort_keys=True, indent=2) + "\n"


def write_queue(path, queue):
    """Write ``queue`` to ``path`` deterministically. The only write in module."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(queue), encoding="utf-8")
