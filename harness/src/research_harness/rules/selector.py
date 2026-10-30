"""Pack selection against intake answers (02 §8.3 step 1). No eval."""

from __future__ import annotations

from typing import Any

from research_harness.rules.loader import Pack


def pack_applies(pack: Pack, answers: dict[str, Any]) -> bool:
    """A pack applies when every field in ``applies_when`` matches an answer.

    ``applies_when`` maps a field to a list of accepted values. An absent or
    ``unknown`` answer never matches a constrained field.
    """
    cond = pack.meta.get("applies_when") or {}
    for field, accepted in cond.items():
        value = answers.get(field)
        accepted_list = accepted if isinstance(accepted, list) else [accepted]
        if isinstance(value, list):
            if not any(v in accepted_list for v in value):
                return False
        elif value not in accepted_list:
            return False
    return True


def select_packs(packs: list[Pack], answers: dict[str, Any]) -> list[Pack]:
    return [p for p in packs if pack_applies(p, answers)]
