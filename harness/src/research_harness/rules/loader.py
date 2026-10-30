"""Load and lint rule packs (02 §8.1–§8.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.hashing import canonical_json_hash
from research_harness.schemas import validate as schema_validate


@dataclass
class Pack:
    meta: dict[str, Any]
    rules: list[dict[str, Any]] = field(default_factory=list)
    sha256: str = ""

    @property
    def id(self) -> str:
        return self.meta["id"]

    @property
    def layer(self) -> int:
        return int(self.meta["layer"])

    @property
    def version(self) -> str:
        return str(self.meta["version"])

    @property
    def status(self) -> str:
        return self.meta["status"]


def load_pack(pack_dir: Path) -> Pack:
    meta = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))
    rules: list[dict[str, Any]] = []
    rules_dir = pack_dir / "rules"
    if rules_dir.is_dir():
        for rf in sorted(rules_dir.glob("*.yaml")):
            doc = yaml.safe_load(rf.read_text(encoding="utf-8"))
            if isinstance(doc, list):
                rules.extend(doc)
            elif isinstance(doc, dict) and "rules" in doc:
                rules.extend(doc["rules"])
            elif isinstance(doc, dict):
                rules.append(doc)
    return Pack(meta=meta, rules=rules, sha256=canonical_json_hash({"pack": meta, "rules": rules}))


def lint_pack(pack_dir: Path) -> list[str]:
    """Return a list of problems; empty means the pack is valid."""
    problems: list[str] = []
    try:
        pack = load_pack(pack_dir)
    except (OSError, yaml.YAMLError) as exc:
        return [f"cannot load pack: {exc}"]

    problems += [f"pack.yaml: {m}" for m in schema_validate("rulepack", pack.meta)]
    seen: set[str] = set()
    for rule in pack.rules:
        rid = rule.get("id", "<no-id>")
        problems += [f"rule {rid}: {m}" for m in schema_validate("rule", rule)]
        if rid in seen:
            problems.append(f"rule {rid}: duplicate id in pack")
        seen.add(rid)
        if rule.get("pack") != pack.id:
            problems.append(f"rule {rid}: pack field {rule.get('pack')!r} != {pack.id!r}")
        if pack.layer == 0 and rule.get("overridable", True):
            problems.append(f"rule {rid}: core (layer 0) rules must be overridable: false")
    return problems
