"""`rh rules lint|resolve|show` (M1-08)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.rules.loader import lint_pack, load_pack
from research_harness.rules.resolver import build_resolved_stack, resolve
from research_harness.rules.selector import select_packs
from research_harness.state.snapshot import atomic_write_bytes

_COMMAND = "rules"
_RULEPACKS = Path(__file__).resolve().parents[3] / "rulepacks"


def register(sub: argparse._SubParsersAction) -> None:
    rp = sub.add_parser(_COMMAND, help="Rule packs: lint, resolve, show.")
    sa = rp.add_subparsers(dest="rules_action", metavar="action", required=True)
    lint = sa.add_parser("lint", help="Lint a rule-pack directory.")
    lint.add_argument("path")
    res = sa.add_parser("resolve", help="Resolve the rule stack for an object.")
    res.add_argument("--packs", help="Rule-packs directory (default: bundled).")
    sa.add_parser("show", help="Show the resolved stack for an object.")


def handles(command: str) -> bool:
    return command == _COMMAND


def _packs_dir(args: Any) -> Path:
    return Path(getattr(args, "packs", None) or _RULEPACKS)


def _all_packs(packs_dir: Path) -> list:
    return [load_pack(d) for d in sorted(packs_dir.iterdir()) if (d / "pack.yaml").is_file()]


def _answers(root: Path) -> dict[str, Any]:
    obj = json.loads((root / "object.json").read_text(encoding="utf-8"))
    ans = {"document_kind": obj.get("document_kind"), "study_kind": obj.get("study_kind")}
    intake = root / "intake" / "answers.json"
    if intake.is_file():
        ans.update(json.loads(intake.read_text(encoding="utf-8")).get("answers", {}))
    return ans


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    action = args.rules_action
    if action == "lint":
        problems = lint_pack(Path(args.path))
        status = "invalid" if problems else "ok"
        env = build_envelope(
            command=_COMMAND,
            status=status,
            lang=lang,
            message_key="rules.lint_bad" if problems else "rules.lint_ok",
            message_params={"n": len(problems)},
            data={"problems": problems},
        )
        return env, (2 if problems else 0)

    root = object_root(args)
    packs = select_packs(_all_packs(_packs_dir(args)), _answers(root))
    stack = resolve(packs)

    if action == "resolve":
        inputs = [{"ref": f"rulepack:{p.id}@{p.version}", "sha256": p.sha256} for p in packs]
        doc = build_resolved_stack(stack, inputs)
        atomic_write_bytes(
            root / "profiles" / "resolved-stack.json",
            (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        blocked = any(f["severity"] == "blocker" for f in stack.findings)
        env = build_envelope(
            command=_COMMAND,
            status="blocked" if blocked else ("partial" if stack.findings else "ok"),
            lang=lang,
            message_key="rules.resolved",
            message_params={"n": len(stack.findings)},
            findings=[
                {k: v for k, v in f.items() if k in ("check_id", "severity", "reason")}
                for f in stack.findings
            ],
            data={
                "packs": len(stack.packs),
                "rules": len(stack.rules),
                "export_blocked": stack.export_blocked(),
            },
        )
        return env, (3 if blocked else 0)

    # show
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="rules.shown",
            data={"packs": stack.packs, "rules": stack.rules},
        ),
        0,
    )
