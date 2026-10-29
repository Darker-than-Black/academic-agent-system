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

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
