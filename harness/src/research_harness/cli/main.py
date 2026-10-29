"""`rh` entry point.

Current scope: the ``version`` command, built through the shared envelope and
i18n layers (M1-02). More commands and the full global-option set arrive in
later M1 cards.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from research_harness import __version__
from research_harness.core.envelope import SCHEMA_VERSION, build_envelope
from research_harness.i18n import resolve_lang, t


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rh", description="Research Harness CLI (rh).")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--lang", choices=("uk", "en"), default=None)
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.add_parser("version", help="Print the harness version envelope.")

    v = sub.add_parser("validate", help="Run read-only validation checks.")
    v.add_argument("--scope", choices=sorted({"schema", "refs", "structure", "freshness", "all"}))
    v.add_argument("--schema", help="Schema name to validate --file against.")
    v.add_argument("--file", action="append", help="File(s) to validate; repeatable.")
    v.add_argument("--known", action="append", help="Known artifact ref(s) for ref checks.")

    cp = sub.add_parser("checkpoint", help="Record a snapshot of the current changes.")
    cp.add_argument("--by", choices=("human", "agent"), required=True)
    cp.add_argument("--request", help="The author's instruction (required for --by agent).")
    cp.add_argument(
        "--units", action="append", help="Limit attribution to these units; repeatable."
    )
    cp.add_argument("--message", help="Optional note.")
    cp.add_argument("--root", help="Object root (default: nearest parent with .rh/).")

    rs = sub.add_parser("resume", help="Run recovery and report state (no content change).")
    rs.add_argument("--root", help="Object root (default: nearest parent with .rh/).")

    hi = sub.add_parser("history", help="Show snapshot history.")
    hi.add_argument("--root", help="Object root (default: nearest parent with .rh/).")
    return parser


def _emit(envelope: dict[str, Any], fmt: str) -> None:
    if fmt == "text":
        print(envelope["message"])
    else:
        json.dump(envelope, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    lang = resolve_lang(args.lang)

    if args.command is None:
        print(t("cli.no_command", lang), file=sys.stderr)
        return 2

    if args.command == "version":
        envelope = build_envelope(
            command="version",
            status="ok",
            lang=lang,
            message_key="version.message",
            message_params={"version": __version__},
            data={"version": __version__, "schema_version": SCHEMA_VERSION},
        )
        _emit(envelope, args.format)
        return 0

    if args.command == "validate":
        from research_harness.cli.validate import run as run_validate

        envelope, code = run_validate(args, lang)
        _emit(envelope, args.format)
        return code

    if args.command in ("checkpoint", "resume", "history"):
        from research_harness.cli import state as state_cli
        from research_harness.core.envelope import error_envelope
        from research_harness.core.errors import RhError

        handler = getattr(state_cli, args.command)
        try:
            envelope, code = handler(args, lang)
        except RhError as err:
            _emit(error_envelope(err, command=args.command, lang=lang), args.format)
            return err.exit_code
        _emit(envelope, args.format)
        return code

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
