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
    "F4-W": ("f4w_metadata", "build_f4w_metadata"),
    "F4-W-working": ("f4w", "build_f4w"),
    "F5b-lifecycle": ("f5b", "build_f5b_lifecycle"),
    "F5d": ("f5d_docx", "build_f5d"),
}

# Committed location of the F4-W working set (no full texts, H8).
_F4W_DIR = Path(__file__).resolve().parents[3] / "evals" / "fixtures" / "F4W"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rh-dev fixtures")
    sub = parser.add_subparsers(dest="action", required=True)
    gen = sub.add_parser("generate", help="Generate a named fixture.")
    gen.add_argument("name", choices=sorted(BUILDERS))
    gen.add_argument("--dest", help="Output directory (default: build/fixtures/<NAME>).")
    chk = sub.add_parser("check", help="Validate a fixture's structure.")
    chk.add_argument("name")
    chk.add_argument("--dir", help="Fixture directory (default: the committed F4W dir).")
    lock = sub.add_parser(
        "holdout-lock",
        help="Build holdout.lock.json from a decrypted holdout dir OUTSIDE the repo (H1).",
    )
    lock.add_argument("--dir", required=True)
    lock.add_argument("--out")
    lock.add_argument("--fixture")
    args = parser.parse_args(argv)

    if args.action == "generate":
        import importlib

        mod_name, func_name = BUILDERS[args.name]
        mod = importlib.import_module(f"research_harness_dev.fixtures.{mod_name}")
        dest = Path(args.dest) if args.dest else Path.cwd() / "build" / "fixtures" / args.name
        out = getattr(mod, func_name)(dest)
        print(f"generated {args.name} at {out}")
        return 0
    if args.action == "check":
        from research_harness_dev.fixtures.check import main as check_main

        fixture_dir = Path(args.dir) if args.dir else _F4W_DIR
        return check_main(args.name, fixture_dir)
    if args.action == "holdout-lock":
        from research_harness_dev.fixtures.holdout_lock import main as lock_main

        lock_argv = ["--dir", args.dir]
        if args.out:
            lock_argv += ["--out", args.out]
        if args.fixture:
            lock_argv += ["--fixture", args.fixture]
        return lock_main(lock_argv)
    return 2
