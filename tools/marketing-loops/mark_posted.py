#!/usr/bin/env python3
"""Mark-posted CLI for the TERREM marketing-loop publish toolchain.

Sprint 003 (spec s5.1 B-P7; contract s3.4). The human-in-the-loop transition:
after the operator posts an asset on a platform by hand, this records the post by
flipping one ``(slug, channel)`` QUEUE row from ``queued`` -> ``posted`` and
storing the supplied ``--posted-on`` date + ``--permalink`` URL. This is the API
seam (B-P8) filled by a human today; a future live-posting adapter fills the same
two fields.

Usage:
    python3 mark_posted.py <slug> <channel> --posted-on YYYY-MM-DD --permalink URL [--queue PATH]

Exit codes (contract s3.6):
    0  success — row transitioned queued -> posted; queue written.
    1  domain refusal — the row is not currently ``queued`` (already posted);
       no write. This is the no-double-post guard (INTENTIONALLY non-idempotent).
    2  usage / precondition error — unknown channel; malformed/invalid
       --posted-on; empty or non-URL --permalink; missing/invalid queue;
       (slug, channel) row not found. Message on stderr, no write, empty stdout.

Never reads the wall clock. ``datetime.strptime`` parses the SUPPLIED
``--posted-on`` only — it never reads the current time. No network. Stdlib only.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import queue  # noqa: E402

_DEFAULT_QUEUE = "content/publish-queue.json"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def transition(q, slug, channel, posted_on, permalink):
    """Return (new_queue, status) for the queued->posted transition. Pure.

    ``status`` is one of:
        "posted"     — a queued row was found and transitioned (new_queue set);
        "not-found"  — no (slug, channel) row exists (new_queue is None);
        "not-queued" — the row exists but state != 'queued' (new_queue is None).

    The input ``q`` is not mutated; on success a new document is returned.
    """
    rows = q["rows"]
    idx = None
    for i, r in enumerate(rows):
        if r["slug"] == slug and r["channel"] == channel:
            idx = i
            break
    if idx is None:
        return None, "not-found"
    if rows[idx].get("state") != queue.STATE_QUEUED:
        return None, "not-queued"
    new_rows = [dict(r) for r in rows]
    new_rows[idx]["state"] = queue.STATE_POSTED
    new_rows[idx]["posted_date"] = posted_on
    new_rows[idx]["permalink"] = permalink
    new_q = {
        "schema_version": q.get("schema_version", queue.SCHEMA_VERSION),
        "rows": new_rows,
    }
    return new_q, "posted"


def run(slug, channel, posted_on, permalink, queue_path):
    """Execute the mark-posted flow. Returns (exit_code, stdout, stderr)."""
    stdout, stderr = [], []

    # (2) channel.
    if channel not in queue.VALID_CHANNELS:
        stderr.append("ERROR: unknown channel {!r} (expected one of {})".format(
            channel, sorted(queue.VALID_CHANNELS)))
        return 2, stdout, stderr

    # (2) --posted-on: format + real calendar date (parsing a supplied date).
    if not posted_on or not _DATE_RE.match(posted_on):
        stderr.append("ERROR: --posted-on must be 'YYYY-MM-DD'; got {!r}".format(
            posted_on))
        return 2, stdout, stderr
    try:
        datetime.strptime(posted_on, "%Y-%m-%d")
    except ValueError:
        stderr.append("ERROR: --posted-on {!r} is not a real calendar date".format(
            posted_on))
        return 2, stdout, stderr

    # (2) --permalink: non-empty + is a URL.
    link = (permalink or "").strip()
    if not link:
        stderr.append("ERROR: --permalink must be non-empty")
        return 2, stdout, stderr
    if not _URL_RE.match(link):
        stderr.append("ERROR: --permalink must be an http(s):// URL; got {!r}".format(
            permalink))
        return 2, stdout, stderr

    # (2) queue must exist + load.
    qp = Path(queue_path)
    if not qp.exists():
        stderr.append("ERROR: queue file does not exist: {} (nothing to mark "
                      "posted)".format(queue_path))
        return 2, stdout, stderr
    try:
        q = queue.load_queue(qp)
    except ValueError as exc:
        stderr.append("ERROR: {}".format(exc))
        return 2, stdout, stderr

    new_q, status = transition(q, slug, channel, posted_on, link)
    if status == "not-found":
        stderr.append(
            "ERROR: no queue row for ({}, {}) — enqueue/package it first".format(
                slug, channel))
        return 2, stdout, stderr
    if status == "not-queued":
        stderr.append(
            "REFUSED ({}, {}): row is already posted; refusing to re-post "
            "(no double-post)".format(slug, channel))
        return 1, stdout, stderr

    queue.write_queue(qp, new_q)
    stdout.append("posted {} {} {}".format(slug, channel, posted_on))
    return 0, stdout, stderr


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Record a manual post: transition a QUEUE row queued->posted "
                    "(spec s5.1 B-P7).")
    parser.add_argument("slug", help="content folder slug (date prefix intact)")
    parser.add_argument("channel", help="instagram | youtube | linkedin")
    parser.add_argument("--posted-on", required=True,
                        help="date the post went live (YYYY-MM-DD)")
    parser.add_argument("--permalink", required=True,
                        help="the live post's permalink URL (http(s)://...)")
    parser.add_argument("--queue", default=_DEFAULT_QUEUE,
                        help="publish-queue JSON path (default: {})".format(_DEFAULT_QUEUE))
    args = parser.parse_args(argv)

    code, stdout_lines, stderr_lines = run(
        args.slug, args.channel, args.posted_on, args.permalink, args.queue)
    for line in stdout_lines:
        sys.stdout.write(line + "\n")
    for line in stderr_lines:
        sys.stderr.write(line + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
