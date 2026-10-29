"""`rh-dev fixtures generate <NAME> [--dest DIR]` — synthetic fixtures (H6)."""

from __future__ import annotations

import argparse
from pathlib import Path

BUILDERS = {"F5b": "build_f5b"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rh-dev fixtures")
    sub = parser.add_subparsers(dest="action", required=True)
    gen = sub.add_parser("generate", help="Generate a named fixture.")
    gen.add_argument("name", choices=sorted(BUILDERS))
    gen.add_argument("--dest", help="Output directory (default: build/fixtures/<NAME>).")
    args = parser.parse_args(argv)

    if args.action == "generate":
        from research_harness_dev.fixtures import f5b

        dest = Path(args.dest) if args.dest else Path.cwd() / "build" / "fixtures" / args.name
        builder = getattr(f5b, BUILDERS[args.name])
        out = builder(dest)
        print(f"generated {args.name} at {out}")
        return 0
    return 2
