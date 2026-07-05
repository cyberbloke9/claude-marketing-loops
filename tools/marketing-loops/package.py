#!/usr/bin/env python3
"""Publish PACKAGE generation CLI for the TERREM marketing-loop toolchain.

Sprint 003 (spec s5.1 B-P4/B-P5/B-P6/B-P9; contract s3.3). On a gate-passing
asset, writes one per-channel PACKAGE JSON (final caption = authored body + the
correct per-channel UTM link; ordered attachment PNG paths from ``manifest.json``;
the deterministic schedule slot) and updates the Sprint-002 QUEUE rows in place
with ``schedule_slot`` + ``package_path``. It **re-runs the frozen Sprint-002
gate** and never bypasses it.

Usage:
    python3 package.py <asset_dir> --week YYYY-Www [--queue PATH] [--publish-dir DIR]

Exit codes (contract s3.6):
    0  success — packages written + queue updated (idempotent re-run also 0).
    1  domain failure — the gate refused the asset; reasons on stderr, no write.
    2  usage / precondition error — bad --week; missing asset/meta.md/manifest/
       captions body; invalid Flywheel UTM; unmapped/zero channels; empty
       surfaces. Message on stderr, no write, empty stdout.

Atomicity: ALL validation happens before ANY write. On any error, zero package
files are written and the queue is untouched.

Never reads the wall clock, no network. ``urllib.parse`` is used only to
parse/rebuild query strings, never to fetch. Stdlib only.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import gate      # noqa: E402
import channels  # noqa: E402
import queue     # noqa: E402  (our QUEUE module, resolved from _HERE)
import utm       # noqa: E402
import captions  # noqa: E402
import schedule  # noqa: E402

# Repo root: tools/marketing-loops/package.py -> parent(marketing-loops) ->
# parent(tools) -> parent(repo root).
_REPO_ROOT = _HERE.parent.parent

_DEFAULT_QUEUE = "content/publish-queue.json"
_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")

PACKAGE_SCHEMA_VERSION = "1"


class UsageError(Exception):
    """Raised for exit-code-2 conditions (precondition / usage)."""


def _repo_relative(path):
    """Return ``path`` as a POSIX repo-relative string when under the repo root,
    else its absolute resolved POSIX path. cwd-independent (repo root from
    ``__file__``)."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_asset(asset_dir):
    p = Path(asset_dir)
    if not p.exists():
        raise UsageError("asset folder does not exist: {}".format(asset_dir))
    if not p.is_dir():
        raise UsageError("asset path is not a directory: {}".format(asset_dir))
    if not (p / "meta.md").is_file():
        raise UsageError("no meta.md in asset folder: {}".format(asset_dir))
    return p


def _attachments(asset_dir):
    """Read manifest.json and return ordered repo-relative attachment PNG paths.

    Raises UsageError (exit 2) if the manifest is absent, unparseable, or has an
    empty/absent ``surfaces`` list.
    """
    manifest_path = Path(asset_dir) / "render" / "manifest.json"
    if not manifest_path.is_file():
        raise UsageError("manifest.json not found at {}".format(manifest_path))
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise UsageError(
            "manifest.json at {} is not valid JSON: {}".format(manifest_path, exc))
    surfaces = data.get("surfaces") if isinstance(data, dict) else None
    if not isinstance(surfaces, list) or not surfaces:
        raise UsageError(
            "manifest.json at {} has an empty or absent 'surfaces' list; a "
            "package with nothing to attach is not valid".format(manifest_path))
    render_dir = Path(asset_dir) / "render"
    attachments = []
    for i, surf in enumerate(surfaces):
        png = surf.get("png") if isinstance(surf, dict) else None
        if not png:
            raise UsageError(
                "manifest.json at {} surface #{} has no 'png' field".format(
                    manifest_path, i))
        attachments.append(_repo_relative(render_dir / png))
    return attachments


def _per_channel_link(flywheel_url, channel, campaign):
    """Canonically rebuild the per-channel UTM link on the flywheel destination.

    Uses scheme://host<path> from the validated flywheel URL and rebuilds the
    query in canonical order, so the link is byte-identical regardless of the
    base link's original param order (contract s3.3 step 7).
    """
    parts = urlparse(flywheel_url)
    base = "{}://{}{}".format(parts.scheme, parts.netloc, parts.path)
    src = utm.CHANNEL_SOURCE_MAP[channel]
    return ("{}?utm_source={}&utm_medium=social&utm_campaign={}".format(
        base, src, campaign))


def _build_package(slug, channel, utm_link, caption, attachments, slot, week):
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "slug": slug,
        "channel": channel,
        "utm_source": utm.CHANNEL_SOURCE_MAP[channel],
        "utm_link": utm_link,
        "caption": caption,
        "attachments": list(attachments),
        "schedule_slot": slot,
        "week": week,
    }


def _dump_package(package):
    return json.dumps(package, sort_keys=True, indent=2) + "\n"


def merge_package_rows(q, incoming_rows):
    """Merge freshly-built package rows into the queue with PACKAGE semantics.

    Distinct from ``queue.merge_rows`` (which leaves an existing queued row
    untouched). Here (contract s3.3 step 9):
        * new (slug, channel) pair      -> append the fresh row;
        * existing ``queued`` row       -> replace its ``schedule_slot`` /
          ``package_path`` / ``week`` with the freshly-computed values, keeping
          ``state="queued"`` and its (null) posted fields;
        * existing ``posted`` row       -> keep wholesale (never regress state or
          clear posted fields). Callers do not pass a posted channel's row here
          (they skip it), so this is a defensive no-regress guard.

    Pure: the input ``q`` is not mutated; a new document is returned.
    """
    by_key = {(r["slug"], r["channel"]): dict(r) for r in q["rows"]}
    for row in incoming_rows:
        key = (row["slug"], row["channel"])
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = dict(row)
        elif existing.get("state") == queue.STATE_POSTED:
            continue  # no-regress: keep the posted row wholesale
        else:
            merged = dict(existing)
            merged["schedule_slot"] = row["schedule_slot"]
            merged["package_path"] = row["package_path"]
            merged["week"] = row["week"]
            merged["state"] = queue.STATE_QUEUED
            by_key[key] = merged
    return {
        "schema_version": q.get("schema_version", queue.SCHEMA_VERSION),
        "rows": queue.sort_rows(by_key.values()),
    }


def run(asset_dir, week, queue_path, publish_dir):
    """Execute the package flow. Returns (exit_code, stdout_lines, stderr_lines).

    All validation precedes the writes. On exit 1/2 nothing is written and both
    stdout and the returned stdout_lines are empty.
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
    slug = asset.name

    # (1) gate first — never bypass (B-P9). Re-uses the frozen Sprint-002 gate.
    result = gate.gate_asset(asset)
    if not result["ok"]:
        stderr.append("REFUSED {}: asset failed the publish gate".format(result["slug"]))
        for reason in result["reasons"]:
            stderr.append("  [{}] {}".format(reason["code"], reason["message"]))
        return 1, stdout, stderr

    # (2) channels.
    meta_text = (asset / "meta.md").read_text(encoding="utf-8")
    chans, unmapped, had_line = channels.channels_for_asset(meta_text)
    if not had_line:
        stderr.append("ERROR: {}: meta.md has no 'Channels:' line".format(slug))
        return 2, stdout, stderr
    if unmapped:
        stderr.append(
            "ERROR: {}: 'Channels:' line has unmapped platform token(s): {} "
            "— add an alias or remove it (never silently guessed)".format(
                slug, ", ".join(repr(t) for t in unmapped)))
        return 2, stdout, stderr
    if not chans:
        stderr.append(
            "ERROR: {}: 'Channels:' line names no known channel "
            "(expected any of IG/Instagram, YT/YouTube, LinkedIn)".format(slug))
        return 2, stdout, stderr

    # (2) UTM precondition — parse the Flywheel line (the only source of the
    # destination base URL) and refuse a wrong-UTM asset before it ships.
    utm_result = utm.validate_asset(asset)
    if not utm_result["ok"]:
        codes = [v["code"] for v in utm_result["violations"]]
        stderr.append(
            "ERROR: {}: Flywheel UTM invalid {} — a wrong-UTM asset never "
            "ships".format(slug, codes))
        for v in utm_result["violations"]:
            stderr.append("  [{}] {}".format(v["code"], v["message"]))
        return 2, stdout, stderr
    flywheel = utm.parse_flywheel_line(meta_text)
    campaign = utm.campaign_from_slug(slug)

    # (2) manifest / attachments.
    try:
        attachments = _attachments(asset)
    except UsageError as exc:
        stderr.append("ERROR: {}".format(exc))
        return 2, stdout, stderr

    # (2) Determine which channels are already posted (skip) vs to-be-packaged.
    # A channel already `posted` in the queue is kept as-is and does NOT require
    # a caption body (contract s3.3 step 8 "see step 9 for posted-skip").
    try:
        q = queue.load_queue(queue_path)
    except ValueError as exc:
        stderr.append("ERROR: {}".format(exc))
        return 2, stdout, stderr
    posted_pairs = {
        (r["slug"], r["channel"])
        for r in q["rows"] if r.get("state") == queue.STATE_POSTED
    }
    to_package = [c for c in chans if (slug, c) not in posted_pairs]

    # (2) caption bodies — required ONLY for the to-be-packaged channels. If every
    # channel is already posted there is nothing to package, so captions.md is not
    # consulted (a re-package of a fully-posted asset stays all kept-posted).
    blocks = {}
    if to_package:
        try:
            blocks = captions.load_captions(asset / "captions.md")
        except FileNotFoundError:
            stderr.append(
                "ERROR: {}: no captions.md — add one with a caption:all block (or "
                "a caption:<channel> block per channel); the tool never invents "
                "caption copy".format(slug))
            return 2, stdout, stderr
        except ValueError as exc:
            stderr.append("ERROR: {}: captions.md is malformed: {}".format(slug, exc))
            return 2, stdout, stderr
        missing = [c for c in to_package if captions.body_for(blocks, c) is None]
        if missing:
            stderr.append(
                "ERROR: {}: no caption body for channel(s) {} — add a "
                "caption:<channel> block or a caption:all block to captions.md; the "
                "tool never invents caption copy".format(
                    slug, ", ".join(repr(c) for c in missing)))
            return 2, stdout, stderr

    # --- All validation passed. Build everything, THEN write (atomic). ---------
    publish_path = Path(publish_dir)
    incoming_rows = []
    package_writes = []  # (package_file_path, serialized_bytes)
    for c in chans:
        if (slug, c) in posted_pairs:
            continue  # kept-posted; emitted below, no build/write
        utm_link = _per_channel_link(flywheel["url"], c, campaign)
        body = captions.body_for(blocks, c)
        caption = "{}\n\n{}".format(body, utm_link)
        slot = schedule.slot_for(week, c)
        pkg = _build_package(slug, c, utm_link, caption, attachments, slot, week)
        pkg_file = publish_path / "{}.json".format(c)
        row = queue.new_row(slug, c, week)
        row["schedule_slot"] = slot
        row["package_path"] = _repo_relative(pkg_file)
        incoming_rows.append(row)
        package_writes.append((pkg_file, _dump_package(pkg)))

    # Writes (the only side effects): publish dir, package files, then queue.
    publish_path.mkdir(parents=True, exist_ok=True)
    for pkg_file, blob in package_writes:
        pkg_file.write_text(blob, encoding="utf-8")
    merged = merge_package_rows(q, incoming_rows)
    queue.write_queue(queue_path, merged)

    # Stdout in canonical channel order: packaged vs kept-posted.
    for c in chans:
        if (slug, c) in posted_pairs:
            stdout.append("kept-posted {} {}".format(slug, c))
        else:
            stdout.append("packaged {} {}".format(slug, c))
    return 0, stdout, stderr


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate per-channel publish packages + update the QUEUE "
                    "for a gate-passing content asset (spec s5.1 B-P4..B-P6).")
    parser.add_argument("asset_dir", help="path to a content/<slug>/ asset folder")
    parser.add_argument("--week", required=True,
                        help="ISO week the asset is scheduled for (YYYY-Www)")
    parser.add_argument("--queue", default=_DEFAULT_QUEUE,
                        help="publish-queue JSON path (default: {})".format(_DEFAULT_QUEUE))
    parser.add_argument("--publish-dir", default=None,
                        help="dir for per-channel PACKAGE files "
                             "(default: <asset_dir>/publish)")
    args = parser.parse_args(argv)

    publish_dir = args.publish_dir
    if publish_dir is None:
        publish_dir = str(Path(args.asset_dir) / "publish")

    code, stdout_lines, stderr_lines = run(
        args.asset_dir, args.week, args.queue, publish_dir)
    for line in stdout_lines:
        sys.stdout.write(line + "\n")
    for line in stderr_lines:
        sys.stderr.write(line + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
