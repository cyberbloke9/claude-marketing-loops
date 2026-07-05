#!/usr/bin/env python3
"""Caption source parser for the TERREM marketing-loop publish toolchain.

Sprint 003 (spec s5.1 B-P5 / A-3; contract s3.1). Parses an asset's
``content/<slug>/captions.md`` — the *authored* caption source — and resolves a
per-channel caption **body**. The tool NEVER writes marketing prose: when a body
is absent for a channel about to be packaged, the caller (``package.py``) errors
and names the channel; it does not invent copy.

The ``captions.md`` format mirrors the existing ``meta.md``
``<!-- provenance:start -->`` marker convention (codebase DNA). One or more
delimited blocks::

    <!-- caption:all:start -->
    <shared caption body — arbitrary text, preserved verbatim>
    <!-- caption:all:end -->

    <!-- caption:instagram:start -->
    <optional Instagram-specific override body>
    <!-- caption:instagram:end -->

Block key is ``all`` or one of the canonical channels
``{instagram, youtube, linkedin}`` (from ``utm.CHANNEL_SOURCE_MAP``). Any other
key parses harmlessly and is simply never resolved by :func:`body_for` — an
unknown/forward-looking block (e.g. ``caption:twitter``) is not an error.

Pure library. No writes, no wall-clock, no network, no CLI side effects on
import. Stdlib only.
"""

import re
import sys
from pathlib import Path

# Import the shared Sprint-001 map from beside this file (runs from any cwd) so
# the canonical channel set is never a forked copy.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import utm  # noqa: E402

# The block key that applies to every channel.
KEY_ALL = "all"

# A caption marker line: ``<!-- caption:<key>:start -->`` / ``:end``.
_MARKER_RE = re.compile(
    r"^\s*<!--\s*caption:(?P<key>[A-Za-z]+):(?P<pos>start|end)\s*-->\s*$"
)


def _strip_blank_edges(lines):
    """Drop leading/trailing blank (whitespace-only) lines; preserve interior."""
    start = 0
    end = len(lines)
    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return lines[start:end]


def parse_captions(text):
    """Parse all caption blocks in ``captions.md`` text (contract s3.1). Pure.

    Returns ``{block_key: body_str, ...}``. The body is the text strictly between
    a block's ``:start``/``:end`` markers, with leading/trailing blank lines
    stripped and interior text preserved byte-for-byte (no reflow).

    Raises ``ValueError`` when a block is malformed — a ``:start`` with no
    matching ``:end`` (including a nested/re-opened block or an ``:end`` whose
    key differs from the open ``:start``) — or when a block key is duplicated.
    The CLI turns a ``ValueError`` into exit code 2.
    """
    blocks = {}
    open_key = None       # key of the currently open block, or None
    body_lines = []       # accumulated body lines for the open block
    for raw in text.splitlines():
        m = _MARKER_RE.match(raw)
        if m is None:
            if open_key is not None:
                body_lines.append(raw)
            continue
        key = m.group("key")
        pos = m.group("pos")
        if pos == "start":
            if open_key is not None:
                raise ValueError(
                    "caption block 'caption:{}' opened before "
                    "'caption:{}' was closed".format(key, open_key))
            open_key = key
            body_lines = []
        else:  # end
            if open_key is None:
                raise ValueError(
                    "caption 'caption:{}:end' has no matching :start".format(key))
            if key != open_key:
                raise ValueError(
                    "caption 'caption:{}:end' does not match open block "
                    "'caption:{}'".format(key, open_key))
            if open_key in blocks:
                raise ValueError(
                    "duplicate caption block 'caption:{}'".format(open_key))
            blocks[open_key] = "\n".join(_strip_blank_edges(body_lines))
            open_key = None
            body_lines = []
    if open_key is not None:
        raise ValueError(
            "caption block 'caption:{}' was never closed (missing :end)".format(
                open_key))
    return blocks


def body_for(blocks, channel):
    """Resolve the caption body for ``channel`` (contract s3.1). Pure.

    Resolution order: the ``caption:<channel>`` block if present, else the
    ``caption:all`` block, else ``None`` (the body is absent for that channel).
    Returns ``None`` — never a fabricated body — when neither exists.
    """
    if channel not in utm.CHANNEL_SOURCE_MAP:
        raise ValueError("unknown channel {!r}".format(channel))
    if channel in blocks:
        return blocks[channel]
    if KEY_ALL in blocks:
        return blocks[KEY_ALL]
    return None


def load_captions(captions_path):
    """Read + parse ``captions.md`` at ``captions_path``.

    Returns the parsed blocks dict. Raises ``FileNotFoundError`` if the file is
    absent (the CLI turns this into a named exit-2 error) and ``ValueError`` on a
    malformed/duplicate block. Read-only; no wall-clock, no network.
    """
    path = Path(captions_path)
    if not path.is_file():
        raise FileNotFoundError("no captions.md at {}".format(path))
    return parse_captions(path.read_text(encoding="utf-8"))
