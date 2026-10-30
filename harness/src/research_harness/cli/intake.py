"""`rh intake questions|answer` (M1-09)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.intake import answers as answers_mod
from research_harness.intake import questions as questions_mod
from research_harness.intake.flow import apply_answer

_COMMAND = "intake"


def register(sub: argparse._SubParsersAction) -> None:
    it = sub.add_parser(_COMMAND, help="Intake questionnaire.")
    sa = it.add_subparsers(dest="intake_action", metavar="action", required=True)
    sa.add_parser("questions", help="List questions still to ask (with prefills).")
    ans = sa.add_parser("answer", help="Record an answer.")
    ans.add_argument("--question", required=True)
    ans.add_argument("--value")
    ans.add_argument("--unknown", action="store_true")


def handles(command: str) -> bool:
    return command == _COMMAND


def _author_profile(args: Any) -> dict[str, Any]:
    from research_harness.workspace import author
    from research_harness.workspace.workspace import Workspace

    try:
        return author.read_profile(Workspace.find(getattr(args, "workspace", None)))
    except Exception:
        return {}


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.intake_action == "questions":
        data = answers_mod.load(root)
        result = questions_mod.plan(data["answers"], author_profile=_author_profile(args))
        ask = [
            {
                "id": q["id"],
                "text": q["text"].get(lang, q["text"]["en"]),
                "help": q["help"].get(lang, q["help"]["en"]),
                "type": q["type"],
                "options": q.get("options"),
            }
            for q in result["ask"]
        ]
        return (
            build_envelope(
                command=_COMMAND,
                status="ok",
                lang=lang,
                message_key="intake.questions",
                message_params={"n": len(ask)},
                data={"ask": ask, "prefilled": result["prefilled"]},
            ),
            0,
        )

    # answer
    value = answers_mod.UNKNOWN if args.unknown else args.value
    if value is None:
        from research_harness.core.errors import InvalidInputError

        raise InvalidInputError("error.intake_no_value")
    result = apply_answer(root, args.question, value, lang=lang)
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="intake.answered",
            message_params={"q": args.question},
            data={
                "question": args.question,
                "consequences": result["consequences"],
                "g0_request": result["g0_request"],
            },
        ),
        0,
    )
