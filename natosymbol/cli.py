"""Command-line interface for NATOSYMBOL.

Subcommands:
  validate <SIDC>...        Validate one or more SIDCs (exit 1 if any invalid)
  describe <SIDC>           Decode a SIDC into human-readable fields
  build [field flags]       Assemble a SIDC from component fields
  batch <file>              Validate a file of SIDCs, one per line

Global:
  --version
  --format {table,json}
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import TOOL_NAME, TOOL_VERSION
from .core import (
    SIDCError,
    build_sidc,
    describe_sidc,
    validate_sidc,
)


def _emit(obj, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(obj, indent=2))
        return
    # table format
    if isinstance(obj, dict) and all(isinstance(v, dict) and "label" in v for k, v in obj.items() if k != "code"):
        print(f"SIDC: {obj.get('code', '')}")
        for key, val in obj.items():
            if key == "code":
                continue
            print(f"  {key:<18} {val['code']:<8} {val['label']}")
    elif isinstance(obj, list):
        for row in obj:
            status = "OK   " if row.get("valid") else "FAIL "
            note = row.get("error", "")
            print(f"  {status} {row.get('code', ''):<16} {note}")
    else:
        print(json.dumps(obj, indent=2))


def _cmd_validate(args) -> int:
    results = []
    ok = True
    for code in args.sidc:
        try:
            validate_sidc(code)
            results.append({"code": code, "valid": True})
        except SIDCError as e:
            ok = False
            results.append({"code": code, "valid": False, "error": str(e)})
    _emit(results, args.format)
    return 0 if ok else 1


def _cmd_describe(args) -> int:
    try:
        desc = describe_sidc(args.sidc)
    except SIDCError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    _emit(desc, args.format)
    return 0


def _cmd_build(args) -> int:
    try:
        code = build_sidc(
            coding_scheme=args.scheme,
            affiliation=args.affiliation,
            battle_dimension=args.dimension,
            status=args.status,
            function_id=args.function or "",
            modifier_1=args.modifier1,
            modifier_2=args.modifier2,
            country=args.country,
            order_of_battle=args.oob,
        )
    except SIDCError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.format == "json":
        _emit({"code": code}, "json")
    else:
        print(code)
    return 0


def _cmd_batch(args) -> int:
    results = []
    ok = True
    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as e:
        print(f"error: cannot read {args.file}: {e}", file=sys.stderr)
        return 1
    seen = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        seen += 1
        try:
            validate_sidc(line)
            results.append({"code": line, "valid": True})
        except SIDCError as e:
            ok = False
            results.append({"code": line, "valid": False, "error": str(e)})
    if seen == 0:
        print("error: no SIDCs found in file", file=sys.stderr)
        return 1
    _emit(results, args.format)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Generate and validate APP-6 / MIL-STD-2525C symbol identification codes (SIDC).",
    )
    p.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    p.add_argument("--format", choices=["table", "json"], default="table", help="output format")

    sub = p.add_subparsers(dest="command", required=True)

    pv = sub.add_parser("validate", help="validate one or more SIDCs")
    pv.add_argument("sidc", nargs="+", help="15-char SIDC string(s)")
    pv.set_defaults(func=_cmd_validate)

    pd = sub.add_parser("describe", help="decode a SIDC into readable fields")
    pd.add_argument("sidc", help="15-char SIDC string")
    pd.set_defaults(func=_cmd_describe)

    pb = sub.add_parser("build", help="assemble a SIDC from component fields")
    pb.add_argument("--scheme", default="S", help="coding scheme (default S=Warfighting)")
    pb.add_argument("--affiliation", default="U", help="affiliation (default U=Unknown)")
    pb.add_argument("--dimension", default="G", help="battle dimension (default G=Ground)")
    pb.add_argument("--status", default="P", help="status (default P=Present)")
    pb.add_argument("--function", default="", help="6-char function ID (e.g. UCI--- = Infantry)")
    pb.add_argument("--modifier1", default="-", help="symbol modifier 1 (HQ/TF/feint)")
    pb.add_argument("--modifier2", default="-", help="symbol modifier 2 (echelon)")
    pb.add_argument("--country", default="--", help="2-char country code")
    pb.add_argument("--oob", default="-", help="order of battle")
    pb.set_defaults(func=_cmd_build)

    pa = sub.add_parser("batch", help="validate a file of SIDCs (one per line)")
    pa.add_argument("file", help="path to file of SIDCs")
    pa.set_defaults(func=_cmd_batch)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
