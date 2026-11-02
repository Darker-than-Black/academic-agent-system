"""`rh style profile build --lang L` — build a style profile (M3-13, FR-19).

`propose` / `accept` (proposals from the author's edits, applied only after the
author accepts in a human channel) are deferred to a later card.
"""

from __future__ import annotations

import argparse
from typing import Any

import yaml

from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.integrity import errors as errors_mod
from research_harness.integrity import overlap as overlap_mod
from research_harness.integrity import style as style_mod
from research_harness.schemas import validate
from research_harness.state.snapshot import atomic_write_bytes
from research_harness.workspace import author as author_mod
from research_harness.workspace.workspace import Workspace

_COMMAND = "style"


def register(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser(_COMMAND, help="Author style profile per language.")
    sa = sp.add_subparsers(dest="style_action", metavar="action", required=True)
    prof = sa.add_parser("profile", help="Build or inspect a style profile.")
    pa = prof.add_subparsers(dest="profile_action", metavar="action", required=True)
    build = pa.add_parser("build", help="Build the profile from the author corpus.")
    build.add_argument("--lang", required=True, help="Language code (e.g. uk, en).")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    ws = Workspace.find(getattr(args, "workspace", None))
    author_root = author_mod.author_dir(ws)
    corpus = overlap_mod.load_corpus(author_root / "corpus")
    catalog = errors_mod.load_catalog()
    profile = style_mod.build_profile(
        list(corpus.values()),
        args.lang,
        voice_markers=catalog.get("voice_markers", {}),
        built_from=sorted(corpus.keys()),
    )
    if validate("style-profile", profile):
        raise InvalidInputError("error.style_invalid")
    out = author_root / "style" / args.lang / "profile.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(
        out, yaml.safe_dump(profile, allow_unicode=True, sort_keys=False).encode("utf-8")
    )
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="style.built",
            message_params={"lang": args.lang, "n": len(corpus)},
            data={"profile": profile},
        ),
        0,
    )
