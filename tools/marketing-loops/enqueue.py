#!/usr/bin/env python3
"""Enqueue CLI for the TERREM marketing-loop publish toolchain.

Sprint 002 (spec s5.1 B-P1/B-P2/B-P3; contract s3.3). A thin CLI over the
importable ``gate``, ``queue`` and ``channels`` modules plus the Sprint-001
``utm`` channel map. It runs the gate, refuses on failure with cited reasons and
NO write, and on a passing asset appends/updates one ``queued`` row per declared
channel — idempotently and without regressing a pre-existing ``posted`` row.

Usage:
    python3 enqueue.py <asset_dir> --week YYYY-Www [--queue PATH]

Exit codes (matching tools/marketing-render/validate.py + Sprint 001):
    0  success — gate passed and enqueue completed (idempotent re-run also 0).
    1  domain failure — the gate refused the asset; reasons cited on stderr,
       no queue write.
    2  usage / precondition error — asset_dir missing or has no meta.md;
       --week missing or malformed; Channels: line yields an unmapped platform
       token or zero channels. Message on stderr, no queue write, empty stdout.

Order of checks (contract s3.3 "gate first"):
    week format (2) -> asset precondition (2) -> gate (1 on refusal) ->
    channels (2) -> load/merge/write queue (0).

Never reads the wall clock, no network. Stdlib only.
"""

import argparse
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import gate      # noqa: E402
import channels  # noqa: E402
import queue     # noqa: E402  (our QUEUE module, resolved from _HERE)

_DEFAULT_QUEUE = "content/publish-queue.json"
_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")


class UsageError(Exception):
    """Raised for exit-code-2 conditions (precondition / usage)."""


def _resolve_asset(asset_dir):
    """Return the asset Path, or raise UsageError (exit 2) if unusable."""
    p = Path(asset_dir)
    if not p.exists():
        raise UsageError("asset folder does not exist: {}".format(asset_dir))
    if not p.is_dir():
        raise UsageError("asset path is not a directory: {}".format(asset_dir))
    if not (p / "meta.md").is_file():
        raise UsageError("no meta.md in asset folder: {}".format(asset_dir))
    return p


def run(asset_dir, week, queue_path):
    """Execute the enqueue flow. Returns (exit_code, stdout_lines, stderr_lines).

    Pure w.r.t. stdout/stderr (returns them) so tests can assert; the only
    side effect is the queue write on the success path.
    """
    stdout, stderr = [], []

    # (2) --week format.
    if not week or not _WEEK_RE.match(week):
        stderr.append("ERROR: --week must be ISO week 'YYYY-Www' (e.g. 2026-W27); "
                      "got {!r}".format(week))
        return 2, stdout, stderr

    # (2) asset precondition.
    try:
        asset = _resolve_asset(asset_dir)
    except UsageError as exc:
        stderr.append("ERROR: {}".format(exc))
        return 2, stdout, stderr

    # (1) gate first.
    result = gate.gate_asset(asset)
    if not result["ok"]:
        stderr.append("REFUSED {}: asset failed the publish gate".format(result["slug"]))
        for reason in result["reasons"]:
            stderr.append("  [{}] {}".format(reason["code"], reason["message"]))
        return 1, stdout, stderr

    # (2) channel parsing (only reached on a gate-passed asset).
    meta_text = (asset / "meta.md").read_text(encoding="utf-8")
    chans, unmapped, had_line = channels.channels_for_asset(meta_text)
    if not had_line:
        stderr.append("ERROR: {}: meta.md has no 'Channels:' line".format(asset.name))
        return 2, stdout, stderr
    if unmapped:
        stderr.append(
            "ERROR: {}: 'Channels:' line has unmapped platform token(s): {} "
            "— add an alias or remove it (never silently guessed)".format(
                asset.name, ", ".join(repr(t) for t in unmapped)))
        return 2, stdout, stderr
    if not chans:
        stderr.append(
            "ERROR: {}: 'Channels:' line names no known channel "
            "(expected any of IG/Instagram, YT/YouTube, LinkedIn)".format(asset.name))
        return 2, stdout, stderr

    # (0) load -> merge -> write.
    try:
        q = queue.load_queue(queue_path)
    except ValueError as exc:
        stderr.append("ERROR: {}".format(exc))
        return 2, stdout, stderr
    incoming = [queue.new_row(asset.name, c, week) for c in chans]
    merged, actions = queue.merge_rows(q, incoming)
    queue.write_queue(queue_path, merged)
    for action, slug, channel in actions:
        stdout.append("{} {} {}".format(action, slug, channel))
    return 0, stdout, stderr


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Gate + enqueue one content asset into the publish queue "
                    "(spec s5.1 B-P1/B-P2/B-P3).")
    parser.add_argument("asset_dir", help="path to a content/<slug>/ asset folder")
    parser.add_argument("--week", required=True,
                        help="ISO week the asset is scheduled for (YYYY-Www)")
    parser.add_argument("--queue", default=_DEFAULT_QUEUE,
                        help="publish-queue JSON path (default: {})".format(_DEFAULT_QUEUE))
    args = parser.parse_args(argv)

    code, stdout_lines, stderr_lines = run(args.asset_dir, args.week, args.queue)
    for line in stdout_lines:
        sys.stdout.write(line + "\n")
    for line in stderr_lines:
        sys.stderr.write(line + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
