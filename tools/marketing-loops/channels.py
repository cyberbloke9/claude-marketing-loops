#!/usr/bin/env python3
"""Free-text ``Channels:`` line parser for the publish toolchain.

Sprint 002 (spec A-7; contract s3.5). Maps the free-text ``Channels:`` line of a
``meta.md`` (e.g. ``IG reel, YT short (LinkedIn text post variant included)``)
onto the canonical channel set ``{instagram, youtube, linkedin}``.

The canonical channel set and its order come from the Sprint-001
``utm.CHANNEL_SOURCE_MAP`` keys (imported, never forked) — the single source of
truth shared by both toolchains. The ALIAS table below (IG/YT/etc. -> canonical)
is the one new declaration this sprint authors, per contract s3.5.

Rules (contract s3.5):
    * Alias match is case-insensitive.
    * Format words (reel, short, carousel, PDF, text, post, variant, included)
      and punctuation/join tokens (+, comma, parens) are IGNORED — they neither
      map nor count as unmapped.
    * Any remaining token that is neither an alias nor a format word is an
      "unmapped platform token" (e.g. Twitter, TikTok, Threads) and is SURFACED
      (the CLI turns >=1 unmapped token into a usage error, exit 2 — never a
      silent guess or drop).
    * Dedup: each canonical channel appears at most once.
    * Result order is the canonical order (instagram, youtube, linkedin).

Pure library. No writes, no wall-clock, no network, no CLI side effects on
import. Stdlib only.
"""

import re
import sys
from pathlib import Path

# Import the Sprint-001 shared map from beside this file (runs from any cwd).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import utm  # noqa: E402

# Canonical channels + their fixed order, DERIVED from the shared map (no fork).
# Dict insertion order in utm.CHANNEL_SOURCE_MAP is instagram, youtube, linkedin.
CANONICAL_CHANNELS = tuple(utm.CHANNEL_SOURCE_MAP.keys())

# Alias table (contract s3.5). Keys are lower-cased tokens; values are canonical
# channels. This is the ONLY new channel declaration this sprint authors.
_ALIASES = {
    "ig": "instagram",
    "instagram": "instagram",
    "yt": "youtube",
    "youtube": "youtube",
    "linkedin": "linkedin",
}

# Format words that describe an asset's shape, not a channel (contract s3.5).
# Ignored: they neither map nor count as unmapped platform tokens.
_FORMAT_WORDS = frozenset({
    "reel", "short", "carousel", "pdf", "text", "post", "variant", "included",
})

# Punctuation / join characters stripped from each token's edges.
_PUNCT = "+,()"

_CHANNELS_LINE_RE = re.compile(r"^\s*Channels:\s*(?P<rest>.*)$", re.MULTILINE)


def extract_channels_line(meta_text):
    """Return the text after ``Channels:`` in meta.md, or None if no such line."""
    m = _CHANNELS_LINE_RE.search(meta_text)
    if m is None:
        return None
    return m.group("rest").strip()


def parse_channels_line(line):
    """Parse a ``Channels:`` value string (contract s3.5). Pure.

    Returns ``(channels, unmapped)`` where ``channels`` is a de-duplicated list
    in canonical order and ``unmapped`` is the ordered list of surfaced,
    channel-like tokens that matched neither an alias nor a format word.
    """
    found = set()
    unmapped = []
    for raw_token in (line or "").split():
        token = raw_token.strip(_PUNCT)
        if not token:
            continue  # pure punctuation / join word
        low = token.lower()
        if low in _ALIASES:
            found.add(_ALIASES[low])
        elif low in _FORMAT_WORDS:
            continue
        else:
            unmapped.append(token)
    channels = [c for c in CANONICAL_CHANNELS if c in found]
    return channels, unmapped


def channels_for_asset(meta_text):
    """Convenience: extract + parse. Returns ``(channels, unmapped, had_line)``.

    ``had_line`` is False when meta.md has no ``Channels:`` line at all (the CLI
    treats that as a precondition error, exit 2), distinct from a line that
    yields zero channels.
    """
    line = extract_channels_line(meta_text)
    if line is None:
        return [], [], False
    channels, unmapped = parse_channels_line(line)
    return channels, unmapped, True
