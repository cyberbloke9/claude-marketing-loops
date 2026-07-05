#!/usr/bin/env python3
"""Weekly-scorecard compiler + CLI for the Gap-3 analytics toolchain.

Sprint 005 (spec s5.2 B-A5..B-A12; contract s3). Consumes the frozen Sprint-004
INGEST structure (built in-process via ``ingest.run``) plus the optional frozen
Sprint-002 QUEUE document and renders the weekly scorecard ``metrics/<week>.md``,
section-for-section faithful to ``metrics/TEMPLATE.md`` with an appended
``## Missing data`` section listing every blanked input.

This module DEFINES NO NEW JSON SCHEMA (its output is human-readable Markdown),
INVENTS NO METRIC, and NEVER modifies a Sprint-001..004 module. It only *imports*
the frozen ``ingest``, ``queue`` and ``schedule`` modules.

Missing-data provenance policy (contract s3.9), pinned so a reviewer reads the
mix as deliberate, not accidental:
    * ``source`` + ``unmatched-campaign`` INGEST absences are passed through
      (``source`` verbatim, e.g. "site analytics export not provided";
      ``unmatched-campaign`` as "unmatched-campaign: <campaign>").
    * ``wrr-component`` absences are RE-GENERATED here from
      ``ingest["wrr_components"]`` (each ``present == False`` -> one line), because
      frozen ``ingest`` only records a wrr-component absence when the site source
      is provided (its guard) -- the no-site / empty runs must still list all
      three components, and ``ingest`` is frozen. The INGEST ``wrr-component``
      absences are therefore SKIPPED in the pass-through to avoid double / mis-
      worded bullets.
    * ``wrong-utm`` is RE-GENERATED here from ``ingest["assets"]`` (each
      ``utm_valid == false`` -> "wrong-UTM asset <slug>: <violations>", B-A11) and
      the INGEST ``wrong-utm`` absence is SKIPPED in the pass-through.
    * The renderer's own structural blanks (last-week/trend WRR, flywheel rows
      2-3, vanity, A/B opposite-buckets + verdicts, qualitative decisions,
      hard-stop) are added directly.
All bullets are sorted lexicographically and de-duplicated.

The B-A5 WRR critical edge: WRR is filled ONLY when all three component inputs
are present; if ANY is absent the This-week cell is BLANK and each missing
component is listed -- a partial sum is FORBIDDEN (it is an invented number).

Exit codes (contract s3.11; match ingest / render / Sprints 001-004):
    0  success, incl. the partial (some sources absent) and empty (no sources)
       runs -- a valid partial/empty scorecard is a success (spec s6).
    1  intentionally UNUSED (mirrors ingest.py: no "domain verdict on well-formed
       input"; corrupt CSV / bad queue / bad path are usage errors -> 2; missing
       inputs and wrong-UTM are handled inside a successful scorecard).
    2  usage / precondition error (message on stderr, NO scorecard written): bad
       --week; a provided --<source> path not found; a bad --content-dir; a
       campaign collision; EVERY inherited B-A3 CSV rejection; a --queue path not
       found or an invalid QUEUE document; and --out + --stdout given together.

Stdlib only (``argparse``, ``json``, ``re``, ``pathlib``) plus the frozen in-repo
imports. NO ``datetime`` (no "now"; --week is a literal string). NO network.
"""

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import ingest    # noqa: E402  (frozen Sprint-004: INGEST build + CSV rejection)
import queue     # noqa: E402  (frozen Sprint-002: QUEUE load)
import schedule  # noqa: E402  (frozen Sprint-003: canonical channel order)

# Canonical channel order, DERIVED from the frozen schedule/utm maps (no fork).
CANONICAL_CHANNELS = schedule.CANONICAL_CHANNELS

# The template's verbatim WRR metric label (metrics/TEMPLATE.md line 9).
_WRR_LABEL = (
    "**WRR — Weekly Returning Readers** (repeat consumers across "
    "≥2 consecutive weeks: returning viewers + digest opens + returning "
    "site visitors from social)"
)

# WRR component columns, in template order (must match ingest._WRR_COMPONENTS).
_WRR_COMPONENT_ORDER = (
    "returning_viewers",
    "digest_opens",
    "returning_visitors_social",
)

# The template preamble (metrics/TEMPLATE.md line 3), verbatim.
_PREAMBLE = ("Loop 5 output. Compiled from platform exports + site analytics. "
             "Retention first; vanity last.")


# --------------------------------------------------------------------------- #
# Markdown cell / row helpers (single-space empty cell, matching the template) #
# --------------------------------------------------------------------------- #

def _cell(value):
    """Render one table cell body. Blank cell => a single space (template style).

    ``value`` is a pre-formatted string ("" for blank). Truthiness is safe here
    because a genuine ``0`` was already formatted to the truthy string "0" by
    :func:`_fmt`; only "" (blank) is falsy.
    """
    return " " + value + " " if value else " "


def _row(cells):
    """Render a full pipe-table row from a list of pre-formatted cell strings."""
    return "|" + "|".join(_cell(c) for c in cells) + "|"


def _fmt(value):
    """Format a numeric INGEST value to a scorecard string. ``None`` -> "" (blank).

    A genuine ``0`` / ``0.0`` renders "0" (never conflated with a blank cell,
    spec B-A7). Integral floats drop the ``.0`` (31.0 -> "31"); 29.5 -> "29.5".
    """
    if value is None:
        return ""
    if isinstance(value, bool):  # defensive: never expected, never a metric
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


# --------------------------------------------------------------------------- #
# Missing-data accumulation                                                    #
# --------------------------------------------------------------------------- #

def _sorted_unique(items):
    """Lexicographically sort + de-duplicate the Missing-data bullet strings."""
    return sorted(set(items))


# --------------------------------------------------------------------------- #
# Pure builder                                                                 #
# --------------------------------------------------------------------------- #

def build_scorecard(ingest_dict, queue_dict, week):
    """Render the scorecard Markdown + return the ordered Missing-data bullets.

    Pure: no I/O, no wall clock, no network. ``queue_dict`` is a loaded QUEUE
    document, or ``None`` when ``--queue`` was omitted. Returns
    ``(markdown, missing)`` where ``missing`` is the sorted, de-duplicated bullet
    list (also embedded as the ``## Missing data`` section of ``markdown``).
    """
    missing = []
    lines = []

    # -- 1. title + preamble --------------------------------------------------
    lines.append("# Weekly Scorecard — {}".format(week))
    lines.append("")
    lines.append(_PREAMBLE)
    lines.append("")

    # -- 2. North star / WRR (B-A5, the critical edge) ------------------------
    lines.append("## North star")
    lines.append("")
    lines.append(_row(["Metric", "This week", "Last week", "Trend"]))
    lines.append("|---|---|---|---|")
    wrr = ingest_dict["wrr_components"]
    all_present = all(wrr[c]["present"] for c in _WRR_COMPONENT_ORDER)
    if all_present:
        this_week = _fmt(sum(wrr[c]["value"] for c in _WRR_COMPONENT_ORDER))
    else:
        this_week = ""  # blank -- a partial sum is forbidden (invented number)
    lines.append(_row([_WRR_LABEL, this_week, "", ""]))
    lines.append("")
    # Absent-component listing regenerated here (frozen ingest only records these
    # when site IS provided; the no-site/empty runs must still list all three).
    for comp in _WRR_COMPONENT_ORDER:
        if not wrr[comp]["present"]:
            missing.append("WRR component '{}' absent".format(comp))
    # Last-week WRR and trend are structurally unavailable this sprint.
    missing.append("last-week WRR not provided (no prior-week input)")
    missing.append("WRR trend not computable (needs last-week WRR)")

    # -- 3. Flywheel (B-A6) ---------------------------------------------------
    lines.append("## Flywheel")
    lines.append("")
    lines.append(_row(["Metric", "Value", "Notes"]))
    lines.append("|---|---|---|")
    site_provided = ingest_dict["sources_provided"]["site"]
    flywheel = ingest_dict["flywheel_clicks_by_campaign"]
    if not site_provided:
        # Site absent -> row-1 blank; the single source-absence line already
        # covers it (no per-campaign spam) -- pass-through carries it below.
        row1_value = ""
    else:
        parts = []
        for entry in flywheel:  # already lexicographic by campaign (INGEST order)
            clicks = _fmt(entry["clicks"])
            parts.append("{}: {}".format(entry["campaign"], clicks))
            if entry["clicks"] is None:
                missing.append(
                    "flywheel clicks absent for campaign {}".format(
                        entry["campaign"]))
        row1_value = "<br>".join(parts)  # multiline cell, one line per campaign
    lines.append(_row(["Clicks to intel.terrem.in (by UTM campaign)",
                       row1_value, ""]))
    lines.append(_row(["Locality-page sessions from social", "", ""]))
    lines.append(_row(["Sign-ups / alerts created from content traffic", "", ""]))
    lines.append("")
    missing.append("Flywheel 'Locality-page sessions from social' "
                   "has no input column")
    missing.append("Flywheel 'Sign-ups / alerts created from content traffic' "
                   "has no input column")

    # -- 4. Craft diagnostics (B-A7) ------------------------------------------
    lines.append("## Craft diagnostics (per asset)")
    lines.append("")
    lines.append(_row(["Asset", "Channel", "3s-hold %",
                       "Completion / swipe-through %", "Shares", "Clicks",
                       "Hook #"]))
    lines.append("|---|---|---|---|---|---|---|")
    for entry in ingest_dict["craft"]:  # INGEST order: (campaign, channel)
        if entry["slug"] is not None:
            asset = entry["slug"]
        else:
            asset = "{} (unmatched)".format(entry["campaign"])
        three = _fmt(entry["three_s_hold_pct"])
        comp = _fmt(entry["completion_pct"])
        shares = _fmt(entry["shares"])
        clicks = _fmt(entry["clicks"])
        hook = _fmt(entry["hook_number"])
        lines.append(_row([asset, entry["channel"], three, comp, shares,
                           clicks, hook]))
        # Blank metric cells listed (blank != 0, B-A7).
        label = entry["slug"] if entry["slug"] is not None else \
            "{} (unmatched)".format(entry["campaign"])
        for metric_name, raw in (("3s-hold %", entry["three_s_hold_pct"]),
                                 ("Completion %", entry["completion_pct"]),
                                 ("Shares", entry["shares"]),
                                 ("Clicks", entry["clicks"])):
            if raw is None:
                missing.append("craft {} absent for {} ({})".format(
                    metric_name, label, entry["channel"]))
        if entry["hook_number"] is None and entry["slug"] is not None:
            missing.append("hook # absent for {}".format(entry["slug"]))
    lines.append("")

    # -- 5. Posting-time A/B (B-A8) -- single-week semantics (contract s3.6) ---
    lines.append("## Posting-time A/B (weeks 1–8)")
    lines.append("")
    lines.append(_row(["Channel", "Morning slot perf",
                       "Evening (3–8pm IST) perf", "Verdict so far"]))
    lines.append("|---|---|---|---|")
    ab_rows, ab_missing = _build_ab(ingest_dict, queue_dict, week)
    lines.extend(ab_rows)
    missing.extend(ab_missing)
    lines.append("")

    # -- 6. Vanity (B-A10 fidelity) -------------------------------------------
    lines.append("## Vanity (tracked, never optimized)")
    lines.append("")
    # Template line "Followers: __ · Likes: __" with both blanks preserved.
    lines.append("Followers: __ · Likes: __".replace("__", ""))
    lines.append("")
    missing.append("Vanity 'Followers' has no input column")
    missing.append("Vanity 'Likes' has no input column")

    # -- 7. Decisions fed back (B-A9) -----------------------------------------
    lines.append("## Decisions fed back")
    lines.append("")
    lines.append("- → Loop 1: which signal types resonated / flopped")
    loop2, loop2_missing = _build_loop2(ingest_dict)
    lines.append(loop2)
    if loop2_missing:
        missing.append(loop2_missing)
    lines.append("- → Loop 3: format changes")
    lines.append("- **Hard-stop check:** WRR flat after 8 published weeks? "
                 "→ stop scaling volume, re-enter Loop 2 (resonance "
                 "problem, not reach problem).")
    lines.append("")
    missing.append("Loop 1 signal-resonance decision is qualitative "
                   "(operator-authored)")
    missing.append("Loop 3 format-changes decision is qualitative "
                   "(operator-authored)")
    missing.append("hard-stop WRR-flat check needs 8 published weeks")

    # -- 8. pass-through INGEST absences (source + unmatched only) -------------
    for absence in ingest_dict["absences"]:
        kind = absence["kind"]
        if kind == "source":
            missing.append(absence["detail"])
        elif kind == "unmatched-campaign":
            missing.append("unmatched-campaign: {}".format(absence["detail"]))
        # wrr-component and wrong-utm are regenerated (see module docstring).

    # -- 9. wrong-UTM assets regenerated from ingest["assets"] (B-A11) --------
    for record in ingest_dict["assets"]:
        if not record["utm_valid"]:
            missing.append("wrong-UTM asset {}: {}".format(
                record["slug"], ", ".join(record["utm_violations"])))

    # -- 10. Missing data section ---------------------------------------------
    missing = _sorted_unique(missing)
    lines.append("## Missing data")
    lines.append("")
    for bullet in missing:
        lines.append("- {}".format(bullet))

    markdown = "\n".join(lines) + "\n"
    return markdown, missing


def _build_ab(ingest_dict, queue_dict, week):
    """Build the A/B table's channel rows + its Missing-data bullets (s3.6)."""
    rows = []
    miss = []
    # Sum of present clicks per channel across this week's craft entries.
    clicks_by_channel = {}
    for entry in ingest_dict["craft"]:
        if entry["clicks"] is None:
            continue
        clicks_by_channel.setdefault(entry["channel"], 0)
        clicks_by_channel[entry["channel"]] += entry["clicks"]

    if queue_dict is None:
        # No queue -> every cell blank; a single aggregate line (no per-channel).
        for channel in CANONICAL_CHANNELS:
            rows.append(_row([channel, "", "", ""]))
        miss.append("publish queue not provided "
                    "(posting-time A/B table blank)")
        return rows, miss

    for channel in CANONICAL_CHANNELS:
        bucket = _bucket_from_queue(queue_dict, week, channel)
        morning, evening, verdict = "", "", ""
        if bucket is None:
            rows.append(_row([channel, morning, evening, verdict]))
            miss.append("no {} slot recorded for {}".format(channel, week))
            miss.append("posting-time A/B verdict for {} needs cross-week "
                        "comparison".format(channel))
            continue
        perf_value = clicks_by_channel.get(channel)
        perf = _fmt(perf_value) if perf_value is not None else ""
        opposite = (schedule.BUCKET_EVENING if bucket == schedule.BUCKET_MORNING
                    else schedule.BUCKET_MORNING)
        if bucket == schedule.BUCKET_MORNING:
            morning = perf
        else:
            evening = perf
        rows.append(_row([channel, morning, evening, verdict]))
        # The active bucket, when it holds no measured data, is itself blank.
        if perf == "":
            miss.append("no {} {} data in {}".format(channel, bucket, week))
        # The opposite bucket is necessarily blank in a single-week scorecard.
        miss.append("no {} {} data in {}".format(channel, opposite, week))
        miss.append("posting-time A/B verdict for {} needs cross-week "
                    "comparison".format(channel))
    return rows, miss


def _bucket_from_queue(queue_dict, week, channel):
    """Return the recorded bucket for (week, channel) from the QUEUE, or None.

    Reads the bucket from a queue row's ``schedule_slot`` (``<week>/<bucket>/
    <HH:MM>``); NEVER recomputes it via ``schedule.bucket_for`` -- recomputing
    would fabricate a slot for an asset that was never queued (contract s3.6).
    """
    buckets = []
    for row in queue_dict.get("rows", []):
        if row.get("week") != week or row.get("channel") != channel:
            continue
        slot = row.get("schedule_slot")
        if not slot:
            continue
        parts = slot.split("/")
        if len(parts) >= 2 and parts[1]:
            buckets.append(parts[1])
    if not buckets:
        return None
    # All rows for a (week, channel) share one deterministic bucket; take the
    # sorted-first for total determinism even against a hand-edited queue.
    return sorted(buckets)[0]


def _build_loop2(ingest_dict):
    """Build the Loop-2 hook-ranking bullet + optional Missing-data line (s3.8)."""
    template = "- → Loop 2: hook winners & retirements (bottom third monthly)"
    # Per matched asset: total present clicks across its channels.
    totals = {}   # slug -> [running clicks, has_present, hook_number]
    for entry in ingest_dict["craft"]:
        slug = entry["slug"]
        if slug is None:
            continue
        rec = totals.setdefault(slug, [0, False, entry["hook_number"]])
        if entry["clicks"] is not None:
            rec[0] += entry["clicks"]
            rec[1] = True
    qualifying = [
        (slug, data[0], data[2])
        for slug, data in totals.items()
        if data[1] and data[2] is not None
    ]
    if len(qualifying) < 2:
        return template, "hook ranking needs ≥2 assets with clicks + hook #"
    # Top = highest clicks; tie-break ascending slug. Bottom = lowest clicks;
    # tie-break ascending slug.
    top = sorted(qualifying, key=lambda q: (-q[1], q[0]))[0]
    bottom = sorted(qualifying, key=lambda q: (q[1], q[0]))[0]
    clause = " — top hook #{} ({} clicks); retire-candidate hook #{} " \
             "({} clicks)".format(top[2], top[1], bottom[2], bottom[1])
    return template + clause, None


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def _default_metrics_dir():
    # repo/metrics (repo root is two levels above tools/marketing-loops/).
    return _HERE.parent.parent / "metrics"


def run(args):
    """Validate + build; return the scorecard Markdown string. Raises for exit 2.

    Delegates INGEST construction to the frozen ``ingest.run`` (inheriting every
    B-A3 CSV rejection), optionally loads the QUEUE, and calls
    :func:`build_scorecard`. Performs NO write (the caller does), so a corrupt
    input leaves no file behind.
    """
    ingest_dict = ingest.run(args)  # raises ingest.UsageError -> exit 2

    queue_dict = None
    if args.queue is not None:
        qpath = Path(args.queue)
        if not qpath.is_file():
            raise ingest.UsageError(
                "--queue file not found: {}".format(args.queue))
        try:
            queue_dict = queue.load_queue(qpath)
        except ValueError as exc:
            raise ingest.UsageError(str(exc))

    markdown, _missing = build_scorecard(ingest_dict, queue_dict, args.week)
    return markdown


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile platform + site analytics into the weekly scorecard "
                    "metrics/<week>.md, template-faithful with an appended "
                    "Missing-data section (spec s5.2 B-A5..B-A12).")
    parser.add_argument("--week", required=True,
                        help="ISO week the scorecard covers, e.g. 2026-W27 "
                             "(a literal string; never parsed against 'now')")
    parser.add_argument("--instagram", default=None, help="Instagram export CSV")
    parser.add_argument("--youtube", default=None, help="YouTube export CSV")
    parser.add_argument("--linkedin", default=None, help="LinkedIn export CSV")
    parser.add_argument("--site", default=None, help="site-analytics export CSV")
    parser.add_argument("--content-dir", default=None,
                        help="content root of <slug>/meta.md assets "
                             "(default: repo content/)")
    parser.add_argument("--queue", default=None,
                        help="publish-queue JSON (Sprint-002 QUEUE) for the "
                             "posting-time A/B table; omitted => table blank")
    parser.add_argument("--out", default=None,
                        help="write the scorecard here (default metrics/<week>.md)")
    parser.add_argument("--stdout", action="store_true",
                        help="write the scorecard to stdout and no file")
    args = parser.parse_args(argv)

    if args.out is not None and args.stdout:
        sys.stderr.write("ERROR: --out and --stdout are mutually exclusive\n")
        return 2

    try:
        markdown = run(args)
    except ingest.UsageError as exc:
        sys.stderr.write("ERROR: {}\n".format(exc))
        return 2

    if args.stdout:
        sys.stdout.write(markdown)
        return 0

    if args.out is not None:
        out_path = Path(args.out)
    else:
        out_path = _default_metrics_dir() / "{}.md".format(args.week)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    sys.stdout.write("{}\n".format(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
