"""Structure-scope check: forbidden / unresolved source origin (M4-13).

Runs when ``ctx.extra["object_root"]`` is set. Reuses the integrity logic so
``rh validate`` and the verified export report the same findings. Russian-language
or russia/belarus-published sources are blockers; an unresolved origin is a major
(H7 — a missing language/country is never guessed).
"""

from __future__ import annotations

from pathlib import Path

from research_harness.integrity import source_origin
from research_harness.validate.framework import Finding, ValidationContext, registry

CHECK_ID = "integrity.source_origin"


@registry.register(id=CHECK_ID, version="1", scope="structure")
def _source_origin_check(ctx: ValidationContext) -> list[Finding]:
    root = ctx.extra.get("object_root")
    if root is None:
        return []
    return source_origin.origin_findings(Path(root))


__all__ = ["CHECK_ID"]
