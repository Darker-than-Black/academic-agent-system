"""Author-supplied thesis regulatory slots (P3-1, thesis.md open points).

постанова КМУ № 1240, the current Порядок / ОНП volume limits and which of УДУ's
local rules apply are legal facts only the author can supply (H6 — never
invented). They live in ``rulepacks/ua-mon-phd/regulatory.yaml`` as slots that
default to ``unknown``. While any required slot is ``unknown`` a thesis cannot be
``verified``: :func:`findings` returns a blocker per unfilled slot (H7). This
module fills nothing; it only loads, validates and reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

UNKNOWN = "unknown"

# Dotted paths that must hold a concrete (non-``unknown``) value, with a short
# description for the finding and the author checklist.
REQUIRED_SLOTS: dict[str, str] = {
    "volume_limits.main_text_author_sheets_min": (
        "main-text volume lower bound in author's sheets (постанова КМУ № 1240 / Порядок / ОНП)"
    ),
    "volume_limits.main_text_author_sheets_max": (
        "main-text volume upper bound in author's sheets (постанова КМУ № 1240 / Порядок / ОНП)"
    ),
    "volume_limits.source": "primary-text citation of the volume limits",
    "self_plagiarism_exclusion.rule": (
        "what disqualifies a publication from counting (self-plagiarism, постанова № 1240)"
    ),
    "self_plagiarism_exclusion.source": "primary-text citation of the self-plagiarism rule",
    "local_rules_udu.onp_applies": "whether the ОНП applies (true/false)",
    "local_rules_udu.ai_regulation_applies": "whether УДУ's AI-use regulation applies (true/false)",
}

# A source slot that is only required when its companion flag is true.
_CONDITIONAL_SOURCES: dict[str, str] = {
    "local_rules_udu.onp_applies": "local_rules_udu.onp_source",
    "local_rules_udu.ai_regulation_applies": "local_rules_udu.ai_regulation_source",
}

_REGULATORY_FILE = "regulatory.yaml"


def regulatory_path(pack_dir: Path) -> Path:
    return pack_dir / _REGULATORY_FILE


def load(pack_dir: Path) -> dict[str, Any]:
    """Load the regulatory slots (empty dict if the file is absent)."""
    path = regulatory_path(pack_dir)
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _get(data: dict[str, Any], dotted: str) -> Any:
    node: Any = data
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return UNKNOWN
        node = node[key]
    return node


def _is_unknown(value: Any) -> bool:
    return value is None or value == UNKNOWN


def _blocker(slot: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": "thesis.regulatory_unfilled",
        "severity": "blocker",
        "reason": reason,
        "location": {"locator": slot},
        "proposed_action": f"Fill {slot} in {_REGULATORY_FILE} from the primary text (H6).",
    }


def findings(pack_dir: Path) -> list[dict[str, Any]]:
    """A blocker per required slot still ``unknown`` (H7). Empty when all filled.

    A ``*_source`` slot is required only when its companion ``*_applies`` flag is
    true; a flag set to false needs no source."""
    data = load(pack_dir)
    out: list[dict[str, Any]] = []
    for slot, desc in REQUIRED_SLOTS.items():
        if _is_unknown(_get(data, slot)):
            out.append(_blocker(slot, f"thesis regulatory input is unknown: {desc}"))
    for flag_slot, source_slot in _CONDITIONAL_SOURCES.items():
        if _get(data, flag_slot) is True and _is_unknown(_get(data, source_slot)):
            out.append(
                _blocker(source_slot, f"primary-source citation required for {flag_slot}=true")
            )
    return out
