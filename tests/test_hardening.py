"""Hardening tests — edge cases, bad input, error paths."""

from __future__ import annotations

import importlib
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from natosymbol.cli import main  # noqa: E402
from natosymbol.core import (  # noqa: E402
    SIDCError,
    build_sidc,
    describe_sidc,
    parse_sidc,
    validate_sidc,
)


# ---------------------------------------------------------------------------
# core.py hardening
# ---------------------------------------------------------------------------


class TestCoreEdgeCases(unittest.TestCase):
    def test_parse_sidc_non_string_raises(self):
        """Non-string input must raise SIDCError, not AttributeError."""
        with self.assertRaises(SIDCError):
            parse_sidc(None)  # type: ignore[arg-type]

    def test_parse_sidc_integer_raises(self):
        with self.assertRaises(SIDCError):
            parse_sidc(12345)  # type: ignore[arg-type]

    def test_parse_sidc_empty_string_raises(self):
        with self.assertRaises(SIDCError):
            parse_sidc("")

    def test_validate_sidc_whitespace_only_raises(self):
        """Whitespace-only string collapses to '' after strip — must raise."""
        with self.assertRaises(SIDCError):
            validate_sidc("               ")

    def test_describe_sidc_non_string_raises(self):
        """describe_sidc with non-string must raise SIDCError cleanly."""
        with self.assertRaises(SIDCError):
            describe_sidc(None)  # type: ignore[arg-type]

    def test_describe_sidc_unmapped_function_id(self):
        """An unmapped function ID should fall back to a label, not crash."""
        # Build a valid SIDC with a function ID not in FUNCTION_IDS
        code = build_sidc(
            coding_scheme="S",
            affiliation="U",
            battle_dimension="G",
            status="P",
            function_id="XYZ---",
        )
        d = describe_sidc(code)
        self.assertIn("label", d["function_id"])
        self.assertIsInstance(d["function_id"]["label"], str)

    def test_build_sidc_none_fields_use_defaults(self):
        """None passed for optional fields must be treated as empty / pad."""
        # _norm() uses (value or "") so None is safe; this should raise only
        # because the resulting coding_scheme '-' is not in CODING_SCHEMES.
        with self.assertRaises(SIDCError):
            build_sidc(coding_scheme=None)  # type: ignore[arg-type]

    def test_validate_multiple_errors_reported_together(self):
        """A SIDC with multiple bad fields should report all in one error."""
        # Bad affiliation (Q) and bad status (Z)
        bad = "SQGZUCI-----USG"
        with self.assertRaises(SIDCError) as ctx:
            validate_sidc(bad)
        msg = str(ctx.exception)
        self.assertIn("affiliation", msg)

    def test_describe_sidc_unspecified_country(self):
        code = build_sidc(country="--")
        d = describe_sidc(code)
        self.assertEqual(d["country"]["label"], "Unspecified")

    def test_parse_sidc_strips_whitespace(self):
        """Leading/trailing whitespace in a SIDC string is stripped."""
        s = parse_sidc("  SFGPUCI-----USG  ")
        self.assertEqual(s.code, "SFGPUCI-----USG")


# ---------------------------------------------------------------------------
# cli.py hardening — batch subcommand
# ---------------------------------------------------------------------------


class TestCLIBatch(unittest.TestCase):
    def _run(self, argv):
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = main(argv)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def test_batch_missing_file_returns_nonzero(self):
        """batch with a non-existent file must exit non-zero with a message."""
        rc, _, err = self._run(["batch", "/nonexistent/path/file.sidc"])
        self.assertNotEqual(rc, 0)
        self.assertIn("error", err.lower())

    def test_batch_empty_file_returns_nonzero(self):
        """batch with a totally empty file must exit non-zero."""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".sidc", delete=False, encoding="utf-8"
        ) as fh:
            path = fh.name  # write nothing
        try:
            rc, _, err = self._run(["batch", path])
            self.assertNotEqual(rc, 0)
        finally:
            os.unlink(path)

    def test_batch_comments_only_returns_nonzero(self):
        """batch with only comments (no real SIDCs) must exit non-zero."""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".sidc", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("# this is a comment\n# another comment\n\n")
            path = fh.name
        try:
            rc, _, err = self._run(["batch", path])
            self.assertNotEqual(rc, 0)
        finally:
            os.unlink(path)

    def test_batch_json_format_invalid(self):
        """batch --format json with an invalid SIDC still returns json."""
        import json

        with tempfile.NamedTemporaryFile(
            "w", suffix=".sidc", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("TOOLSHORT\n")
            path = fh.name
        try:
            rc, out, _ = self._run(["--format", "json", "batch", path])
            self.assertEqual(rc, 1)
            data = json.loads(out)
            self.assertFalse(data[0]["valid"])
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# cli.py hardening — describe subcommand
# ---------------------------------------------------------------------------


class TestCLIDescribe(unittest.TestCase):
    def _run(self, argv):
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = main(argv)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def test_describe_bad_sidc_returns_nonzero(self):
        rc, _, err = self._run(["describe", "TOOSHORT"])
        self.assertEqual(rc, 1)
        self.assertIn("error", err.lower())

    def test_describe_valid_sidc_returns_zero(self):
        rc, out, _ = self._run(["describe", "SFGPUCI-----USG"])
        self.assertEqual(rc, 0)
        self.assertIn("Friend", out)


# ---------------------------------------------------------------------------
# mcp_server.py — importability (the broken scan/to_json references are fixed)
# ---------------------------------------------------------------------------


class TestMCPServerImportable(unittest.TestCase):
    def test_mcp_server_imports_without_error(self):
        """mcp_server must be importable; it no longer references missing names."""
        try:
            import natosymbol.mcp_server as mcp_mod  # noqa: F401

            # Force a fresh import in case it was cached before the fix
            importlib.reload(mcp_mod)
        except ImportError as exc:
            self.fail(f"mcp_server raised ImportError: {exc}")

    def test_serve_returns_nonzero_when_mcp_missing(self):
        """serve() must return 1 (not crash) when the 'mcp' package is absent."""
        import natosymbol.mcp_server as mcp_mod

        # Temporarily hide 'mcp' so the optional import fails
        original = sys.modules.get("mcp")
        sys.modules["mcp"] = None  # type: ignore[assignment]
        try:
            rc = mcp_mod.serve()
            self.assertEqual(rc, 1)
        finally:
            if original is None:
                sys.modules.pop("mcp", None)
            else:
                sys.modules["mcp"] = original


if __name__ == "__main__":
    unittest.main()
