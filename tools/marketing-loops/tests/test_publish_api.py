#!/usr/bin/env python3
"""Tests for the Sprint 002 publish_api.py skeleton (contract sprint_002).

Mocked transport only; NO real network anywhere. Mirrors the existing test
header convention (sys.path insert of the tool dir; subprocess.run with
cwd=_REPO_ROOT for CLI-level checks, as test_utm.py / test_mark_posted.py do).
"""

import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

_TESTS_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _TESTS_DIR.parent
_REPO_ROOT = _TOOL_DIR.parent.parent
_PUBLISH = _TOOL_DIR / "publish_api.py"

if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import publish_api  # noqa: E402

_REAL_SLUG = "2026-07-09-anarock-vs-propequity"
_REAL_WEEK = "2026-W28"

# The real asset is a 3-image carousel (contract s3). The seed replicates it so
# the instagram adapter (Sprint 003) renders/executes the real flow hermetically.
_REAL_ATTACHMENTS = [
    "content/{}/render/format-01.png".format(_REAL_SLUG),
    "content/{}/render/format-02.png".format(_REAL_SLUG),
    "content/{}/render/format-03.png".format(_REAL_SLUG),
]
# Verbatim caption from the real package (contains a real newline, B5).
_REAL_CAPTION = (
    "ANAROCK says Bengaluru housing sales grew 1% last quarter. PropEquity says "
    "47%. Same city, same three months. Swipe for all four cities — and the "
    "three checks that tell you which headline to trust.\n\n"
    "https://intel.terrem.in/markets?utm_source=instagram&utm_medium=social"
    "&utm_campaign=anarock-vs-propequity"
)


# --------------------------------------------------------------------------- #
# Helpers to build a self-contained throwaway workspace (queue + packages).
# --------------------------------------------------------------------------- #
def _seed_workspace(d, rows=None, write_packages=True, abs_packages=True,
                    attachments=None, caption=None):
    """Create content/publish-queue.json + package files under temp dir ``d``.

    Returns the queue path. Default rows = the real 2-row asset (ig + linkedin);
    default package payload replicates the real 3-image carousel + caption so the
    instagram adapter (Sprint 003) renders 8 steps. ``attachments`` / ``caption``
    override the package payload (used by the >10 / 0 / single-image fixtures).

    ``package_path`` is resolved by the tool relative to CWD (matching the
    contract's literal ``Path(package_path)``). ``abs_packages=True`` (the
    default) writes ABSOLUTE package paths so ``run(...)``-direct tests are
    self-contained regardless of CWD; CLI tests (run with ``cwd=d``) pass
    ``abs_packages=False`` to keep the repo-relative ``content/...`` paths the
    stdout template asserts.
    """
    root = Path(d)
    content = root / "content"
    content.mkdir(parents=True, exist_ok=True)

    def _pkg_rel(channel):
        return "content/{}/publish/{}.json".format(_REAL_SLUG, channel)

    if rows is None:
        rows = [
            {"slug": _REAL_SLUG, "channel": "instagram", "state": "queued",
             "week": _REAL_WEEK, "schedule_slot": "2026-W28/morning/09:00",
             "package_path": _pkg_rel("instagram"),
             "posted_date": None, "permalink": None},
            {"slug": _REAL_SLUG, "channel": "linkedin", "state": "queued",
             "week": _REAL_WEEK, "schedule_slot": "2026-W28/morning/08:30",
             "package_path": _pkg_rel("linkedin"),
             "posted_date": None, "permalink": None},
        ]

    atts = attachments if attachments is not None else list(_REAL_ATTACHMENTS)
    cap = caption if caption is not None else _REAL_CAPTION

    if write_packages:
        for r in rows:
            pp = r.get("package_path")
            if not pp:
                continue
            fp = root / pp  # always create under the temp dir
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(json.dumps({
                "channel": r["channel"], "slug": r["slug"],
                "caption": cap, "attachments": atts,
                "schedule_slot": r["schedule_slot"],
            }))

    # Sprint 004 seed extension (contract s7.1): the LinkedIn DOCUMENT flow reads
    # content/<slug>/render/manifest.json for the PDF filename. Write it for every
    # row's slug (deduped) so the default dry-run drives the document flow
    # hermetically. Dry-run reads only the filename (no PDF bytes); execute tests
    # seed their own carousel.pdf + PNGs. The IG adapter ignores the manifest, so
    # the IG >10/0/single-image fixtures are unperturbed.
    for slug in {r["slug"] for r in rows}:
        mdir = content / slug / "render"
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / "manifest.json").write_text(json.dumps({
            "schema_version": "2", "slug": slug, "pdf": "carousel.pdf"}))

    if abs_packages:
        for r in rows:
            pp = r.get("package_path")
            if pp:
                r["package_path"] = str(root / pp)

    qp = content / "publish-queue.json"
    qp.write_text(json.dumps({"schema_version": "1", "rows": rows}))
    return qp


def _run_cli(argv, cwd):
    return subprocess.run(
        [sys.executable, str(_PUBLISH)] + argv,
        capture_output=True, text=True, cwd=str(cwd))


# --------------------------------------------------------------------------- #
# Pure helpers.
# --------------------------------------------------------------------------- #
class TestPureHelpers(unittest.TestCase):
    def test_placeholder(self):
        self.assertEqual(publish_api.placeholder("ig-parent-creation-id"),
                         "<ig-parent-creation-id>")
        self.assertEqual(publish_api.placeholder("ig-child-container-id", 2),
                         "<ig-child-container-id-2>")
        self.assertEqual(publish_api.placeholder("li-image-urn", 1),
                         "<li-image-urn-1>")

    def test_redaction(self):
        self.assertEqual(publish_api.redacted(), "<REDACTED>")
        self.assertEqual(publish_api.redact_bearer("Bearer sk-real"),
                         "Bearer <REDACTED>")
        self.assertEqual(publish_api.redact_token_param("access_token=sk-real"),
                         "access_token=<REDACTED>")
        # the real secret never survives
        self.assertNotIn("sk-real", publish_api.redact_bearer("Bearer sk-real"))
        self.assertNotIn("sk-real",
                         publish_api.redact_token_param("access_token=sk-real"))

    def test_image_url_join(self):
        self.assertEqual(
            publish_api.image_url("https://a.example/social-assets", "slug", "1.png"),
            "https://a.example/social-assets/slug/1.png")
        # trailing slash collapsed
        self.assertEqual(
            publish_api.image_url("https://a.example/base/", "slug", "1.png"),
            "https://a.example/base/slug/1.png")
        # None base -> placeholder
        self.assertEqual(
            publish_api.image_url(None, "slug", "1.png"),
            "<PUBLIC_ASSET_BASE_URL>/slug/1.png")

    def test_parse_env_worked_cases(self):
        env, err = publish_api.parse_env("\n".join([
            "FOO=bar",
            'QUOTED="bar baz"',
            "SQUOTED='bar'",
            "INNERQ='bar\"baz'",
            "SPACED=bar baz",
            'LEADQ="bar',
            "TRAILC=bar # note",
            "EMPTY=",
            "# a full comment",
            "  ",
        ]))
        self.assertIsNone(err)
        self.assertEqual(env["FOO"], "bar")
        self.assertEqual(env["QUOTED"], "bar baz")
        self.assertEqual(env["SQUOTED"], "bar")
        self.assertEqual(env["INNERQ"], 'bar"baz')
        self.assertEqual(env["SPACED"], "bar baz")
        self.assertEqual(env["LEADQ"], '"bar')
        self.assertEqual(env["TRAILC"], "bar")
        self.assertEqual(env["EMPTY"], "")

    def test_parse_env_last_wins(self):
        env, err = publish_api.parse_env("FOO=a\nFOO=b")
        self.assertIsNone(err)
        self.assertEqual(env["FOO"], "b")

    def test_parse_env_no_equals_errors(self):
        env, err = publish_api.parse_env("VALIDKEY=ok\njustnoise")
        self.assertIsNone(env)
        self.assertIn("line 2", err)
        self.assertNotIn("justnoise", err)  # value/line never echoed verbatim


# --------------------------------------------------------------------------- #
# Transport seam + no-network proofs.
# --------------------------------------------------------------------------- #
class TestTransportSeam(unittest.TestCase):
    def test_recording_transport_records_and_returns(self):
        t = publish_api.RecordingTransport(responses=[{"id": "child_1"}])
        resp = t.request("POST", "https://x/media", headers={"a": "b"}, body=b"z")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.json(), {"id": "child_1"})
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(t.calls[0][0], "POST")

    def test_recording_transport_default_empty(self):
        t = publish_api.RecordingTransport()
        self.assertEqual(t.request("GET", "https://x").json(), {})

    def test_raising_transport_raises(self):
        with self.assertRaises(AssertionError):
            publish_api.RaisingTransport().request("GET", "https://x")

    def test_ast_single_urlopen_site_inside_transport(self):
        tree = ast.parse(_PUBLISH.read_text())
        # collect urlopen references in both import forms
        refs = [n for n in ast.walk(tree)
                if (isinstance(n, ast.Attribute) and n.attr == "urlopen")
                or (isinstance(n, ast.Name) and n.id == "urlopen")]
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and n.func in refs]
        self.assertEqual(len(calls), 1, "exactly one urlopen call site required")
        # that single call must be lexically inside the Transport class body
        transport_cls = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == "Transport")
        inside = [n for n in ast.walk(transport_cls)
                  if isinstance(n, ast.Call) and n.func in refs]
        self.assertEqual(len(inside), 1, "urlopen must be inside Transport")

    def test_dryrun_never_touches_transport(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d)
            t = publish_api.RaisingTransport()
            code, out, err = publish_api.run(
                week=_REAL_WEEK,
                queue_path=str(Path(d) / "content" / "publish-queue.json"),
                transport=t)
            self.assertEqual(code, 0, msg=err)
            # A RecordingTransport would show zero calls too.
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d)
            rec = publish_api.RecordingTransport()
            code, out, err = publish_api.run(
                week=_REAL_WEEK,
                queue_path=str(Path(d) / "content" / "publish-queue.json"),
                transport=rec)
            self.assertEqual(code, 0)
            self.assertEqual(len(rec.calls), 0)

    def test_live_uses_injected_transport(self):
        # Sprint 006 (was test_live_noop_never_touches_transport): the honest
        # no-op is gone — a passing live gate now POSTS via the INJECTED transport
        # (never the real socket). The default 2-row seed drives IG (8 calls) +
        # LI document (3 calls) = 11 recorded calls; both rows flip to posted.
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            env = Path(d) / "live.env"
            env.write_text("\n".join([
                "IG_USER_ID=IGID", "IG_ACCESS_TOKEN=IGTOK",
                "LI_PERSON_URN=urn:li:person:X", "LI_ACCESS_TOKEN=LITOK",
                "PUBLIC_ASSET_BASE_URL=https://assets.example/social-assets",
            ]))
            rec = publish_api.RecordingTransport(responses=_two_row_live_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(env),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertEqual(len(rec.calls), 11)
            states = {r["channel"]: r["state"]
                      for r in json.loads(qp.read_text())["rows"]}
            self.assertEqual(states, {"instagram": "posted", "linkedin": "posted"})


# --------------------------------------------------------------------------- #
# Dry-run plan (the default).
# --------------------------------------------------------------------------- #
class TestDryRunPlan(unittest.TestCase):
    def _plan(self, d):
        return json.loads((Path(d) / "content" / "publish-plan.json").read_text())

    def test_default_mode_is_dry_run_two_rows(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 0, msg=err)
            plan = self._plan(d)
            self.assertEqual(plan["mode"], "dry-run")
            self.assertEqual(plan["week"], _REAL_WEEK)
            # Sprint 004 conscious update (contract s7): the linkedin row now
            # carries the 3-step DEFAULT document flow + the adapter note (was
            # steps:0 + "Sprint 004+"). The instagram row is UNCHANGED (8 steps).
            self.assertEqual([(r["slug"], r["channel"], len(r["steps"]))
                              for r in plan["rows"]],
                             [(_REAL_SLUG, "instagram", 8),
                              (_REAL_SLUG, "linkedin", 3)])
            self.assertIn("instagram adapter (Instagram Login",
                          plan["rows"][0]["note"])
            self.assertIn("linkedin adapter (member profile, api.linkedin.com; "
                          "document flow); 3 HTTP calls; verified R4-B4/R5-6",
                          plan["rows"][1]["note"])

    def test_stdout_template_exact(self):
        # Sprint 003 conscious update (contract s7.2): the instagram block now
        # renders the exact 8-step carousel flow. LinkedIn block byte-identical.
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            r = _run_cli(["--week", _REAL_WEEK], cwd=d)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            plan_path = "content/publish-plan.json"
            host = "https://graph.instagram.com"
            base_ph = "<PUBLIC_ASSET_BASE_URL>"
            cap = _REAL_CAPTION.replace("\n", "\\n")  # stdout escape rule
            children = ("<ig-child-container-id-1>,<ig-child-container-id-2>,"
                        "<ig-child-container-id-3>")
            # Sprint 004 linkedin block (contract s6.1). Payload lines are built by
            # the IDENTICAL compact json.dumps the renderer uses (NEVER hand-typed:
            # the caption's em-dash is — and newlines are \n under default
            # ensure_ascii); the post body comes from the same builder the adapter
            # uses, so the test cannot silently drift from production.
            li_version = publish_api.LINKEDIN_VERSION_DEFAULT
            li_json_headers = (
                "Authorization: Bearer <REDACTED>, "
                "Content-Type: application/json, "
                "LinkedIn-Version: {}, "
                "X-Restli-Protocol-Version: 2.0.0".format(li_version))
            li_init_payload = json.dumps(
                {"initializeUploadRequest": {"owner": "<LI_PERSON_URN>"}},
                sort_keys=True, separators=(",", ":"))
            li_doc_payload = json.dumps(
                publish_api._li_document_post_body(
                    "<LI_PERSON_URN>", _REAL_CAPTION, "<li-document-urn>",
                    _REAL_SLUG),
                sort_keys=True, separators=(",", ":"))
            expected = "\n".join([
                "Publishing plan for week 2026-W28 (mode: dry-run)",
                "",
                "Row 1/2: {} (instagram)".format(_REAL_SLUG),
                "  package: content/{}/publish/instagram.json".format(_REAL_SLUG),
                "  steps: 8",
                "    1. IG · check content_publishing_limit",
                "       GET {}/<IG_USER_ID>/content_publishing_limit".format(host),
                "       params: access_token=<REDACTED>, "
                "fields=quota_usage,quota_total",
                "    2. IG · create child container 1/3",
                "       POST {}/<IG_USER_ID>/media".format(host),
                "       params: access_token=<REDACTED>, "
                "image_url={}/{}/format-01.png, is_carousel_item=true".format(
                    base_ph, _REAL_SLUG),
                "    3. IG · create child container 2/3",
                "       POST {}/<IG_USER_ID>/media".format(host),
                "       params: access_token=<REDACTED>, "
                "image_url={}/{}/format-02.png, is_carousel_item=true".format(
                    base_ph, _REAL_SLUG),
                "    4. IG · create child container 3/3",
                "       POST {}/<IG_USER_ID>/media".format(host),
                "       params: access_token=<REDACTED>, "
                "image_url={}/{}/format-03.png, is_carousel_item=true".format(
                    base_ph, _REAL_SLUG),
                "    5. IG · create parent carousel container",
                "       POST {}/<IG_USER_ID>/media".format(host),
                "       params: access_token=<REDACTED>, caption={}, "
                "children={}, media_type=CAROUSEL".format(cap, children),
                "    6. IG · poll container status",
                "       GET {}/<ig-parent-creation-id>".format(host),
                "       params: access_token=<REDACTED>, fields=status_code",
                "    7. IG · publish media",
                "       POST {}/<IG_USER_ID>/media_publish".format(host),
                "       params: access_token=<REDACTED>, "
                "creation_id=<ig-parent-creation-id>",
                "    8. IG · fetch permalink",
                "       GET {}/<ig-media-id>".format(host),
                "       params: access_token=<REDACTED>, fields=permalink",
                "  note: instagram adapter (Instagram Login, "
                "graph.instagram.com); 8 HTTP calls; verified R4-B2/R4-B3/R5-3",
                "",
                "Row 2/2: {} (linkedin)".format(_REAL_SLUG),
                "  package: content/{}/publish/linkedin.json".format(_REAL_SLUG),
                "  steps: 3",
                "    1. LI · initialize document upload",
                "       POST https://api.linkedin.com/rest/documents",
                "       params: action=initializeUpload",
                "       headers: {}".format(li_json_headers),
                "       payload: {}".format(li_init_payload),
                "    2. LI · upload document bytes",
                "       PUT <li-upload-url-1>",
                "       params: (none)",
                "       headers: Authorization: Bearer <REDACTED>",
                "       payload: <binary PDF: carousel.pdf>",
                "    3. LI · create document post",
                "       POST https://api.linkedin.com/rest/posts",
                "       params: (none)",
                "       headers: {}".format(li_json_headers),
                "       payload: {}".format(li_doc_payload),
                "  note: linkedin adapter (member profile, api.linkedin.com; "
                "document flow); 3 HTTP calls; verified R4-B4/R5-6",
                "",
                "Plan written to {}".format(plan_path),
                "",
            ])
            self.assertEqual(r.stdout, expected)

    def test_determinism_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            _run_cli(["--week", _REAL_WEEK], cwd=d)
            first = (Path(d) / "content" / "publish-plan.json").read_bytes()
            _run_cli(["--week", _REAL_WEEK], cwd=d)
            second = (Path(d) / "content" / "publish-plan.json").read_bytes()
            self.assertEqual(first, second)

    def test_dryrun_does_not_write_queue(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            before = qp.read_bytes()
            publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(qp.read_bytes(), before)

    def test_plan_deterministic_serialization(self):
        # sort_keys + indent 2 + single trailing newline
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            _run_cli(["--week", _REAL_WEEK], cwd=d)
            text = (Path(d) / "content" / "publish-plan.json").read_text()
            self.assertTrue(text.endswith("\n"))
            self.assertFalse(text.endswith("\n\n"))
            # keys sorted at top level
            self.assertEqual(json.loads(text)["schema_version"], "1")

    def test_scope_slug_and_channel(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", queue_path=str(qp))
            self.assertEqual(code, 0)
            plan = self._plan(d)
            self.assertEqual([r["channel"] for r in plan["rows"]], ["linkedin"])


# --------------------------------------------------------------------------- #
# Empty state.
# --------------------------------------------------------------------------- #
class TestEmptyState(unittest.TestCase):
    def test_empty_scope_exit0_no_plan_written(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            r = _run_cli(["--week", "2026-W01"], cwd=d)
            self.assertEqual(r.returncode, 0)
            self.assertIn("nothing queued for 2026-W01", r.stderr)
            self.assertFalse((Path(d) / "content" / "publish-plan.json").exists())

    def test_empty_scope_preserves_existing_plan(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            _run_cli(["--week", _REAL_WEEK], cwd=d)  # writes a plan
            plan_path = Path(d) / "content" / "publish-plan.json"
            before = hashlib.sha256(plan_path.read_bytes()).hexdigest()
            _run_cli(["--week", "2026-W01"], cwd=d)  # empty scope
            after = hashlib.sha256(plan_path.read_bytes()).hexdigest()
            self.assertEqual(before, after)

    def test_empty_message_includes_filters(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(
                week="2026-W01", slug="nope", channel="instagram",
                queue_path=str(qp))
            self.assertEqual(code, 0)
            joined = "\n".join(err)
            self.assertIn("slug=nope", joined)
            self.assertIn("channel=instagram", joined)


# --------------------------------------------------------------------------- #
# Validation / exit 2.
# --------------------------------------------------------------------------- #
class TestValidation(unittest.TestCase):
    def test_malformed_week(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d)
            for bad in ("2026-28", "2026-W5", "garbage"):
                r = _run_cli(["--week", bad], cwd=d)
                self.assertEqual(r.returncode, 2, msg=bad)
                self.assertIn("ERROR", r.stderr)
            self.assertFalse((Path(d) / "content" / "publish-plan.json").exists())

    def test_unknown_channel(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d)
            r = _run_cli(["--week", _REAL_WEEK, "--channel", "twitter"], cwd=d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)

    def test_both_modes(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d)
            r = _run_cli(["--week", _REAL_WEEK, "--dry-run", "--live"], cwd=d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("mutually exclusive", r.stderr)

    def test_malformed_date(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d)
            r = _run_cli(["--week", _REAL_WEEK, "--date", "2026-13-40"], cwd=d)
            self.assertEqual(r.returncode, 2)

    def test_bad_linkedin_post_type(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d)
            r = _run_cli(["--week", _REAL_WEEK, "--linkedin-post-type", "bogus"],
                         cwd=d)
            self.assertEqual(r.returncode, 2)

    def test_bad_max_per_day(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, max_per_day=0, queue_path=str(qp))
            self.assertEqual(code, 2)
            self.assertIn(">= 1", "\n".join(err))

    def test_invalid_queue(self):
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            content.mkdir()
            (content / "publish-queue.json").write_text("{ not json")
            r = _run_cli(["--week", _REAL_WEEK], cwd=d)
            self.assertEqual(r.returncode, 2)

    def test_missing_package_exit2_no_plan(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, write_packages=False)
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 2)
            self.assertIn("package not found", "\n".join(err))
            self.assertFalse((Path(d) / "content" / "publish-plan.json").exists())

    def test_invalid_package_json_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            # corrupt one package
            bad = Path(d) / "content" / _REAL_SLUG / "publish" / "instagram.json"
            bad.write_text("{ broken")
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 2)
            self.assertIn("not valid JSON", "\n".join(err))


# --------------------------------------------------------------------------- #
# Live gate.
# --------------------------------------------------------------------------- #
class TestLiveGate(unittest.TestCase):
    def _env(self, d, **overrides):
        base = {
            "IG_USER_ID": "IGID", "IG_ACCESS_TOKEN": "IGTOK",
            "LI_PERSON_URN": "urn:li:person:X", "LI_ACCESS_TOKEN": "LITOK",
            "PUBLIC_ASSET_BASE_URL": "https://assets.example/social-assets",
        }
        base.update(overrides)
        ep = Path(d) / "live.env"
        ep.write_text("\n".join("{}={}".format(k, v) for k, v in base.items()))
        return ep

    def test_live_no_env_no_ack_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                env_path=str(Path(d) / "nope.env"))
            self.assertEqual(code, 2)
            joined = "\n".join(err)
            self.assertIn("env file", joined)
            self.assertIn("--i-have-verified-dry-run", joined)
            self.assertIn("--date", joined)
            self.assertFalse((Path(d) / "content" / "publish-plan.json").exists())

    def test_live_missing_token_named_not_echoed(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            ep = self._env(d, IG_ACCESS_TOKEN="")  # empty -> missing
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True)
            self.assertEqual(code, 2)
            self.assertIn("IG_ACCESS_TOKEN", "\n".join(err))

    def test_live_scoped_tokens_only(self):
        # --channel linkedin => only LI tokens required; IG absence is fine. The
        # gate accepts LI-only tokens and the row then posts via the mock (Sprint
        # 006: a passing gate posts; no real socket — RecordingTransport).
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = Path(d) / "li.env"
            ep.write_text("\n".join([
                "LI_PERSON_URN=urn:li:person:X", "LI_ACCESS_TOKEN=LITOK",
                "PUBLIC_ASSET_BASE_URL=https://a.example",
            ]))
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", mode="live",
                queue_path=str(qp), date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True,
                transport=publish_api.RecordingTransport(
                    responses=_li_doc_responses()))
            self.assertEqual(code, 0, msg="\n".join(err))
            li = [r for r in json.loads(qp.read_text())["rows"]
                  if r["channel"] == "linkedin"][0]
            self.assertEqual(li["state"], "posted")

    def test_live_missing_base_url_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            ep = self._env(d, PUBLIC_ASSET_BASE_URL="")
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True)
            self.assertEqual(code, 2)
            self.assertIn("PUBLIC_ASSET_BASE_URL", "\n".join(err))

    def test_live_base_url_from_flag(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = self._env(d, PUBLIC_ASSET_BASE_URL="")
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                public_asset_base_url="https://flag.example",
                i_have_verified_dry_run=True,
                transport=publish_api.RecordingTransport(
                    responses=_two_row_live_responses()))
            self.assertEqual(code, 0, msg="\n".join(err))

    def test_live_missing_date_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            ep = self._env(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                env_path=str(ep), i_have_verified_dry_run=True)
            self.assertEqual(code, 2)
            self.assertIn("--date", "\n".join(err))

    def test_live_pass_gate_posts_both_rows(self):
        # Sprint 006 (was test_live_pass_gate_honest_noop): a passing gate is no
        # longer a no-op — it POSTS both rows and writes the queue. stdout carries
        # a real "posted <slug> <channel> <date>" line per row (mark_posted idiom).
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = self._env(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True,
                transport=publish_api.RecordingTransport(
                    responses=_two_row_live_responses()))
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn(
                "posted {} instagram 2026-07-09".format(_REAL_SLUG), out)
            self.assertIn(
                "posted {} linkedin 2026-07-09".format(_REAL_SLUG), out)
            for r in json.loads(qp.read_text())["rows"]:
                self.assertEqual(r["state"], "posted")
                self.assertEqual(r["posted_date"], "2026-07-09")
                self.assertTrue(r["permalink"])

    def test_live_no_secret_echoed(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = self._env(d, IG_ACCESS_TOKEN="SENTINEL_SECRET")
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True,
                transport=publish_api.RecordingTransport(
                    responses=_two_row_live_responses()))
            self.assertEqual(code, 0, msg="\n".join(err))
            combined = "\n".join(out + err)
            self.assertNotIn("SENTINEL_SECRET", combined)
            # nor in the written queue
            self.assertNotIn("SENTINEL_SECRET", qp.read_text())


# --------------------------------------------------------------------------- #
# Instagram adapter (Sprint 003). Mocked transport only; no real network.
# --------------------------------------------------------------------------- #
_IG_ROW = {"slug": _REAL_SLUG, "channel": "instagram"}


def _ig_package(attachments=None, caption=None):
    return {
        "channel": "instagram", "slug": _REAL_SLUG,
        "caption": caption if caption is not None else _REAL_CAPTION,
        "attachments": (attachments if attachments is not None
                        else list(_REAL_ATTACHMENTS)),
        "schedule_slot": "2026-W28/morning/09:00",
    }


def _ig_ctx(token="SENTINEL_TOKEN"):
    return {
        "ig_user_id": "IGID", "ig_access_token": token,
        "public_asset_base_url": "https://assets.example/social-assets",
        "sleep": lambda _s: None,
    }


def _happy_carousel_responses(permalink="https://www.instagram.com/p/ABC/"):
    return [
        {"data": [{"quota_usage": 1, "quota_total": 50}]},   # limit
        {"id": "child_1"}, {"id": "child_2"}, {"id": "child_3"},
        {"id": "PARENT"},                                     # parent
        {"status_code": "FINISHED"},                          # poll
        {"id": "MEDIA"},                                      # publish
        {"permalink": permalink},                            # permalink
    ]


class TestInstagramDryRunFidelity(unittest.TestCase):
    def _plan(self, d):
        return json.loads((Path(d) / "content" / "publish-plan.json").read_text())

    def test_instagram_row_eight_steps_shape(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 0, msg="\n".join(err))
            plan = self._plan(d)
            ig = [r for r in plan["rows"] if r["channel"] == "instagram"][0]
            self.assertEqual(len(ig["steps"]), 8)
            methods = [(s["method"], s["url"]) for s in ig["steps"]]
            host = "https://graph.instagram.com"
            self.assertEqual(methods, [
                ("GET", host + "/<IG_USER_ID>/content_publishing_limit"),
                ("POST", host + "/<IG_USER_ID>/media"),
                ("POST", host + "/<IG_USER_ID>/media"),
                ("POST", host + "/<IG_USER_ID>/media"),
                ("POST", host + "/<IG_USER_ID>/media"),
                ("GET", host + "/<ig-parent-creation-id>"),
                ("POST", host + "/<IG_USER_ID>/media_publish"),
                ("GET", host + "/<ig-media-id>"),
            ])
            for s in ig["steps"]:
                self.assertEqual(s["headers"], {})
                self.assertIsNone(s["payload"])
                self.assertEqual(s["params"]["access_token"], "<REDACTED>")
            # child placeholders threaded into parent children param
            parent = ig["steps"][4]
            self.assertEqual(
                parent["params"]["children"],
                "<ig-child-container-id-1>,<ig-child-container-id-2>,"
                "<ig-child-container-id-3>")
            self.assertEqual(parent["params"]["media_type"], "CAROUSEL")
            # image_url placeholder base (no --public-asset-base-url)
            self.assertEqual(
                ig["steps"][1]["params"]["image_url"],
                "<PUBLIC_ASSET_BASE_URL>/{}/format-01.png".format(_REAL_SLUG))
            # caption VERBATIM in machine JSON (real newline preserved)
            self.assertIn("\n", parent["params"]["caption"])
            self.assertEqual(parent["params"]["caption"], _REAL_CAPTION)
            # linkedin row now carries the Sprint-004 3-step document flow
            li = [r for r in plan["rows"] if r["channel"] == "linkedin"][0]
            self.assertEqual(len(li["steps"]), 3)
            self.assertIn("linkedin adapter (member profile", li["note"])

    def test_concrete_base_url(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, queue_path=str(qp),
                public_asset_base_url="https://assets.example/social-assets")
            self.assertEqual(code, 0, msg="\n".join(err))
            plan = self._plan(d)
            ig = [r for r in plan["rows"] if r["channel"] == "instagram"][0]
            self.assertEqual(
                ig["steps"][1]["params"]["image_url"],
                "https://assets.example/social-assets/{}/format-01.png".format(
                    _REAL_SLUG))

    def test_determinism_with_steps(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            first = (Path(d) / "content" / "publish-plan.json").read_bytes()
            publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            second = (Path(d) / "content" / "publish-plan.json").read_bytes()
            self.assertEqual(first, second)

    def test_no_secret_in_dryrun_output(self):
        # dry-run never carries a token at all; sentinel absent from stdout + JSON.
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            r = _run_cli(["--week", _REAL_WEEK], cwd=d)
            self.assertNotIn("SENTINEL_TOKEN", r.stdout)
            body = (Path(d) / "content" / "publish-plan.json").read_text()
            self.assertNotIn("SENTINEL_TOKEN", body)
            self.assertIn("<REDACTED>", body)


class TestInstagramExecute(unittest.TestCase):
    def test_happy_carousel_path(self):
        adapter = publish_api.InstagramAdapter()
        t = publish_api.RecordingTransport(responses=_happy_carousel_responses())
        res = adapter.execute(_IG_ROW, _ig_package(), _ig_ctx(), t)
        self.assertEqual(res.permalink, "https://www.instagram.com/p/ABC/")
        self.assertEqual(res.media_id, "MEDIA")
        self.assertEqual(len(t.calls), 8)
        methods = [c[0] for c in t.calls]
        self.assertEqual(
            methods, ["GET", "POST", "POST", "POST", "POST", "GET", "POST", "GET"])
        # real token in EVERY execute call (proves live sends it)
        for c in t.calls:
            self.assertIn("access_token=SENTINEL_TOKEN", c[1])
        # dependent-value wiring: child ids -> parent children; parent -> poll+publish
        parent_url = t.calls[4][1]
        self.assertIn("child_1", parent_url)
        self.assertIn("child_2", parent_url)
        self.assertIn("child_3", parent_url)
        self.assertIn("/PARENT", urlsplit(t.calls[5][1]).path)
        self.assertIn("creation_id=PARENT", t.calls[6][1])
        self.assertIn("/MEDIA", urlsplit(t.calls[7][1]).path)

    def test_token_never_in_plan(self):
        # the plan path never receives the real token (redaction is render-time).
        adapter = publish_api.InstagramAdapter()
        steps = adapter.plan_steps(_IG_ROW, _ig_package(), None)
        self.assertNotIn("SENTINEL_TOKEN", json.dumps(steps))
        for s in steps:
            self.assertEqual(s["params"]["access_token"], "<REDACTED>")

    def test_parity_plan_matches_transport(self):
        adapter = publish_api.InstagramAdapter()
        steps = adapter.plan_steps(_IG_ROW, _ig_package(), None)
        t = publish_api.RecordingTransport(responses=_happy_carousel_responses())
        adapter.execute(_IG_ROW, _ig_package(), _ig_ctx(), t)
        self.assertEqual(len(steps), len(t.calls))
        subs = {"<IG_USER_ID>": "IGID", "<ig-parent-creation-id>": "PARENT",
                "<ig-media-id>": "MEDIA"}
        for pstep, call in zip(steps, t.calls):
            self.assertEqual(pstep["method"], call[0])
            plan_path = urlsplit(pstep["url"]).path
            for ph, real in subs.items():
                plan_path = plan_path.replace(ph, real)
            self.assertEqual(plan_path, urlsplit(call[1]).path)

    def test_container_error_refusal(self):
        for bad in ("ERROR", "EXPIRED"):
            resp = _happy_carousel_responses()
            resp = resp[:5] + [{"status_code": bad}]
            adapter = publish_api.InstagramAdapter()
            t = publish_api.RecordingTransport(responses=resp)
            with self.assertRaises(publish_api.AdapterRefusal) as cm:
                adapter.execute(_IG_ROW, _ig_package(), _ig_ctx(), t)
            self.assertIn(bad, str(cm.exception))

    def test_poll_exhausted_refusal(self):
        resp = _happy_carousel_responses()[:5] + [
            {"status_code": "IN_PROGRESS"}, {"status_code": "IN_PROGRESS"}]
        orig = publish_api.MAX_POLL_ATTEMPTS
        publish_api.MAX_POLL_ATTEMPTS = 2
        try:
            adapter = publish_api.InstagramAdapter()
            t = publish_api.RecordingTransport(responses=resp)
            with self.assertRaises(publish_api.AdapterRefusal) as cm:
                adapter.execute(_IG_ROW, _ig_package(), _ig_ctx(), t)
            self.assertIn("did not finish", str(cm.exception))
        finally:
            publish_api.MAX_POLL_ATTEMPTS = orig

    def test_rate_limit_refusal_before_media(self):
        adapter = publish_api.InstagramAdapter()
        t = publish_api.RecordingTransport(
            responses=[{"data": [{"quota_usage": 50, "quota_total": 50}]}])
        with self.assertRaises(publish_api.AdapterRefusal) as cm:
            adapter.execute(_IG_ROW, _ig_package(), _ig_ctx(), t)
        self.assertIn("rate limit", str(cm.exception).lower())
        self.assertEqual(len(t.calls), 1)  # only the limit call

    def test_unexpected_response_is_refusal(self):
        # a /media response missing "id" -> refusal, not an uncaught KeyError.
        resp = [{"data": [{"quota_usage": 1, "quota_total": 50}]}, {"nope": "x"}]
        adapter = publish_api.InstagramAdapter()
        t = publish_api.RecordingTransport(responses=resp)
        with self.assertRaises(publish_api.AdapterRefusal):
            adapter.execute(_IG_ROW, _ig_package(), _ig_ctx(), t)


class TestInstagramAttachmentGuard(unittest.TestCase):
    def test_dryrun_over_ten_exit2_no_plan(self):
        eleven = ["content/{}/render/format-{:02d}.png".format(_REAL_SLUG, i)
                  for i in range(1, 12)]
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, attachments=eleven)
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 2)
            self.assertIn("exceeds 10", "\n".join(err))
            self.assertFalse((Path(d) / "content" / "publish-plan.json").exists())

    def test_dryrun_zero_attachments_exit2_no_plan(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, attachments=[])
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 2)
            self.assertIn("no attachments", "\n".join(err))
            self.assertFalse((Path(d) / "content" / "publish-plan.json").exists())

    def test_execute_over_ten_usage_error(self):
        eleven = ["r/format-{:02d}.png".format(i) for i in range(1, 12)]
        adapter = publish_api.InstagramAdapter()
        with self.assertRaises(publish_api.AdapterUsageError):
            adapter.execute(_IG_ROW, _ig_package(attachments=eleven), _ig_ctx(),
                            publish_api.RecordingTransport())

    def test_execute_zero_usage_error(self):
        adapter = publish_api.InstagramAdapter()
        with self.assertRaises(publish_api.AdapterUsageError):
            adapter.execute(_IG_ROW, _ig_package(attachments=[]), _ig_ctx(),
                            publish_api.RecordingTransport())


class TestInstagramSingleImage(unittest.TestCase):
    # Contract s4.2 conflict: the prose enumerates 5 stages (limit -> create ->
    # poll -> publish -> permalink) with "NO separate parent step", but the
    # parenthetical says "(6 steps)". The 5-stage enumeration + "no parent" is the
    # only FAITHFUL reading (carousel is N+5=8 for N=3; drop the parent for a
    # single image -> N+4=5). We assert the exact label sequence so the test
    # encodes the "no parent / no carousel flags" behavior. See generator_trace.
    _EXPECTED_LABELS = [
        "IG · check content_publishing_limit",
        "IG · create media container",
        "IG · poll container status",
        "IG · publish media",
        "IG · fetch permalink",
    ]

    def test_dryrun_single_image_no_carousel(self):
        one = ["content/{}/render/format-01.png".format(_REAL_SLUG)]
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, attachments=one)
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 0, msg="\n".join(err))
            plan = json.loads(
                (Path(d) / "content" / "publish-plan.json").read_text())
            ig = [r for r in plan["rows"] if r["channel"] == "instagram"][0]
            self.assertEqual([s["label"] for s in ig["steps"]],
                             self._EXPECTED_LABELS)
            body = json.dumps(ig["steps"])
            self.assertNotIn("is_carousel_item", body)
            self.assertNotIn("media_type", body)
            # the single container feeds the poll + publish creation_id
            self.assertIn("<ig-parent-creation-id>", ig["steps"][2]["url"])

    def test_execute_single_image(self):
        adapter = publish_api.InstagramAdapter()
        one = ["content/{}/render/format-01.png".format(_REAL_SLUG)]
        responses = [
            {"data": [{"quota_usage": 1, "quota_total": 50}]},
            {"id": "CONT"}, {"status_code": "FINISHED"}, {"id": "MEDIA"},
            {"permalink": "https://www.instagram.com/p/XYZ/"},
        ]
        t = publish_api.RecordingTransport(responses=responses)
        res = adapter.execute(_IG_ROW, _ig_package(attachments=one), _ig_ctx(), t)
        self.assertEqual(res.permalink, "https://www.instagram.com/p/XYZ/")
        self.assertEqual(len(t.calls), 5)
        self.assertNotIn("is_carousel_item", t.calls[1][1])
        self.assertNotIn("media_type", t.calls[1][1])


class TestInstagramLive(unittest.TestCase):
    def test_live_instagram_posts_and_transitions(self):
        # Sprint 006 (was test_live_instagram_noop_raising_transport): live now
        # posts the IG row via the injected transport and flips it queued->posted
        # with the fetched permalink; no secret ever reaches stdout/stderr/queue.
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = Path(d) / "ig.env"
            ep.write_text("\n".join([
                "IG_USER_ID=SENTINEL_IGID", "IG_ACCESS_TOKEN=SENTINEL_TOKEN",
                "PUBLIC_ASSET_BASE_URL=https://assets.example/social-assets",
            ]))
            rec = publish_api.RecordingTransport(
                responses=_happy_carousel_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="instagram", mode="live",
                queue_path=str(qp), date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn(
                "posted {} instagram 2026-07-09".format(_REAL_SLUG), out)
            ig = [r for r in json.loads(qp.read_text())["rows"]
                  if r["channel"] == "instagram"][0]
            self.assertEqual(ig["state"], "posted")
            self.assertEqual(ig["permalink"], "https://www.instagram.com/p/ABC/")
            self.assertNotIn("SENTINEL", "\n".join(out + err))  # no secret
            self.assertNotIn("SENTINEL", qp.read_text())
            # live writes the queue only, never publish-plan.json
            self.assertFalse(
                (Path(d) / "content" / "publish-plan.json").exists())


class TestInstagramBlacklist(unittest.TestCase):
    def test_refuted_names_absent_correct_names_present(self):
        src = _PUBLISH.read_text()
        # the refuted permission name ends in ..._content_publishing (NOT _limit)
        self.assertIsNone(re.search(r"content_publishing(?!_limit)", src))
        self.assertNotIn("media_publishing", src)
        # the correct endpoints ARE present
        self.assertIn("media_publish", src)
        self.assertIn("content_publishing_limit", src)


# --------------------------------------------------------------------------- #
# LinkedIn adapter (Sprint 004). Mocked transport only; no real network.
# --------------------------------------------------------------------------- #
_LI_HOST = "https://api.linkedin.com"


def _li_seed(d, attachments_n=3):
    """Hermetic execute workspace: content/<slug>/render/{manifest.json,
    carousel.pdf, format-0i.png} + publish/linkedin.json. Returns (row, package)
    with an absolute package_path (so the manifest resolves cwd-independently) and
    absolute attachment paths (so multiimage read_bytes() succeeds)."""
    root = Path(d)
    slug = _REAL_SLUG
    render = root / "content" / slug / "render"
    render.mkdir(parents=True, exist_ok=True)
    (render / "manifest.json").write_text(json.dumps(
        {"schema_version": "2", "slug": slug, "pdf": "carousel.pdf"}))
    (render / "carousel.pdf").write_bytes(b"%PDF-1.4 fake pdf bytes")
    atts = []
    for i in range(1, attachments_n + 1):
        p = render / "format-{:02d}.png".format(i)
        p.write_bytes(("PNGBYTES" + str(i)).encode())
        atts.append(str(p))
    pub = root / "content" / slug / "publish"
    pub.mkdir(parents=True, exist_ok=True)
    pkg_path = pub / "linkedin.json"
    package = {
        "channel": "linkedin", "slug": slug, "caption": _REAL_CAPTION,
        "attachments": atts, "schedule_slot": "2026-W28/morning/08:30",
    }
    pkg_path.write_text(json.dumps(package))
    row = {"slug": slug, "channel": "linkedin", "package_path": str(pkg_path)}
    return row, package


def _li_ctx(post_type="document", token="SENTINEL_LITOKEN", version=None):
    return {
        "li_person_urn": "urn:li:person:REAL",
        "li_access_token": token,
        "linkedin_post_type": post_type,
        "linkedin_version": version or publish_api.LINKEDIN_VERSION_DEFAULT,
    }


def _li_doc_responses():
    return [
        {"value": {"uploadUrl": "https://up.li/DOC",
                   "document": "urn:li:document:D1"}},
        {},                                # empty upload response
        {"id": "urn:li:share:S1"},         # post (body id fallback)
    ]


def _li_multi_responses():
    r = []
    for i in (1, 2, 3):
        r.append({"value": {"uploadUrl": "https://up.li/IMG{}".format(i),
                            "image": "urn:li:image:I{}".format(i)}})
        r.append({})
    r.append({"id": "urn:li:share:MULTI"})
    return r


class TestLinkedInDryRunFidelity(unittest.TestCase):
    def _li(self, d):
        plan = json.loads(
            (Path(d) / "content" / "publish-plan.json").read_text())
        return [r for r in plan["rows"] if r["channel"] == "linkedin"][0]

    def test_document_default_three_steps(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", queue_path=str(qp))
            self.assertEqual(code, 0, msg="\n".join(err))
            li = self._li(d)
            self.assertEqual(len(li["steps"]), 3)
            self.assertEqual(
                [(s["method"], s["url"]) for s in li["steps"]],
                [("POST", _LI_HOST + "/rest/documents"),
                 ("PUT", "<li-upload-url-1>"),
                 ("POST", _LI_HOST + "/rest/posts")])
            self.assertEqual(li["steps"][0]["params"],
                             {"action": "initializeUpload"})
            for idx in (0, 2):  # versioned headers on the JSON /rest/* steps
                h = li["steps"][idx]["headers"]
                self.assertEqual(h["Authorization"], "Bearer <REDACTED>")
                self.assertEqual(h["LinkedIn-Version"],
                                 publish_api.LINKEDIN_VERSION_DEFAULT)
                self.assertEqual(h["X-Restli-Protocol-Version"], "2.0.0")
                self.assertEqual(h["Content-Type"], "application/json")
            self.assertEqual(li["steps"][1]["headers"],
                             {"Authorization": "Bearer <REDACTED>"})
            self.assertEqual(li["steps"][1]["payload"],
                             "<binary PDF: carousel.pdf>")
            body = li["steps"][2]["payload"]
            self.assertEqual(body["content"]["media"]["id"], "<li-document-urn>")
            self.assertEqual(body["author"], "<LI_PERSON_URN>")
            self.assertEqual(body["commentary"], _REAL_CAPTION)  # verbatim (B5)
            self.assertIn("\n", body["commentary"])
            self.assertEqual(body["visibility"], "PUBLIC")
            self.assertEqual(body["lifecycleState"], "PUBLISHED")
            self.assertIn("document flow", li["note"])

    def test_multiimage_seven_steps(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", queue_path=str(qp),
                linkedin_post_type="multi-image")
            self.assertEqual(code, 0, msg="\n".join(err))
            li = self._li(d)
            self.assertEqual(len(li["steps"]), 7)
            self.assertEqual(
                [(s["method"], s["url"]) for s in li["steps"]],
                [("POST", _LI_HOST + "/rest/images"),
                 ("PUT", "<li-upload-url-1>"),
                 ("POST", _LI_HOST + "/rest/images"),
                 ("PUT", "<li-upload-url-2>"),
                 ("POST", _LI_HOST + "/rest/images"),
                 ("PUT", "<li-upload-url-3>"),
                 ("POST", _LI_HOST + "/rest/posts")])
            body = li["steps"][6]["payload"]
            self.assertEqual(
                body["content"]["multiImage"]["images"],
                [{"id": "<li-image-urn-1>"}, {"id": "<li-image-urn-2>"},
                 {"id": "<li-image-urn-3>"}])
            self.assertEqual(body["visibility"], "PUBLIC")
            self.assertEqual(body["lifecycleState"], "PUBLISHED")
            self.assertEqual(body["author"], "<LI_PERSON_URN>")
            self.assertIn("multi-image flow", li["note"])

    def test_exactly_one_flow_no_cross_contamination(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            publish_api.run(week=_REAL_WEEK, channel="linkedin",
                            queue_path=str(qp))
            li = self._li(d)
            b = json.dumps(li)
            self.assertIn("rest/documents", b)
            self.assertNotIn("rest/images", b)
            self.assertNotIn("multiImage", b)
            self.assertEqual(
                set(li["steps"][2]["payload"]["content"].keys()), {"media"})

            publish_api.run(week=_REAL_WEEK, channel="linkedin",
                            queue_path=str(qp), linkedin_post_type="multi-image")
            li2 = self._li(d)
            b2 = json.dumps(li2)
            self.assertIn("rest/images", b2)
            self.assertNotIn("rest/documents", b2)
            self.assertNotIn('"media"', b2)
            self.assertEqual(
                set(li2["steps"][6]["payload"]["content"].keys()), {"multiImage"})

    def test_version_flag_in_headers(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            publish_api.run(week=_REAL_WEEK, channel="linkedin",
                            queue_path=str(qp), linkedin_version="202503")
            li = self._li(d)
            for idx in (0, 2):
                self.assertEqual(
                    li["steps"][idx]["headers"]["LinkedIn-Version"], "202503")

    def test_determinism_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            publish_api.run(week=_REAL_WEEK, channel="linkedin",
                            queue_path=str(qp))
            first = (Path(d) / "content" / "publish-plan.json").read_bytes()
            publish_api.run(week=_REAL_WEEK, channel="linkedin",
                            queue_path=str(qp))
            second = (Path(d) / "content" / "publish-plan.json").read_bytes()
            self.assertEqual(first, second)


class TestLinkedInExecute(unittest.TestCase):
    def test_happy_document_member_profile(self):
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            t = publish_api.RecordingTransport(responses=_li_doc_responses())
            res = publish_api.LinkedInAdapter().execute(row, package, _li_ctx(), t)
            self.assertEqual(
                res.permalink,
                "https://www.linkedin.com/feed/update/urn:li:share:S1")
            self.assertEqual(res.post_urn, "urn:li:share:S1")
            self.assertEqual([c[0] for c in t.calls], ["POST", "PUT", "POST"])
            # PUT url == the exact uploadUrl the init returned (dependent value)
            self.assertEqual(t.calls[1][1], "https://up.li/DOC")
            # real token in EVERY /rest/* Authorization header (live sends it)
            for c in t.calls:
                self.assertEqual(c[2]["Authorization"], "Bearer SENTINEL_LITOKEN")
            # PUT body == the seeded PDF bytes
            self.assertEqual(t.calls[1][3], b"%PDF-1.4 fake pdf bytes")
            # post body references the document URN from the init response
            post_body = json.loads(t.calls[2][3])
            self.assertEqual(post_body["content"]["media"]["id"],
                             "urn:li:document:D1")
            self.assertEqual(post_body["author"], "urn:li:person:REAL")

    def test_happy_multiimage(self):
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            t = publish_api.RecordingTransport(responses=_li_multi_responses())
            res = publish_api.LinkedInAdapter().execute(
                row, package, _li_ctx(post_type="multi-image"), t)
            self.assertEqual(
                res.permalink,
                "https://www.linkedin.com/feed/update/urn:li:share:MULTI")
            self.assertEqual(len(t.calls), 7)
            for i, put_idx in zip((1, 2, 3), (1, 3, 5)):
                self.assertEqual(t.calls[put_idx][1],
                                 "https://up.li/IMG{}".format(i))
                self.assertEqual(t.calls[put_idx][3],
                                 ("PNGBYTES" + str(i)).encode())
            post_body = json.loads(t.calls[6][3])
            self.assertEqual(
                post_body["content"]["multiImage"]["images"],
                [{"id": "urn:li:image:I1"}, {"id": "urn:li:image:I2"},
                 {"id": "urn:li:image:I3"}])

    def test_parity_plan_matches_transport(self):
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            adapter = publish_api.LinkedInAdapter()
            steps = adapter.plan_steps(
                row, package, None, "multi-image",
                publish_api.LINKEDIN_VERSION_DEFAULT)
            t = publish_api.RecordingTransport(responses=_li_multi_responses())
            adapter.execute(row, package, _li_ctx(post_type="multi-image"), t)
            self.assertEqual(len(steps), len(t.calls))
            for pstep, call in zip(steps, t.calls):
                self.assertEqual(pstep["method"], call[0])
            for idx in (0, 2, 4, 6):  # host-anchored steps in both
                self.assertEqual(urlsplit(t.calls[idx][1]).netloc,
                                 "api.linkedin.com")
                self.assertEqual(urlsplit(steps[idx]["url"]).netloc,
                                 "api.linkedin.com")
            for i, put_idx in zip((1, 2, 3), (1, 3, 5)):  # dependent-value proof
                self.assertEqual(steps[put_idx]["url"],
                                 "<li-upload-url-{}>".format(i))
                self.assertEqual(t.calls[put_idx][1],
                                 "https://up.li/IMG{}".format(i))

    def test_unexpected_response_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            adapter = publish_api.LinkedInAdapter()
            # init missing value.uploadUrl -> refusal
            with self.assertRaises(publish_api.AdapterRefusal):
                adapter.execute(row, package, _li_ctx(),
                                publish_api.RecordingTransport(
                                    responses=[{"value": {}}]))
            # post with neither x-restli-id header nor body id -> refusal
            bad = _li_doc_responses()[:2] + [{"nope": "x"}]
            with self.assertRaises(publish_api.AdapterRefusal):
                adapter.execute(row, package, _li_ctx(),
                                publish_api.RecordingTransport(responses=bad))

    def test_token_never_in_plan_steps(self):
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            steps = publish_api.LinkedInAdapter().plan_steps(
                row, package, None, "document",
                publish_api.LINKEDIN_VERSION_DEFAULT)
            self.assertNotIn("SENTINEL_LITOKEN", json.dumps(steps))
            self.assertEqual(steps[0]["headers"]["Authorization"],
                             "Bearer <REDACTED>")


class TestLinkedInPreconditions(unittest.TestCase):
    def _err(self, d, **kw):
        qp = _seed_workspace(d)
        return qp

    def test_manifest_missing_dryrun_and_execute(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            (Path(d) / "content" / _REAL_SLUG / "render"
             / "manifest.json").unlink()
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", queue_path=str(qp))
            self.assertEqual(code, 2)
            self.assertIn("render manifest not found", "\n".join(err))
            self.assertFalse(
                (Path(d) / "content" / "publish-plan.json").exists())
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            (Path(d) / "content" / _REAL_SLUG / "render"
             / "manifest.json").unlink()
            with self.assertRaises(publish_api.AdapterUsageError):
                publish_api.LinkedInAdapter().execute(
                    row, package, _li_ctx(), publish_api.RecordingTransport())

    def test_manifest_no_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            (Path(d) / "content" / _REAL_SLUG / "render"
             / "manifest.json").write_text(json.dumps(
                 {"schema_version": "2", "slug": _REAL_SLUG}))
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", queue_path=str(qp))
            self.assertEqual(code, 2)
            self.assertIn("no 'pdf'", "\n".join(err))
            self.assertFalse(
                (Path(d) / "content" / "publish-plan.json").exists())

    def test_multiimage_zero_attachments(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, attachments=[])
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", queue_path=str(qp),
                linkedin_post_type="multi-image")
            self.assertEqual(code, 2)
            self.assertIn("no attachments to publish (multi-image)",
                          "\n".join(err))

    def test_multiimage_over_twenty(self):
        twentyone = ["content/{}/render/format-{:02d}.png".format(_REAL_SLUG, i)
                     for i in range(1, 22)]
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, attachments=twentyone)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", queue_path=str(qp),
                linkedin_post_type="multi-image")
            self.assertEqual(code, 2)
            self.assertIn("exceeds 20 images", "\n".join(err))

    def test_execute_side_precondition_guards(self):
        # §8.6: each guard fails identically in execute (same self._validate path).
        adapter = publish_api.LinkedInAdapter()
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            # no-pdf manifest
            (Path(d) / "content" / _REAL_SLUG / "render"
             / "manifest.json").write_text(json.dumps(
                 {"schema_version": "2", "slug": _REAL_SLUG}))
            with self.assertRaises(publish_api.AdapterUsageError):
                adapter.execute(row, package, _li_ctx(),
                                publish_api.RecordingTransport())
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            package["attachments"] = []  # 0 attachments, multi-image
            with self.assertRaises(publish_api.AdapterUsageError):
                adapter.execute(row, package, _li_ctx(post_type="multi-image"),
                                publish_api.RecordingTransport())
        with tempfile.TemporaryDirectory() as d:
            row, package = _li_seed(d)
            package["attachments"] = ["a{}.png".format(i) for i in range(21)]
            with self.assertRaises(publish_api.AdapterUsageError):
                adapter.execute(row, package, _li_ctx(post_type="multi-image"),
                                publish_api.RecordingTransport())


class TestLinkedInDriverGeneralization(unittest.TestCase):
    def test_empty_body_tolerated_nonjson_refused(self):
        received = []

        def gen():
            r = yield publish_api._Step("linkedin", "probe", "PUT", "https://up",
                                        {})
            received.append(r)
            return "done"

        class _FakeTransport(object):
            def __init__(self, body):
                self._body = body
                self.calls = []

            def request(self, method, url, headers=None, body=None):
                self.calls.append((method, url, headers, body))
                return publish_api.Response(status=201, headers={},
                                            body=self._body)

        out = publish_api._drive_execute(gen(), _FakeTransport(b""))
        self.assertEqual(out, "done")
        self.assertEqual(received[0], {})  # empty body -> {}, no refusal
        with self.assertRaises(publish_api.AdapterRefusal):
            publish_api._drive_execute(gen(), _FakeTransport(b"<html>"))

    def test_ig_execute_unchanged_after_generalization(self):
        # IG steps carry no upload_path + null payload -> execute_body() is None;
        # the driver generalization leaves IG behavior byte-identical.
        t = publish_api.RecordingTransport(responses=_happy_carousel_responses())
        res = publish_api.InstagramAdapter().execute(
            _IG_ROW, _ig_package(), _ig_ctx(), t)
        self.assertEqual(res.permalink, "https://www.instagram.com/p/ABC/")
        self.assertEqual(len(t.calls), 8)
        for c in t.calls:
            self.assertIsNone(c[3])  # IG sends no request body


class TestLinkedInVersionValidation(unittest.TestCase):
    def test_bad_version_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            for bad in ("bogus", "2025-03", "20250", ""):
                code, out, err = publish_api.run(
                    week=_REAL_WEEK, channel="linkedin", queue_path=str(qp),
                    linkedin_version=bad)
                self.assertEqual(code, 2, msg=repr(bad))
                self.assertIn("YYYYMM", "\n".join(err))

    def test_bad_version_cli(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            r = _run_cli(["--week", _REAL_WEEK, "--channel", "linkedin",
                          "--linkedin-version", "bogus"], cwd=d)
            self.assertEqual(r.returncode, 2)


class TestLinkedInLive(unittest.TestCase):
    def test_live_linkedin_posts_and_transitions(self):
        # Sprint 006 (was test_live_noop_raising_transport): live posts the LI
        # document row via the injected transport and records the URN-derived
        # permalink; no secret reaches stdout/stderr/queue.
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = Path(d) / "li.env"
            ep.write_text("\n".join([
                "LI_PERSON_URN=urn:li:person:SENTINEL",
                "LI_ACCESS_TOKEN=SENTINEL_LITOKEN",
                "PUBLIC_ASSET_BASE_URL=https://assets.example/social-assets",
            ]))
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", mode="live",
                queue_path=str(qp), date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True,
                transport=publish_api.RecordingTransport(
                    responses=_li_doc_responses()))
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn(
                "posted {} linkedin 2026-07-09".format(_REAL_SLUG), out)
            li = [r for r in json.loads(qp.read_text())["rows"]
                  if r["channel"] == "linkedin"][0]
            self.assertEqual(li["state"], "posted")
            self.assertEqual(
                li["permalink"],
                "https://www.linkedin.com/feed/update/urn:li:share:S1")
            self.assertNotIn("SENTINEL", "\n".join(out + err))
            self.assertNotIn("SENTINEL", qp.read_text())

    def test_no_secret_in_dryrun_output(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            r = _run_cli(["--week", _REAL_WEEK, "--channel", "linkedin"], cwd=d)
            self.assertNotIn("SENTINEL_LITOKEN", r.stdout)
            body = (Path(d) / "content" / "publish-plan.json").read_text()
            self.assertNotIn("SENTINEL_LITOKEN", body)
            self.assertIn("Bearer <REDACTED>", body)
            self.assertIn("<LI_PERSON_URN>", body)  # person URN placeholder


# --------------------------------------------------------------------------- #
# Facebook Page adapter (Sprint 005, ROUND-5-GAP, gated). Mocked transport only;
# no real network. --enable-facebook default OFF ⇒ skip-with-notice; ON ⇒ the
# best-documented-guess photos+feed flow (B32).
# --------------------------------------------------------------------------- #
_FB_ROW = {"slug": _REAL_SLUG, "channel": "facebook"}

_FB_DISABLED_NOTE = ("facebook adapter disabled (round-5-gap, unverified); pass "
                     "--enable-facebook to render this row")
_FB_NOTICE = ("NOTICE: facebook row ({}) skipped: facebook adapter disabled; "
              "pass --enable-facebook (round-5-gap, unverified)").format(_REAL_SLUG)


def _fb_mixed_rows():
    """An IG row + a facebook row (both queued, same week) — the Gate 2/3 fixture."""
    return [
        {"slug": _REAL_SLUG, "channel": "instagram", "state": "queued",
         "week": _REAL_WEEK, "schedule_slot": "2026-W28/morning/09:00",
         "package_path": "content/{}/publish/instagram.json".format(_REAL_SLUG),
         "posted_date": None, "permalink": None},
        {"slug": _REAL_SLUG, "channel": "facebook", "state": "queued",
         "week": _REAL_WEEK, "schedule_slot": "2026-W28/morning/10:00",
         "package_path": "content/{}/publish/facebook.json".format(_REAL_SLUG),
         "posted_date": None, "permalink": None},
    ]


def _fb_only_rows():
    return [
        {"slug": _REAL_SLUG, "channel": "facebook", "state": "queued",
         "week": _REAL_WEEK, "schedule_slot": "2026-W28/morning/10:00",
         "package_path": "content/{}/publish/facebook.json".format(_REAL_SLUG),
         "posted_date": None, "permalink": None},
    ]


def _fb_package(attachments=None, caption=None):
    return {
        "channel": "facebook", "slug": _REAL_SLUG,
        "caption": caption if caption is not None else _REAL_CAPTION,
        "attachments": (attachments if attachments is not None
                        else list(_REAL_ATTACHMENTS)),
        "schedule_slot": "2026-W28/morning/10:00",
    }


def _fb_ctx(token="SENTINEL_TOKEN"):
    return {
        "fb_page_id": "PAGEID", "fb_page_token": token,
        "public_asset_base_url": "https://assets.example/social-assets",
    }


def _fb_responses(post_id="POST123"):
    return [{"id": "photo_1"}, {"id": "photo_2"}, {"id": "photo_3"},
            {"id": post_id}]


class TestFacebookDisabledSkip(unittest.TestCase):
    def _plan(self, d):
        return json.loads((Path(d) / "content" / "publish-plan.json").read_text())

    def test_facebook_disabled_skip_dryrun(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_mixed_rows())
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 0, msg="\n".join(err))
            plan = self._plan(d)
            fb = [r for r in plan["rows"] if r["channel"] == "facebook"][0]
            self.assertEqual(fb["steps"], [])
            self.assertEqual(fb["note"], _FB_DISABLED_NOTE)
            # exact skip NOTICE on stderr, once
            self.assertIn(_FB_NOTICE, err)
            self.assertEqual(err.count(_FB_NOTICE), 1)
            # IG row unaffected: still its full 8-step carousel flow
            ig = [r for r in plan["rows"] if r["channel"] == "instagram"][0]
            self.assertEqual(len(ig["steps"]), 8)
            # no "no adapter registered ... facebook" leakage anywhere (§7.4)
            self.assertNotIn("no adapter registered for channel 'facebook'",
                             json.dumps(plan) + "\n".join(err))

    def test_facebook_disabled_no_gap_string_in_stdout_note(self):
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, rows=_fb_mixed_rows(), abs_packages=False)
            r = _run_cli(["--week", _REAL_WEEK], cwd=d)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertIn("round-5-gap", r.stdout)  # disabled note carries it
            self.assertIn(_FB_NOTICE, r.stderr)


class TestFacebookEnabledDryRunFidelity(unittest.TestCase):
    def _plan(self, d):
        return json.loads((Path(d) / "content" / "publish-plan.json").read_text())

    def test_facebook_enabled_dryrun_fidelity(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_only_rows())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, queue_path=str(qp), enable_facebook=True)
            self.assertEqual(code, 0, msg="\n".join(err))
            plan = self._plan(d)
            fb = [r for r in plan["rows"] if r["channel"] == "facebook"][0]
            steps = fb["steps"]
            self.assertEqual(len(steps), 4)  # N+1 = 3 photos + 1 feed
            host = "https://graph.facebook.com"
            methods = [(s["method"], s["url"]) for s in steps]
            self.assertEqual(methods, [
                ("POST", host + "/<FB_PAGE_ID>/photos"),
                ("POST", host + "/<FB_PAGE_ID>/photos"),
                ("POST", host + "/<FB_PAGE_ID>/photos"),
                ("POST", host + "/<FB_PAGE_ID>/feed"),
            ])
            # every step: no headers line, null payload, redacted token (IG-shaped)
            for s in steps:
                self.assertEqual(s["headers"], {})
                self.assertIsNone(s["payload"])
                self.assertEqual(s["params"]["access_token"], "<REDACTED>")
            # photo step 1: exact label + params
            p1 = steps[0]
            self.assertEqual(p1["label"], "FB · upload unpublished photo 1/3")
            self.assertEqual(p1["params"]["published"], "false")
            self.assertEqual(
                p1["params"]["url"],
                "<PUBLIC_ASSET_BASE_URL>/{}/format-01.png".format(_REAL_SLUG))
            # feed step: exact label, attached_media threads fb-photo-id-1..3,
            # caption VERBATIM (real newline preserved in machine JSON, B5)
            feed = steps[3]
            self.assertEqual(feed["label"], "FB · create feed post")
            self.assertEqual(
                feed["params"]["attached_media"],
                '[{"media_fbid":"<fb-photo-id-1>"},'
                '{"media_fbid":"<fb-photo-id-2>"},'
                '{"media_fbid":"<fb-photo-id-3>"}]')
            self.assertEqual(feed["params"]["message"], _REAL_CAPTION)
            self.assertIn("\n", feed["params"]["message"])
            # note: round-5-gap + best-documented-guess + N+1 call count
            self.assertIn("round-5-gap", fb["note"])
            self.assertIn("best-documented-guess", fb["note"])
            self.assertIn("4 HTTP calls", fb["note"])
            # stdout keys SORTED for the photo step params line
            joined = "\n".join(out)
            self.assertIn(
                "params: access_token=<REDACTED>, published=false, "
                "url=<PUBLIC_ASSET_BASE_URL>/{}/format-01.png".format(_REAL_SLUG),
                joined)

    def test_facebook_enabled_concrete_base_url(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_only_rows())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, queue_path=str(qp), enable_facebook=True,
                public_asset_base_url="https://assets.example/social-assets")
            self.assertEqual(code, 0, msg="\n".join(err))
            fb = [r for r in self._plan(d)["rows"]
                  if r["channel"] == "facebook"][0]
            self.assertEqual(
                fb["steps"][0]["params"]["url"],
                "https://assets.example/social-assets/{}/format-01.png".format(
                    _REAL_SLUG))

    def test_facebook_no_invented_version_prefix(self):
        # code + emitted plan carry no /vXX.0/ graph version prefix (Gate 4).
        src = publish_api.__file__
        body = Path(src).read_text()
        self.assertNotRegex(body, r"graph\.facebook\.com/v[0-9]")
        self.assertGreaterEqual(body.count("round-5-gap"), 1)


class TestFacebookAttachmentGuard(unittest.TestCase):
    def test_facebook_zero_attachments_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_only_rows(), attachments=[])
            code, out, err = publish_api.run(
                week=_REAL_WEEK, queue_path=str(qp), enable_facebook=True)
            self.assertEqual(code, 2)
            self.assertIn("no attachments", "\n".join(err))
            # NO plan written on the usage error
            self.assertFalse(
                (Path(d) / "content" / "publish-plan.json").exists())

    def test_facebook_execute_zero_usage_error(self):
        with self.assertRaises(publish_api.AdapterUsageError):
            publish_api.FacebookAdapter().execute(
                _FB_ROW, _fb_package(attachments=[]), _fb_ctx(),
                publish_api.RecordingTransport())


class TestFacebookExecute(unittest.TestCase):
    def test_facebook_execute_happy_path(self):
        adapter = publish_api.FacebookAdapter()
        t = publish_api.RecordingTransport(responses=_fb_responses())
        res = adapter.execute(_FB_ROW, _fb_package(), _fb_ctx(), t)
        self.assertIsInstance(res, publish_api._FbResult)
        self.assertEqual(res.post_id, "POST123")
        self.assertEqual(res.permalink, "https://www.facebook.com/POST123")
        # N photos + 1 feed in order, all POST
        self.assertEqual(len(t.calls), 4)
        self.assertEqual([c[0] for c in t.calls],
                         ["POST", "POST", "POST", "POST"])
        for c in t.calls[:3]:
            self.assertIn("/PAGEID/photos", urlsplit(c[1]).path)
        self.assertIn("/PAGEID/feed", urlsplit(t.calls[3][1]).path)
        # real token sent on EVERY execute call (proves live sends it)
        for c in t.calls:
            self.assertIn("access_token=SENTINEL_TOKEN", c[1])
        # feed attached_media carries the REAL photo ids returned by transport
        feed_url = t.calls[3][1]
        self.assertIn("photo_1", feed_url)
        self.assertIn("photo_2", feed_url)
        self.assertIn("photo_3", feed_url)
        # FB sends no request body (params are query-string, like IG)
        for c in t.calls:
            self.assertIsNone(c[3])

    def test_facebook_parity_plan_matches_transport(self):
        adapter = publish_api.FacebookAdapter()
        steps = adapter.plan_steps(_FB_ROW, _fb_package(), None)
        t = publish_api.RecordingTransport(responses=_fb_responses())
        adapter.execute(_FB_ROW, _fb_package(), _fb_ctx(), t)
        self.assertEqual(len(steps), len(t.calls))
        subs = {"<FB_PAGE_ID>": "PAGEID"}
        for s, c in zip(steps, t.calls):
            self.assertEqual(s["method"], c[0])
            plan_path = urlsplit(s["url"]).path
            for k, v in subs.items():
                plan_path = plan_path.replace(k, v)
            self.assertEqual(plan_path, urlsplit(c[1]).path)

    def test_facebook_unexpected_response_refusal(self):
        adapter = publish_api.FacebookAdapter()
        # feed response missing "id" → AdapterRefusal
        bad = [{"id": "photo_1"}, {"id": "photo_2"}, {"id": "photo_3"}, {}]
        t = publish_api.RecordingTransport(responses=bad)
        with self.assertRaises(publish_api.AdapterRefusal):
            adapter.execute(_FB_ROW, _fb_package(), _fb_ctx(), t)
        # photo response missing "id" also refuses
        bad2 = [{"nope": 1}]
        with self.assertRaises(publish_api.AdapterRefusal):
            adapter.execute(_FB_ROW, _fb_package(), _fb_ctx(),
                            publish_api.RecordingTransport(responses=bad2))

    def test_facebook_token_never_in_plan(self):
        adapter = publish_api.FacebookAdapter()
        steps = adapter.plan_steps(_FB_ROW, _fb_package(), None)
        self.assertNotIn("SENTINEL_TOKEN", json.dumps(steps))
        for s in steps:
            self.assertEqual(s["params"]["access_token"], "<REDACTED>")


class TestFacebookSecretsAndDeterminism(unittest.TestCase):
    def test_facebook_no_secret_in_output(self):
        # dry-run (flag ON) never carries a token; sentinel absent, redaction shown
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, rows=_fb_only_rows(), abs_packages=False)
            r = _run_cli(["--week", _REAL_WEEK, "--enable-facebook",
                          "--public-asset-base-url",
                          "https://assets.example/social-assets"], cwd=d)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            body = (Path(d) / "content" / "publish-plan.json").read_text()
            self.assertNotIn("SENTINEL_TOKEN", r.stdout)
            self.assertNotIn("SENTINEL_TOKEN", body)
            self.assertIn("<REDACTED>", body)
            self.assertIn("best-documented-guess", body)
        # execute with a RecordingTransport + sentinel token: the plan output
        # (built separately) never contains the token used at execute time
        adapter = publish_api.FacebookAdapter()
        t = publish_api.RecordingTransport(responses=_fb_responses())
        adapter.execute(_FB_ROW, _fb_package(), _fb_ctx(token="LEAK_ME"), t)
        steps = adapter.plan_steps(_FB_ROW, _fb_package(), None)
        self.assertNotIn("LEAK_ME", json.dumps(steps))

    def test_facebook_determinism_flag_on(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_only_rows())
            publish_api.run(week=_REAL_WEEK, queue_path=str(qp),
                            enable_facebook=True)
            first = (Path(d) / "content" / "publish-plan.json").read_bytes()
            publish_api.run(week=_REAL_WEEK, queue_path=str(qp),
                            enable_facebook=True)
            second = (Path(d) / "content" / "publish-plan.json").read_bytes()
            self.assertEqual(first, second)


class TestFacebookNonRegression(unittest.TestCase):
    def test_facebook_non_regression_real_asset(self):
        # DEFAULT dry-run over the real 2-row seed (no facebook in scope) must be
        # byte-identical to the Sprint-004 golden (adding facebook to _ADAPTERS +
        # threading the flag must NOT perturb the IG/LI rows).
        golden = (_TESTS_DIR / "golden" /
                  "publish-plan-sprint004-2026-W28.json").read_bytes()
        with tempfile.TemporaryDirectory() as d:
            _seed_workspace(d, abs_packages=False)
            r = _run_cli(["--week", _REAL_WEEK], cwd=d)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            got = (Path(d) / "content" / "publish-plan.json").read_bytes()
        self.assertEqual(got, golden)


class TestFacebookLive(unittest.TestCase):
    def test_facebook_live_posts_flag_on(self):
        # Sprint 006 (was test_facebook_live_noop_flag_on): with the flag ON the
        # round-5-gap FB row now posts via execute + transitions; the adapter's
        # round-5-gap label is preserved (note() unchanged). No plan written.
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_only_rows())
            ep = Path(d) / "fb.env"
            ep.write_text("\n".join([
                "FB_PAGE_ID=PAGEID_SENTINEL",
                "FB_PAGE_TOKEN=SENTINEL_FBTOKEN",
                "PUBLIC_ASSET_BASE_URL=https://assets.example/social-assets",
            ]))
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep), enable_facebook=True,
                i_have_verified_dry_run=True,
                transport=publish_api.RecordingTransport(
                    responses=_fb_responses()))
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn(
                "posted {} facebook 2026-07-09".format(_REAL_SLUG), out)
            fb = json.loads(qp.read_text())["rows"][0]
            self.assertEqual(fb["state"], "posted")
            self.assertEqual(fb["permalink"], "https://www.facebook.com/POST123")
            self.assertNotIn("SENTINEL", "\n".join(out + err))
            self.assertNotIn("SENTINEL", qp.read_text())
            # round-5-gap label preserved on the adapter note (source unchanged)
            self.assertIn("round-5-gap", publish_api.FacebookAdapter().note(4))
            self.assertFalse(
                (Path(d) / "content" / "publish-plan.json").exists())

    def test_facebook_live_noop_flag_off_skips(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_only_rows())
            before = qp.read_bytes()
            ep = Path(d) / "fb.env"
            # flag OFF ⇒ gate needs NO FB tokens (facebook is skipped, not posted)
            ep.write_text(
                "PUBLIC_ASSET_BASE_URL=https://assets.example/social-assets\n")
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep), enable_facebook=False,
                i_have_verified_dry_run=True,
                transport=publish_api.RaisingTransport())
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn(_FB_NOTICE, err)
            self.assertEqual(qp.read_bytes(), before)


# --------------------------------------------------------------------------- #
# Sprint 006 — live transition, no-regress, day-cap, end-to-end. Every live test
# injects a RecordingTransport (canned) or a RaisingTransport; NO real socket.
# --------------------------------------------------------------------------- #
def _seed_live_bytes(d, slug=_REAL_SLUG):
    """Write the local upload bytes the live LinkedIn flows read (contract s4.4):
    the document PDF (carousel.pdf) + the 3 carousel PNGs. IG/FB upload by URL and
    need no local bytes; this satisfies the up-front byte precondition."""
    render = Path(d) / "content" / slug / "render"
    render.mkdir(parents=True, exist_ok=True)
    (render / "carousel.pdf").write_bytes(b"%PDF-1.4 fake pdf bytes")
    for i in (1, 2, 3):
        (render / "format-{:02d}.png".format(i)).write_bytes(
            ("PNGBYTES" + str(i)).encode())


def _two_row_live_responses():
    """Canned responses for the default IG+LI seed in (slug, channel) order:
    instagram (8 calls) then linkedin document (3 calls) = 11."""
    return _happy_carousel_responses() + _li_doc_responses()


def _live_env(d, **overrides):
    """Write a full live .env (all channels' tokens + base URL). ``k=None`` in
    ``overrides`` drops that key entirely (to exercise a missing-token gate)."""
    base = {
        "IG_USER_ID": "IGID", "IG_ACCESS_TOKEN": "IGTOK",
        "LI_PERSON_URN": "urn:li:person:X", "LI_ACCESS_TOKEN": "LITOK",
        "FB_PAGE_ID": "PAGEID", "FB_PAGE_TOKEN": "FBTOK",
        "PUBLIC_ASSET_BASE_URL": "https://assets.example/social-assets",
    }
    base.update(overrides)
    ep = Path(d) / "live.env"
    ep.write_text("\n".join(
        "{}={}".format(k, v) for k, v in base.items() if v is not None))
    return ep


def _live_row(channel, state="queued", posted_date=None, permalink=None,
              slug=_REAL_SLUG):
    return {
        "slug": slug, "channel": channel, "state": state, "week": _REAL_WEEK,
        "schedule_slot": "2026-W28/morning/09:00",
        "package_path": "content/{}/publish/{}.json".format(slug, channel),
        "posted_date": posted_date, "permalink": permalink,
    }


class TestSprint006LiveTransition(unittest.TestCase):
    # 1a
    def test_live_targeted_already_posted_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            rows = [_live_row("instagram", state="posted",
                              posted_date="2026-07-01",
                              permalink="https://www.instagram.com/p/OLD/"),
                    _live_row("linkedin")]
            qp = _seed_workspace(d, rows=rows)
            _seed_live_bytes(d)
            before = qp.read_bytes()
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(responses=_two_row_live_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, slug=_REAL_SLUG, channel="instagram",
                mode="live", queue_path=str(qp), date="2026-07-09",
                env_path=str(ep), i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 1)
            self.assertIn(
                "REFUSED ({}, instagram): row is already posted; refusing to "
                "re-post (no double-post)".format(_REAL_SLUG), "\n".join(err))
            self.assertEqual(qp.read_bytes(), before)   # byte-identical
            self.assertEqual(len(rec.calls), 0)         # zero network

    # 1b
    def test_live_rerun_fully_posted_week_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            rows = [_live_row("instagram", state="posted",
                              posted_date="2026-07-09",
                              permalink="https://i/1"),
                    _live_row("linkedin", state="posted",
                              posted_date="2026-07-09",
                              permalink="https://l/1")]
            qp = _seed_workspace(d, rows=rows)
            before = qp.read_bytes()
            ep = _live_env(d)
            rec = publish_api.RecordingTransport()
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn("nothing queued for {}".format(_REAL_WEEK),
                          "\n".join(err))
            self.assertEqual(qp.read_bytes(), before)   # no re-post / regression
            self.assertEqual(len(rec.calls), 0)

    # 2
    def test_live_happy_path_ig_li_transition(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(responses=_two_row_live_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn(
                "posted {} instagram 2026-07-09".format(_REAL_SLUG), out)
            self.assertIn(
                "posted {} linkedin 2026-07-09".format(_REAL_SLUG), out)
            rowmap = {r["channel"]: r
                      for r in json.loads(qp.read_text())["rows"]}
            for ch in ("instagram", "linkedin"):
                self.assertEqual(rowmap[ch]["state"], "posted")
                self.assertEqual(rowmap[ch]["posted_date"], "2026-07-09")
            # transport call order: IG flow (8) then LI document flow (3)
            methods = [c[0] for c in rec.calls]
            self.assertEqual(methods, [
                "GET", "POST", "POST", "POST", "POST", "GET", "POST", "GET",
                "POST", "PUT", "POST"])
            # live writes the queue only
            self.assertFalse(
                (Path(d) / "content" / "publish-plan.json").exists())

    # 3
    def test_live_permalink_recorded_from_response(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(responses=_two_row_live_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            rowmap = {r["channel"]: r
                      for r in json.loads(qp.read_text())["rows"]}
            self.assertEqual(rowmap["instagram"]["permalink"],
                             "https://www.instagram.com/p/ABC/")
            self.assertEqual(
                rowmap["linkedin"]["permalink"],
                "https://www.linkedin.com/feed/update/urn:li:share:S1")

    # 4
    def test_live_daycap_breach_refusal_prior_stand(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)          # IG + LI both queued
            _seed_live_bytes(d)
            ep = _live_env(d)
            # only IG responses needed — LI is refused by the cap before execute
            rec = publish_api.RecordingTransport(
                responses=_happy_carousel_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep), max_per_day=1,
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 1)
            self.assertIn("(day-cap)", "\n".join(err))
            rowmap = {r["channel"]: r
                      for r in json.loads(qp.read_text())["rows"]}
            self.assertEqual(rowmap["instagram"]["state"], "posted")  # prior stand
            self.assertEqual(rowmap["linkedin"]["state"], "queued")   # breaching
            self.assertEqual(len(rec.calls), 8)  # only IG hit the wire

    # 5
    def test_live_daycap_counts_existing_posted_today(self):
        with tempfile.TemporaryDirectory() as d:
            rows = [_live_row("instagram", state="posted",
                              posted_date="2026-07-09", permalink="https://i/1"),
                    _live_row("linkedin")]
            qp = _seed_workspace(d, rows=rows)
            _seed_live_bytes(d)
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(responses=_li_doc_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep), max_per_day=1,
                i_have_verified_dry_run=True, transport=rec)
            # baseline already 1 (IG posted today) => the queued LI breaches
            self.assertEqual(code, 1)
            self.assertIn("(day-cap)", "\n".join(err))
            li = [r for r in json.loads(qp.read_text())["rows"]
                  if r["channel"] == "linkedin"][0]
            self.assertEqual(li["state"], "queued")
            self.assertEqual(len(rec.calls), 0)

    # 6
    def test_live_adapter_refusal_container_error(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            before_ig = [r for r in json.loads(qp.read_text())["rows"]
                         if r["channel"] == "instagram"][0]
            ep = _live_env(d)
            resp = _happy_carousel_responses()[:5] + [{"status_code": "ERROR"}]
            rec = publish_api.RecordingTransport(responses=resp)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="instagram", mode="live",
                queue_path=str(qp), date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 1)
            joined = "\n".join(err)
            self.assertIn("REFUSED ({}, instagram)".format(_REAL_SLUG), joined)
            self.assertIn("ERROR", joined)
            ig = [r for r in json.loads(qp.read_text())["rows"]
                  if r["channel"] == "instagram"][0]
            self.assertEqual(ig["state"], "queued")   # not transitioned
            self.assertEqual(ig, before_ig)

    # 7
    def test_live_adapter_refusal_rate_limit(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(
                responses=[{"data": [{"quota_usage": 50, "quota_total": 50}]}])
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="instagram", mode="live",
                queue_path=str(qp), date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 1)
            self.assertIn("rate limit", "\n".join(err).lower())
            ig = [r for r in json.loads(qp.read_text())["rows"]
                  if r["channel"] == "instagram"][0]
            self.assertEqual(ig["state"], "queued")

    # 8
    def test_live_incremental_write_prior_posts_persist(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)          # IG then LI
            _seed_live_bytes(d)
            ep = _live_env(d)
            # IG posts (8 canned); LI's first (initialize) gets a bad shape -> refuse
            resp = _happy_carousel_responses() + [{"nope": 1}]
            rec = publish_api.RecordingTransport(responses=resp)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 1)
            self.assertIn("REFUSED ({}, linkedin)".format(_REAL_SLUG),
                          "\n".join(err))
            rowmap = {r["channel"]: r
                      for r in json.loads(qp.read_text())["rows"]}
            self.assertEqual(rowmap["instagram"]["state"], "posted")  # persisted
            self.assertEqual(rowmap["linkedin"]["state"], "queued")

    # 9
    def test_live_no_plan_written(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(responses=_two_row_live_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertFalse(
                (Path(d) / "content" / "publish-plan.json").exists())

    # 10
    def test_live_no_secret_in_queue_or_output(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            _seed_live_bytes(d)
            ep = _live_env(d, IG_ACCESS_TOKEN="SENTINEL_IGSECRET",
                           LI_ACCESS_TOKEN="SENTINEL_LISECRET")
            rec = publish_api.RecordingTransport(responses=_two_row_live_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            blob = "\n".join(out + err) + qp.read_text()
            self.assertNotIn("SENTINEL_IGSECRET", blob)
            self.assertNotIn("SENTINEL_LISECRET", blob)

    # 11
    def test_live_missing_upload_bytes_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)          # manifest written, but NO carousel.pdf
            before = qp.read_bytes()
            ep = _live_env(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="linkedin", mode="live",
                queue_path=str(qp), date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True,
                transport=publish_api.RaisingTransport())
            self.assertEqual(code, 2)
            self.assertIn("local upload file missing", "\n".join(err))
            self.assertEqual(qp.read_bytes(), before)  # no queue write

    # 12
    def test_live_facebook_enabled_posts(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d, rows=_fb_only_rows())
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(responses=_fb_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep), enable_facebook=True,
                max_per_day=1, i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            fb = json.loads(qp.read_text())["rows"][0]
            self.assertEqual(fb["state"], "posted")
            self.assertEqual(fb["permalink"], "https://www.facebook.com/POST123")
            self.assertIn("round-5-gap", publish_api.FacebookAdapter().note(4))

    # 13
    def test_live_facebook_disabled_skipped_no_count(self):
        with tempfile.TemporaryDirectory() as d:
            # facebook < instagram in (slug, channel) order => FB processed first;
            # skipped WITHOUT consuming cap, so IG still posts under max_per_day=1.
            qp = _seed_workspace(d, rows=_fb_mixed_rows())
            ep = _live_env(d)
            rec = publish_api.RecordingTransport(
                responses=_happy_carousel_responses())
            code, out, err = publish_api.run(
                week=_REAL_WEEK, mode="live", queue_path=str(qp),
                date="2026-07-09", env_path=str(ep), enable_facebook=False,
                max_per_day=1, i_have_verified_dry_run=True, transport=rec)
            self.assertEqual(code, 0, msg="\n".join(err))
            self.assertIn(_FB_NOTICE, err)
            rowmap = {r["channel"]: r
                      for r in json.loads(qp.read_text())["rows"]}
            self.assertEqual(rowmap["facebook"]["state"], "queued")   # skipped
            self.assertEqual(rowmap["instagram"]["state"], "posted")  # still posts

    # 14
    def test_live_gate_still_exit2(self):
        for missing in ("env", "base", "ack", "date"):
            with tempfile.TemporaryDirectory() as d:
                qp = _seed_workspace(d)
                before = qp.read_bytes()
                kwargs = dict(
                    week=_REAL_WEEK, mode="live", queue_path=str(qp),
                    date="2026-07-09", i_have_verified_dry_run=True,
                    transport=publish_api.RaisingTransport())
                if missing == "env":
                    kwargs["env_path"] = str(Path(d) / "nope.env")
                elif missing == "base":
                    kwargs["env_path"] = str(_live_env(d, PUBLIC_ASSET_BASE_URL=""))
                elif missing == "ack":
                    kwargs["env_path"] = str(_live_env(d))
                    kwargs["i_have_verified_dry_run"] = False
                else:  # date
                    kwargs["env_path"] = str(_live_env(d))
                    kwargs["date"] = None
                code, out, err = publish_api.run(**kwargs)
                self.assertEqual(code, 2, msg="{}: {}".format(missing, err))
                self.assertEqual(qp.read_bytes(), before)
                self.assertFalse(
                    (Path(d) / "content" / "publish-plan.json").exists())

    # 15
    def test_live_usage_error_prevalidation_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            eleven = ["content/{}/render/format-{:02d}.png".format(_REAL_SLUG, i)
                      for i in range(1, 12)]
            qp = _seed_workspace(d, attachments=eleven)
            before = qp.read_bytes()
            ep = _live_env(d)
            code, out, err = publish_api.run(
                week=_REAL_WEEK, channel="instagram", mode="live",
                queue_path=str(qp), date="2026-07-09", env_path=str(ep),
                i_have_verified_dry_run=True,
                transport=publish_api.RaisingTransport())
            self.assertEqual(code, 2)
            self.assertIn("exceeds 10 children", "\n".join(err))
            self.assertEqual(qp.read_bytes(), before)  # nothing posted/written

    # 16
    def test_real_asset_dryrun_two_rows_fidelity(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            code, out, err = publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            self.assertEqual(code, 0, msg="\n".join(err))
            plan = json.loads(
                (Path(d) / "content" / "publish-plan.json").read_text())
            chans = [(r["slug"], r["channel"]) for r in plan["rows"]]
            self.assertEqual(chans, [(_REAL_SLUG, "instagram"),
                                     (_REAL_SLUG, "linkedin")])
            ig = [r for r in plan["rows"] if r["channel"] == "instagram"][0]
            li = [r for r in plan["rows"] if r["channel"] == "linkedin"][0]
            self.assertEqual(len(ig["steps"]), 8)   # container flow
            self.assertEqual(len(li["steps"]), 3)   # document flow
            # caption + UTM link verbatim in the IG parent step
            parent = ig["steps"][4]
            self.assertEqual(parent["params"]["caption"], _REAL_CAPTION)
            self.assertIn("utm_source=instagram", parent["params"]["caption"])
            # dependent-value placeholders present, secrets redacted
            self.assertEqual(parent["params"]["access_token"], "<REDACTED>")
            self.assertIn("<ig-child-container-id-1>",
                          parent["params"]["children"])

    # 17
    def test_real_asset_dryrun_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            first = (Path(d) / "content" / "publish-plan.json").read_bytes()
            publish_api.run(week=_REAL_WEEK, queue_path=str(qp))
            second = (Path(d) / "content" / "publish-plan.json").read_bytes()
            self.assertEqual(first, second)

    # 18
    def test_dryrun_raising_transport_still_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            qp = _seed_workspace(d)
            before = qp.read_bytes()
            code, out, err = publish_api.run(
                week=_REAL_WEEK, queue_path=str(qp),
                transport=publish_api.RaisingTransport())
            self.assertEqual(code, 0, msg="\n".join(err))
            plan = json.loads(
                (Path(d) / "content" / "publish-plan.json").read_text())
            self.assertEqual(len(plan["rows"]), 2)      # full plan emitted
            self.assertEqual(qp.read_bytes(), before)   # no queue write

    # 19
    def test_live_ast_single_urlopen_site(self):
        tree = ast.parse(_PUBLISH.read_text())
        refs = [n for n in ast.walk(tree)
                if (isinstance(n, ast.Attribute) and n.attr == "urlopen")
                or (isinstance(n, ast.Name) and n.id == "urlopen")]
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and n.func in refs]
        self.assertEqual(len(calls), 1,
                         "exactly one urlopen call site after Sprint 006")


# --------------------------------------------------------------------------- #
# Import safety.
# --------------------------------------------------------------------------- #
class TestImportSafety(unittest.TestCase):
    def test_import_is_silent(self):
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'tools/marketing-loops'); "
             "import publish_api"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")


if __name__ == "__main__":
    unittest.main()
