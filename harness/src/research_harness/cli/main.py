"""`rh` entry point.

M1-01 scope: only the `version` command. The real envelope builder, i18n
message catalogs and the full global-option set arrive in M1-02 / M1-03; this
module keeps a minimal, forward-compatible shape of the envelope described in
`03-cli.md` §1.1 so that `rh version` already prints `data.version`.
"""

from __future__ import annotations

import argparse
import json
import sys

from research_harness import __version__

SCHEMA_VERSION = "0.2"

# Minimal inline messages until the i18n catalogs land in M1-02 (02 §1.6).
_VERSION_MESSAGE = {
    "uk": "Research Harness, версія {version}.",
    "en": "Research Harness, version {version}.",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rh",
        description="Research Harness CLI (rh).",
        add_help=True,
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format: one JSON envelope (default) or a human summary.",
    )
    parser.add_argument(
        "--lang",
        choices=("uk", "en"),
        default="uk",
        help="Language of human-readable output (02 §1.6).",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.add_parser("version", help="Print the harness version envelope.")
    return parser


def _emit(envelope: dict, fmt: str) -> None:
    if fmt == "text":
        print(envelope["message"])
    else:
        json.dump(envelope, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


def _version_envelope(lang: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "version",
        "status": "ok",
        "lang": lang,
        "message": _VERSION_MESSAGE[lang].format(version=__version__),
        "data": {"version": __version__, "schema_version": SCHEMA_VERSION},
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return 2

    if args.command == "version":
        _emit(_version_envelope(args.lang), args.format)
        return 0

    # argparse rejects unknown commands before reaching here.
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
