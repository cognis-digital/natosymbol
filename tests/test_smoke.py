"""Smoke tests for NATOSYMBOL — stdlib unittest, no network."""

import io
import os
import sys
import json
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from natosymbol import (  # noqa: E402
    TOOL_NAME,
    TOOL_VERSION,
    build_sidc,
    parse_sidc,
    validate_sidc,
    describe_sidc,
    SIDCError,
)
from natosymbol.cli import main  # noqa: E402


class TestCore(unittest.TestCase):
    def test_exports(self):
        self.assertEqual(TOOL_NAME, "natosymbol")
        self.assertTrue(TOOL_VERSION)

    def test_build_roundtrip(self):
        code = build_sidc(affiliation="F", battle_dimension="G", function_id="UCI---", country="US", order_of_battle="G")
        self.assertEqual(len(code), 15)
        self.assertEqual(code, "SFGPUCI-----USG")
        parsed = parse_sidc(code)
        self.assertEqual(parsed.affiliation, "F")
        self.assertEqual(parsed.battle_dimension, "G")
        self.assertEqual(parsed.function_id, "UCI---")
        self.assertEqual(parsed.country, "US")

    def test_validate_good(self):
        s = validate_sidc("SFGPUCI-----USG")
        self.assertEqual(s.affiliation, "F")

    def test_validate_bad_length(self):
        with self.assertRaises(SIDCError):
            validate_sidc("SFGPUCI----USG")  # 14 chars

    def test_validate_bad_affiliation(self):
        with self.assertRaises(SIDCError):
            validate_sidc("SQGPUCI-----USG")

    def test_describe_labels(self):
        d = describe_sidc("SFGPUCI-----USG")
        self.assertEqual(d["affiliation"]["label"], "Friend")
        self.assertEqual(d["battle_dimension"]["label"], "Ground")
        self.assertEqual(d["function_id"]["label"], "Infantry")

    def test_build_rejects_bad_field(self):
        with self.assertRaises(SIDCError):
            build_sidc(function_id="TOOLONGXX")


class TestCLI(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_validate_ok(self):
        rc, out = self._run(["validate", "SFGPUCI-----USG"])
        self.assertEqual(rc, 0)

    def test_validate_fail_nonzero(self):
        rc, out = self._run(["validate", "SQGPUCI-----USG"])
        self.assertEqual(rc, 1)

    def test_describe_json(self):
        rc, out = self._run(["--format", "json", "describe", "SFGPUCI-----USG"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["code"], "SFGPUCI-----USG")
        self.assertEqual(data["affiliation"]["label"], "Friend")

    def test_build_cli(self):
        rc, out = self._run(["build", "--affiliation", "H", "--function", "UCR---", "--country", "US"])
        self.assertEqual(rc, 0)
        self.assertIn("SHG", out)

    def test_batch(self):
        with tempfile.NamedTemporaryFile("w", suffix=".sidc", delete=False, encoding="utf-8") as fh:
            fh.write("SFGPUCI-----USG\n# comment\nSHGPUCR-----RUG\n")
            path = fh.name
        try:
            rc, out = self._run(["batch", path])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(path)

    def test_batch_detects_invalid(self):
        with tempfile.NamedTemporaryFile("w", suffix=".sidc", delete=False, encoding="utf-8") as fh:
            fh.write("SFGPUCI-----USG\nSQGPUCI-----USG\n")
            path = fh.name
        try:
            rc, out = self._run(["batch", path])
            self.assertEqual(rc, 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
