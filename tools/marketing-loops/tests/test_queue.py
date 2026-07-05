"""Unit tests for the Sprint 002 QUEUE schema + helpers (contract s3.2 / s5.4).

Covers the schema constants, empty/load, deterministic serialization + ordering,
idempotent merge, and the no-regress rule for a pre-existing posted row.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _TESTS_DIR.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import queue  # noqa: E402
import utm    # noqa: E402


class TestSchemaConstants(unittest.TestCase):
    def test_schema_version_is_one(self):
        self.assertEqual(queue.SCHEMA_VERSION, "1")

    def test_state_enum(self):
        self.assertEqual(queue.STATES, frozenset({"queued", "posted"}))

    def test_valid_channels_from_shared_map(self):
        self.assertEqual(queue.VALID_CHANNELS,
                         frozenset(utm.CHANNEL_SOURCE_MAP.keys()))

    def test_empty_queue_shape(self):
        self.assertEqual(queue.empty_queue(),
                         {"schema_version": "1", "rows": []})


class TestRow(unittest.TestCase):
    def test_new_row_all_lifecycle_fields_null(self):
        r = queue.new_row("2026-07-03-x", "instagram", "2026-W27")
        self.assertEqual(r["state"], "queued")
        self.assertEqual(r["week"], "2026-W27")
        for k in ("schedule_slot", "package_path", "posted_date", "permalink"):
            self.assertIsNone(r[k])

    def test_new_row_rejects_unknown_channel(self):
        with self.assertRaises(ValueError):
            queue.new_row("s", "twitter", "2026-W27")


class TestSerialization(unittest.TestCase):
    def test_deterministic_and_sorted(self):
        q = queue.empty_queue()
        rows = [
            queue.new_row("b-slug", "youtube", "2026-W27"),
            queue.new_row("a-slug", "linkedin", "2026-W27"),
            queue.new_row("a-slug", "instagram", "2026-W27"),
        ]
        q, _ = queue.merge_rows(q, rows)
        out = queue.dumps(q)
        self.assertTrue(out.endswith("\n"))
        self.assertFalse(out.endswith("\n\n"))
        data = json.loads(out)
        order = [(r["slug"], r["channel"]) for r in data["rows"]]
        self.assertEqual(order, [("a-slug", "instagram"),
                                 ("a-slug", "linkedin"),
                                 ("b-slug", "youtube")])
        # dumps twice -> byte identical
        self.assertEqual(queue.dumps(q), out)


class TestMergeIdempotentAndNoRegress(unittest.TestCase):
    def test_merge_dedups_pair(self):
        q = queue.empty_queue()
        row = queue.new_row("s", "instagram", "2026-W27")
        q, _ = queue.merge_rows(q, [row])
        q, actions = queue.merge_rows(q, [row])
        self.assertEqual(len(q["rows"]), 1)
        self.assertEqual(actions, [("queued", "s", "instagram")])

    def test_no_regress_posted_row(self):
        q = queue.empty_queue()
        posted = queue.new_row("s", "instagram", "2026-W27")
        posted["state"] = "posted"
        posted["posted_date"] = "2026-07-04"
        posted["permalink"] = "https://example.com/p/1"
        q["rows"].append(posted)
        # re-enqueue instagram + a new youtube row
        incoming = [queue.new_row("s", "instagram", "2026-W27"),
                    queue.new_row("s", "youtube", "2026-W27")]
        q, actions = queue.merge_rows(q, incoming)
        by = {(r["slug"], r["channel"]): r for r in q["rows"]}
        ig = by[("s", "instagram")]
        self.assertEqual(ig["state"], "posted")
        self.assertEqual(ig["posted_date"], "2026-07-04")
        self.assertEqual(ig["permalink"], "https://example.com/p/1")
        self.assertEqual(by[("s", "youtube")]["state"], "queued")
        self.assertIn(("kept-posted", "s", "instagram"), actions)
        self.assertIn(("queued", "s", "youtube"), actions)

    def test_merge_does_not_mutate_input(self):
        q = queue.empty_queue()
        q["rows"].append(queue.new_row("s", "instagram", "2026-W27"))
        original_len = len(q["rows"])
        queue.merge_rows(q, [queue.new_row("s", "youtube", "2026-W27")])
        self.assertEqual(len(q["rows"]), original_len)  # input untouched


class TestLoad(unittest.TestCase):
    def test_missing_file_is_empty_queue(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(queue.load_queue(Path(d) / "nope.json"),
                             queue.empty_queue())

    def test_load_rows_empty_ok(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "q.json"
            p.write_text('{"schema_version":"1","rows":[]}\n')
            self.assertEqual(queue.load_queue(p)["rows"], [])

    def test_load_rejects_garbage(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "q.json"
            p.write_text("not json")
            with self.assertRaises(ValueError):
                queue.load_queue(p)

    def test_write_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "q.json"
            q = queue.empty_queue()
            q, _ = queue.merge_rows(q, [queue.new_row("s", "instagram", "2026-W27")])
            queue.write_queue(p, q)
            self.assertEqual(queue.load_queue(p)["rows"], q["rows"])


if __name__ == "__main__":
    unittest.main()
