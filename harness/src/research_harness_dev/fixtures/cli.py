"""`rh-dev fixtures generate <NAME> [--dest DIR]` — synthetic fixtures (H6)."""

from __future__ import annotations

import argparse
from pathlib import Path

# fixture name -> (module, function)
BUILDERS = {
    "F5b": ("f5b", "build_f5b"),
    "F5f": ("f5f", "build_f5f"),
    "F7-structure": ("f7_structure", "build_f7_structure"),
    "F5a": ("f5a_rules", "build_f5a"),
}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rh-dev fixtures")
    sub = parser.add_subparsers(dest="action", required=True)
    gen = sub.add_parser("generate", help="Generate a named fixture.")
    gen.add_argument("name", choices=sorted(BUILDERS))
    gen.add_argument("--dest", help="Output directory (default: build/fixtures/<NAME>).")
    args = parser.parse_args(argv)

    if args.action == "generate":
        import importlib

        mod_name, func_name = BUILDERS[args.name]
        mod = importlib.import_module(f"research_harness_dev.fixtures.{mod_name}")
        dest = Path(args.dest) if args.dest else Path.cwd() / "build" / "fixtures" / args.name
        out = getattr(mod, func_name)(dest)
        print(f"generated {args.name} at {out}")
        return 0
    return 2
