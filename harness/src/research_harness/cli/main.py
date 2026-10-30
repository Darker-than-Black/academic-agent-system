"""`rh` entry point: argument parsing and command dispatch.

Each command's logic lives in a ``cli/<area>.py`` handler returning
``(envelope, exit_code)``. Handlers may raise :class:`RhError`; dispatch turns
it into an error envelope with the mapped exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from research_harness import __version__
from research_harness.core.envelope import SCHEMA_VERSION, build_envelope, error_envelope
from research_harness.core.errors import RhError
from research_harness.i18n import resolve_lang, t


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rh", description="Research Harness CLI (rh).")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--lang", choices=("uk", "en"), default=None)
    parser.add_argument("--workspace", help="Workspace root (default: nearest parent workspace).")
    parser.add_argument(
        "--object", help="Object id (A-/T-…); resolves its folder in the workspace."
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.add_parser("version", help="Print the harness version envelope.")

    v = sub.add_parser("validate", help="Run read-only validation checks.")
    v.add_argument("--scope", choices=sorted({"schema", "refs", "structure", "freshness", "all"}))
    v.add_argument("--schema", help="Schema name to validate --file against.")
    v.add_argument("--file", action="append", help="File(s) to validate; repeatable.")
    v.add_argument("--known", action="append", help="Known artifact ref(s) for ref checks.")
    v.add_argument("--root", help="Object root for freshness (default: nearest parent with .rh/).")

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

    iw = sub.add_parser("init-workspace", help="Create a new workspace.")
    iw.add_argument("path", help="Directory for the workspace.")

    au = sub.add_parser("author", help="Author profile commands.")
    au_sub = au.add_subparsers(dest="author_action", metavar="action", required=True)
    au_sub.add_parser("show", help="Show the author profile.")
    au_set = au_sub.add_parser("set", help="Set a profile field (versioned).")
    au_set.add_argument("key")
    au_set.add_argument("value")
    au_pin = au_sub.add_parser("pin", help="Re-pin the author profile into an object.")
    au_pin.add_argument("--object", dest="object", required=True)

    rn = sub.add_parser("rename", help="Rename an object (folder + history).")
    rn.add_argument("--object", dest="object", required=True)
    rn.add_argument("--title", required=True)

    wk = sub.add_parser("workspace", help="Workspace maintenance.")
    wk_sub = wk.add_subparsers(dest="workspace_action", metavar="action", required=True)
    wk_sub.add_parser("reindex", help="Rebuild the object index from folders on disk.")

    _register_more(sub)
    return parser


def _register_more(sub: argparse._SubParsersAction) -> None:
    """Subcommands added by later M1 cards (structure, rules, intake, …)."""
    from research_harness.cli import register_all

    register_all(sub)


def _emit(envelope: dict[str, Any], fmt: str) -> None:
    if fmt == "text":
        rendered = envelope.get("data", {}).get("_text")
        print(rendered if rendered else envelope["message"])
    else:
        json.dump(envelope, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


def _dispatch(args: argparse.Namespace, lang: str) -> tuple[dict[str, Any], int] | None:
    cmd = args.command
    if cmd == "validate":
        from research_harness.cli.validate import run

        return run(args, lang)
    if cmd in ("checkpoint", "resume", "history"):
        from research_harness.cli import state as m

        return getattr(m, cmd)(args, lang)
    if cmd in ("init-workspace", "author", "rename", "workspace"):
        from research_harness.cli import workspace as m

        fn = {"init-workspace": "init_workspace"}.get(cmd, cmd)
        return getattr(m, fn)(args, lang)
    from research_harness.cli import route_extra

    return route_extra(args, lang)


def _load_env() -> None:
    """Load a gitignored ``.env`` (keys live in env vars only, H8). No-op if absent.

    Values already set in the real environment win; a missing ``.env`` or a
    missing ``python-dotenv`` is silently skipped. Values are never logged.
    """
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path, override=False)


def main(argv: list[str] | None = None) -> int:
    _load_env()
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

    try:
        result = _dispatch(args, lang)
    except RhError as err:
        _emit(error_envelope(err, command=args.command, lang=lang), args.format)
        return err.exit_code

    if result is None:
        parser.print_help(sys.stderr)
        return 2
    envelope, code = result
    _emit(envelope, args.format)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
