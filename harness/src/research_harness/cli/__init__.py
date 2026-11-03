"""Command-line entry point package for `rh`.

Later M1 cards (structure, rules, intake, gates, lifecycle, models, migrate,
eval) register their subcommands through :func:`register_all` and route through
:func:`route_extra`. Each such module exposes ``register(sub)`` and
``route(args, lang)`` (returning ``(envelope, code)`` or ``None``).
"""

from __future__ import annotations

import argparse
import importlib
from typing import Any

# cli submodules that self-register additional subcommands, in load order.
_EXTRA_MODULES: tuple[str, ...] = (
    "research_harness.cli.structure",
    "research_harness.cli.rules",
    "research_harness.cli.intake",
    "research_harness.cli.materials",
    "research_harness.cli.sources",
    "research_harness.cli.library",
    "research_harness.cli.search",
    "research_harness.cli.protocol",
    "research_harness.cli.synthesis",
    "research_harness.cli.claims",
    "research_harness.cli.methodology",
    "research_harness.cli.substance",
    "research_harness.cli.brief",
    "research_harness.cli.summaries",
    "research_harness.cli.contextpack",
    "research_harness.cli.drafting",
    "research_harness.cli.review",
    "research_harness.cli.resolution",
    "research_harness.cli.export",
    "research_harness.cli.import_docx",
    "research_harness.cli.gates",
    "research_harness.cli.autonomy",
    "research_harness.cli.ethics",
    "research_harness.cli.asset",
    "research_harness.cli.venue",
    "research_harness.cli.style",
    "research_harness.cli.errors",
    "research_harness.cli.repo",
    "research_harness.cli.ai_use",
    "research_harness.cli.dataset",
    "research_harness.cli.analysis",
    "research_harness.cli.results",
    "research_harness.cli.figure",
    "research_harness.cli.coding",
    "research_harness.cli.lifecycle_ops",
    "research_harness.cli.lifecycle",
    "research_harness.cli.models",
    "research_harness.cli.budget",
    "research_harness.cli.overlap",
    "research_harness.cli.migrate",
    "research_harness.cli.evals",
)


def _loaded() -> list[Any]:
    mods = []
    for name in _EXTRA_MODULES:
        try:
            mods.append(importlib.import_module(name))
        except ModuleNotFoundError:
            continue
    return mods


def register_all(sub: argparse._SubParsersAction) -> None:
    for mod in _loaded():
        if hasattr(mod, "register"):
            mod.register(sub)


def route_extra(args: argparse.Namespace, lang: str) -> tuple[dict[str, Any], int] | None:
    for mod in _loaded():
        if hasattr(mod, "handles") and mod.handles(args.command):
            return mod.route(args, lang)
    return None
