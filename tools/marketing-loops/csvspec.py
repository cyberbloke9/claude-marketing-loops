#!/usr/bin/env python3
"""CSV column contracts + robust parser for the Gap-3 analytics toolchain.

Sprint 004 (spec s5.2 B-A1/B-A3; contract s3.1/s3.2). Declares the four
documented, versioned CSV column contracts (Instagram / YouTube / LinkedIn
platform exports + the site-analytics export) and a single pure entry point,
:func:`read_csv`, that validates a provided CSV against its contract and either
returns a list of typed row dicts or raises a cited :class:`CsvError`.

These column contracts are an AUTHORED INTERNAL contract (Assumption A-5): no
real platform export layout is reproduced here. Fixtures conform to them. They
are versioned exactly like ``manifest.json`` / ``qa-verdict.json`` are versioned
schemas — ``CSV_SCHEMA_VERSION`` is declared once below.

The B-A3 vs B-A4 crux, pinned (contract s3.1):
    * a BLANK cell in an int/num column -> the value is ABSENT (``None``), NOT
      corrupt and NOT zero (B-A4); parsing continues, exit stays 0 downstream.
    * a NON-BLANK cell that fails to parse (``abc``, ``12x``, ``1,2``) -> CORRUPT
      -> reject with a cited CsvError (B-A3: corruption never becomes a blank).
    * ``0`` / ``0.0`` is a genuinely PRESENT value, never conflated with absent.

Pure library: no CLI side effects on import, no wall clock, no network, no
writes. Stdlib only (``csv``, ``io``, ``re``, ``pathlib``).
"""

import csv
import io
import re
from pathlib import Path

# Declared once. Bump if a column contract changes shape (contract s3.1).
CSV_SCHEMA_VERSION = "1"

# Column type tokens.
T_STR = "str"
T_INT = "int"
T_NUM = "num"

_INT_RE = re.compile(r"^-?\d+$")
_NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")


class CsvError(Exception):
    """A cited CSV rejection (B-A3). The CLI maps this to exit code 2."""


# --- The four documented column contracts (spec s5.4 CSV-INPUTS) --------------
# Each contract: an ordered list of (header, type) pairs = the REQUIRED headers,
# plus the join column. Extra columns beyond the required set are IGNORED (not an
# error). Header match is exact and case-sensitive.

# Platform exports (Instagram / YouTube / LinkedIn) are STRUCTURALLY IDENTICAL;
# the row's channel is fixed by which --instagram/--youtube/--linkedin flag the
# file arrives on (a platform CSV carries no channel column). One row per
# published asset x channel — the craft-diagnostics source (B-A7).
_PLATFORM_COLUMNS = [
    ("utm_campaign", T_STR),       # join key (B-A2) -> asset slug + hook #
    ("three_s_hold_pct", T_NUM),   # Craft: 3s-hold %
    ("completion_pct", T_NUM),     # Craft: completion / swipe-through %
    ("shares", T_INT),             # Craft: Shares
    ("clicks", T_INT),             # Craft: Clicks
]

# Site-analytics export: per-campaign rows; the flywheel source (B-A6) and the
# sole home of the three WRR component inputs (A-5/A-6 authored contract). WRR is
# a single week-level rollup, so housing all three components in the one
# site-level export keeps WRR single-source and makes the Sprint-005 B-A5
# "any component absent -> blank WRR" edge testable at the value level.
_SITE_COLUMNS = [
    ("utm_source", T_STR),                  # filter (informational)
    ("utm_medium", T_STR),                  # filter: only 'social' rows count
    ("utm_campaign", T_STR),                # join key -> flywheel grouping (B-A6)
    ("clicks", T_INT),                      # Flywheel: clicks by campaign (B-A6)
    ("returning_viewers", T_INT),           # WRR component 1
    ("digest_opens", T_INT),                # WRR component 2
    ("returning_visitors_social", T_INT),   # WRR component 3
]


def _contract(name, columns, join):
    return {
        "schema_version": CSV_SCHEMA_VERSION,
        "name": name,
        "columns": list(columns),
        "headers": [h for h, _ in columns],
        "types": {h: t for h, t in columns},
        "join": join,
    }


# The four named contracts. instagram/youtube/linkedin share the platform shape
# but are named separately so the seam documents four distinct kinds.
CONTRACTS = {
    "instagram": _contract("instagram", _PLATFORM_COLUMNS, "utm_campaign"),
    "youtube": _contract("youtube", _PLATFORM_COLUMNS, "utm_campaign"),
    "linkedin": _contract("linkedin", _PLATFORM_COLUMNS, "utm_campaign"),
    "site": _contract("site", _SITE_COLUMNS, "utm_campaign"),
}

# The platform kinds (each one row -> a craft entry on that channel).
PLATFORM_KINDS = ("instagram", "youtube", "linkedin")


def _coerce(value, header, col_type, join_col, path, row_no):
    """Coerce one raw cell to its typed value or None (absent). Cited on error.

    * str: stripped verbatim; a blank JOIN column is a reject (row cannot join).
    * int/num: blank -> None (absent, B-A4); non-blank must parse or reject
      (corrupt, B-A3). ``0`` is a present value, never conflated with None.
    """
    raw = "" if value is None else value
    stripped = raw.strip()
    if col_type == T_STR:
        if header == join_col and stripped == "":
            raise CsvError(
                "{}: row {} column {!r}: blank join value (row cannot join)"
                .format(path, row_no, header))
        return stripped
    # Numeric columns.
    if stripped == "":
        return None  # absent, NOT zero (B-A4)
    if col_type == T_INT:
        if not _INT_RE.match(stripped):
            raise CsvError(
                "{}: row {} column {!r}: non-blank value {!r} is not an integer"
                .format(path, row_no, header, stripped))
        return int(stripped)
    # T_NUM
    if not _NUM_RE.match(stripped):
        raise CsvError(
            "{}: row {} column {!r}: non-blank value {!r} is not numeric"
            .format(path, row_no, header, stripped))
    return float(stripped)


def read_csv(path, contract):
    """Read + validate ``path`` against ``contract``; return typed row dicts.

    Returns a list of dicts ``{header: typed_value_or_None}`` restricted to the
    contract's required headers (extra columns ignored). A valid header with ZERO
    data rows returns ``[]`` — a present-but-empty source, NOT malformed.

    Raises :class:`CsvError` (CLI -> exit 2) on: undecodable bytes, unparseable
    CSV, empty file / missing required header(s), a data row with the wrong column
    count (incl. truncation), a non-blank non-numeric numeric cell, or a blank
    join column. Pure: no wall clock, no network, no writes.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CsvError("{}: not decodable as UTF-8 ({})".format(path, exc))
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        raise CsvError("{}: not parseable as CSV ({})".format(path, exc))

    required = contract["headers"]
    if not rows or not rows[0] or all(c.strip() == "" for c in rows[0]):
        raise CsvError(
            "{}: missing required header(s): {}".format(path, ", ".join(required)))

    header = rows[0]
    missing = [h for h in required if h not in header]
    if missing:
        raise CsvError(
            "{}: missing required header(s): {}".format(path, ", ".join(missing)))

    width = len(header)
    index = {h: header.index(h) for h in required}
    join_col = contract["join"]
    types = contract["types"]

    out = []
    data_row_no = 0
    for raw_row in rows[1:]:
        if len(raw_row) == 0:
            # A completely empty line is not a data row (tolerate trailing blank
            # lines). A truncated row still carries fields and is caught below.
            continue
        data_row_no += 1
        if len(raw_row) != width:
            raise CsvError(
                "{}: row {} has {} columns, expected {}".format(
                    path, data_row_no, len(raw_row), width))
        typed = {}
        for h in required:
            typed[h] = _coerce(
                raw_row[index[h]], h, types[h], join_col, path, data_row_no)
        out.append(typed)
    return out
