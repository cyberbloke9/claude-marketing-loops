#!/usr/bin/env python3
"""UTM verifier CLI for the TERREM marketing-loop toolchains.

Sprint 001 (spec s5.0 B-U4; contract s3.4). A thin CLI wrapper over the
``utm`` module. Scans one asset folder OR a content-root of asset folders and
reports, per asset, ``OK`` or the specific cited UTM violation(s).

Path auto-detect (contract s3.4):
    * if ``path`` itself contains a ``meta.md`` -> scan just that asset;
    * else treat ``path`` as a content-root and scan every immediate subdir
      that contains a ``meta.md``, in lexicographic slug order.

Output (stdout only, deterministic):
    OK  <slug>
    FAIL <slug>  <code>[, <code>...]  — <message>[; <message>...]

Exit codes (matching tools/marketing-render/validate.py convention):
    0  every scanned asset valid
    1  >=1 asset flagged (domain failure); a full report is still printed
    2  usage / precondition error (path missing, or a scan target with nothing
       to scan) -- message on stderr, nothing on stdout

Never reads the wall clock, no network, no file writes. Stdlib only.
"""

import argparse
import sys
from pathlib import Path

# Import the shared module from beside this file (runs from any cwd).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import utm  # noqa: E402


class PreconditionError(Exception):
    """Raised for exit-code-2 conditions (missing path / nothing to scan)."""


def resolve_targets(path):
    """Return an ordered list of asset folders to scan (contract s3.4).

    Raises PreconditionError (exit 2) if the path does not exist, or resolves
    to a content-root with zero meta.md-bearing subdirs.
    """
    p = Path(path)
    if not p.exists():
        raise PreconditionError("path does not exist: {}".format(path))
    if not p.is_dir():
        raise PreconditionError("path is not a directory: {}".format(path))
    if (p / "meta.md").is_file():
        return [p]
    subdirs = sorted(
        (child for child in p.iterdir()
         if child.is_dir() and (child / "meta.md").is_file()),
        key=lambda c: c.name,
    )
    if not subdirs:
        raise PreconditionError(
            "no meta.md found at {0} and no immediate subdirectory contains a "
            "meta.md (nothing to scan)".format(path))
    return subdirs


def format_line(result):
    """Render one asset result as its stable stdout line (contract s3.4)."""
    if result["ok"]:
        return "OK  {}".format(result["slug"])
    codes = ", ".join(v["code"] for v in result["violations"])
    messages = "; ".join(v["message"] for v in result["violations"])
    return "FAIL {}  {}  — {}".format(result["slug"], codes, messages)


def run(path):
    """Scan ``path`` and print the report. Returns the exit code (0 or 1)."""
    targets = resolve_targets(path)
    any_failed = False
    for asset_dir in targets:
        result = utm.validate_asset(asset_dir)
        if not result["ok"]:
            any_failed = True
        print(format_line(result))
    return 1 if any_failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify Flywheel UTM links in content asset meta.md files "
                    "against the documented scheme (spec s5.0 B-U4).")
    parser.add_argument(
        "path", nargs="?", default="content",
        help="a single asset folder OR a content-root of asset folders "
             "(default: content)")
    args = parser.parse_args(argv)
    try:
        return run(args.path)
    except PreconditionError as exc:
        sys.stderr.write("ERROR: {}\n".format(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
