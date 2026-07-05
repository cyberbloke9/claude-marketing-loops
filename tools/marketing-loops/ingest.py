#!/usr/bin/env python3
"""Analytics CSV ingestion builder + CLI for the Gap-3 toolchain.

Sprint 004 (spec s5.2 B-A2/B-A4/B-A6; contract s3.4/s3.5). Reads whichever of the
four operator-provided CSVs it is given (Instagram / YouTube / LinkedIn platform
exports + the site-analytics export), joins metrics rows to content assets via
the frozen Sprint-001 join key, aggregates flywheel clicks and the three WRR
COMPONENT INPUTS (NOT the WRR sum — that is Sprint 005's B-A5), records every
absence, and emits a deterministic INGEST JSON structure (the seam Sprint 005's
scorecard compiler consumes).

Hard boundaries (contract s7):
    * NO scorecard markdown, NO ``metrics/*.md``, NO WRR sum, NO Missing-data
      prose — Sprint 005.
    * NO estimation / interpolation / defaulting / zero-filling: an absent metric
      stays ``null``; ``0`` is only ever a genuinely present ``0`` (B-A4/B-A7).
    * NO wall clock (``--week`` is validated as a string, never parsed vs "now"),
      NO network, NO writes except an optional ``--out`` file.

Exit codes (contract s3.6; matches render / Sprint 001-003):
    0  success, incl. a partial run (some sources absent) and the empty run.
    1  intentionally UNUSED (ingestion has no "domain verdict on well-formed
       input"; a corrupt CSV is malformed input -> 2, and unmatched-campaign /
       wrong-UTM are flags, not rejections).
    2  usage / precondition error (message on stderr, NO JSON on stdout, NO --out
       write): malformed --week; a provided --<source> path that does not exist;
       a bad --content-dir; a campaign collision; and EVERY B-A3 CSV rejection.

Stdlib only (``argparse``, ``json``, ``re``, ``pathlib``).
"""

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import csvspec   # noqa: E402
import assetmap  # noqa: E402

# Declared once (contract s3.5).
INGEST_SCHEMA_VERSION = "1"

_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")

# The three WRR component columns (site-analytics), in template order. comp3 is
# filtered to social rows; comp1/comp2 are week-level column sums (contract s3.4).
_WRR_COMPONENTS = (
    ("returning_viewers", False),
    ("digest_opens", False),
    ("returning_visitors_social", True),   # filtered to utm_medium == "social"
)

# Human-readable "not provided" phrasing per source (contract s3.4 step 7).
_SOURCE_LABEL = {
    "instagram": "instagram export not provided",
    "youtube": "youtube export not provided",
    "linkedin": "linkedin export not provided",
    "site": "site analytics export not provided",
}


class UsageError(Exception):
    """Raised for exit-code-2 conditions (message on stderr, no JSON)."""


def build_ingest(week, provided_rows, asset_map):
    """Pure builder -> the INGEST dict (contract s3.5). No I/O, no wall clock.

    ``provided_rows`` maps each source kind in {instagram, youtube, linkedin,
    site} to either its list of validated row dicts (present, possibly empty) or
    ``None`` (not provided). ``asset_map`` is :func:`assetmap.build_asset_map`.
    """
    sources_provided = {k: (provided_rows.get(k) is not None)
                        for k in ("instagram", "youtube", "linkedin", "site")}

    assets = sorted(asset_map.values(), key=lambda r: r["slug"])

    absences = []  # list of {kind, detail}; de-duped + sorted at the end.

    # --- source absences -----------------------------------------------------
    for kind in ("instagram", "youtube", "linkedin", "site"):
        if not sources_provided[kind]:
            absences.append({"kind": "source", "detail": _SOURCE_LABEL[kind]})

    # --- wrong-utm flags (B-A11) --------------------------------------------
    for record in assets:
        if not record["utm_valid"]:
            absences.append({
                "kind": "wrong-utm",
                "detail": "{}: {}".format(
                    record["slug"], ", ".join(record["utm_violations"])),
            })

    # --- craft rows (B-A7) ---------------------------------------------------
    craft = []
    unmatched = set()
    for kind in csvspec.PLATFORM_KINDS:
        rows = provided_rows.get(kind)
        if rows is None:
            continue
        for row in rows:
            campaign = row["utm_campaign"]
            record = asset_map.get(campaign)
            if record is None:
                unmatched.add(campaign)
                slug, hook = None, None
            else:
                slug, hook = record["slug"], record["hook_number"]
            craft.append({
                "campaign": campaign,
                "channel": kind,
                "slug": slug,
                "hook_number": hook,
                "three_s_hold_pct": row["three_s_hold_pct"],
                "completion_pct": row["completion_pct"],
                "shares": row["shares"],
                "clicks": row["clicks"],
            })
    craft.sort(key=lambda c: (c["campaign"], c["channel"]))

    # --- flywheel clicks by campaign (B-A6) ----------------------------------
    site_rows = provided_rows.get("site")
    flywheel = []
    if site_rows is not None:
        totals = {}       # campaign -> running int sum over present cells
        has_value = {}    # campaign -> bool (>=1 present clicks cell)
        for row in site_rows:
            if row["utm_medium"] != "social":
                continue
            campaign = row["utm_campaign"]
            totals.setdefault(campaign, 0)
            has_value.setdefault(campaign, False)
            if row["clicks"] is not None:
                totals[campaign] += row["clicks"]
                has_value[campaign] = True
        for campaign in sorted(totals):
            flywheel.append({
                "campaign": campaign,
                "clicks": totals[campaign] if has_value[campaign] else None,
            })
            if campaign not in asset_map:
                unmatched.add(campaign)

    # --- unmatched-campaign absences (deduped, from craft + flywheel) --------
    for campaign in sorted(unmatched):
        absences.append({"kind": "unmatched-campaign", "detail": campaign})

    # --- WRR component inputs (NOT summed — Sprint 005 does B-A5) -------------
    wrr = {}
    for column, social_only in _WRR_COMPONENTS:
        present = False
        value = None
        if site_rows is not None:
            total = 0
            seen = False
            for row in site_rows:
                if social_only and row["utm_medium"] != "social":
                    continue
                cell = row[column]
                if cell is not None:
                    total += cell
                    seen = True
            if seen:
                present, value = True, total
        wrr[column] = {"present": present, "value": value, "source": "site"}
        # A wrr-component absence is only a meaningful signal when the site source
        # IS provided but the column is blank. When site is absent entirely, the
        # single "site analytics export not provided" source-absence already covers
        # it (contract s4: the empty state has exactly one absence per source).
        if site_rows is not None and not present:
            absences.append({
                "kind": "wrr-component",
                "detail": "{} (WRR component) absent".format(column),
            })

    # --- deterministic absence ordering + de-dup -----------------------------
    seen_abs = set()
    deduped = []
    for entry in sorted(absences, key=lambda a: (a["kind"], a["detail"])):
        key = (entry["kind"], entry["detail"])
        if key not in seen_abs:
            seen_abs.add(key)
            deduped.append(entry)

    return {
        "schema_version": INGEST_SCHEMA_VERSION,
        "week": week,
        "sources_provided": sources_provided,
        "assets": assets,
        "wrr_components": wrr,
        "flywheel_clicks_by_campaign": flywheel,
        "craft": craft,
        "absences": deduped,
    }


def _default_content_dir():
    # repo/content (repo root is two levels above tools/marketing-loops/).
    return _HERE.parent.parent / "content"


def _load_sources(args):
    """Parse each provided CSV -> {kind: rows|None}. Raises UsageError (exit 2)."""
    provided = {}
    for kind in ("instagram", "youtube", "linkedin", "site"):
        path = getattr(args, kind)
        if path is None:
            provided[kind] = None
            continue
        p = Path(path)
        if not p.is_file():
            raise UsageError("--{} file not found: {}".format(kind, path))
        try:
            provided[kind] = csvspec.read_csv(p, csvspec.CONTRACTS[kind])
        except csvspec.CsvError as exc:
            raise UsageError(str(exc))
    return provided


def run(args):
    """Validate + build; return (exit_code, ingest_dict_or_None). No printing."""
    if not _WEEK_RE.match(args.week or ""):
        raise UsageError(
            "--week must be ISO 'YYYY-Www' (e.g. 2026-W27); got {!r}".format(
                args.week))

    content_dir = Path(args.content_dir) if args.content_dir else _default_content_dir()
    if not content_dir.is_dir():
        raise UsageError("--content-dir is not a directory: {}".format(content_dir))

    # Provided-path existence + CSV parse BEFORE building the asset map so a bad
    # path / corrupt CSV is reported first; all validation precedes any output.
    provided = _load_sources(args)

    try:
        asset_map = assetmap.build_asset_map(content_dir)
    except ValueError as exc:
        raise UsageError(str(exc))

    return build_ingest(args.week, provided, asset_map)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Ingest platform + site analytics CSV exports into the "
                    "validated INGEST structure Sprint 005 compiles into the "
                    "weekly scorecard (spec s5.2 B-A1..B-A6).")
    parser.add_argument("--week", required=True,
                        help="ISO week the exports cover, e.g. 2026-W27 (validated "
                             "as a string, never parsed against the wall clock)")
    parser.add_argument("--instagram", default=None, help="Instagram export CSV")
    parser.add_argument("--youtube", default=None, help="YouTube export CSV")
    parser.add_argument("--linkedin", default=None, help="LinkedIn export CSV")
    parser.add_argument("--site", default=None, help="site-analytics export CSV")
    parser.add_argument("--content-dir", default=None,
                        help="content root of <slug>/meta.md assets "
                             "(default: repo content/)")
    parser.add_argument("--out", default=None,
                        help="write the INGEST JSON here instead of stdout")
    args = parser.parse_args(argv)

    try:
        ingest = run(args)
    except UsageError as exc:
        sys.stderr.write("ERROR: {}\n".format(exc))
        return 2

    payload = json.dumps(ingest, sort_keys=True, indent=2) + "\n"
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
