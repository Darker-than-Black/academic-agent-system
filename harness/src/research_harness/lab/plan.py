"""Search plans (``lab/search-plan-v<N>.yaml``): validated and versioned.

A plan must name resources (checked against the policy), carry a saturation
(stopping) rule and a budget (FR-56). No search runs without a stored plan.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from research_harness.schemas import validate
from research_harness.sources.policy import resources as policy_resources

_PLAN_RE = re.compile(r"^search-plan-v(\d+)\.yaml$")


def lab_dir(root: Path) -> Path:
    d = root / "lab"
    d.mkdir(parents=True, exist_ok=True)
    return d


def plan_path(root: Path, version: int) -> Path:
    return root / "lab" / f"search-plan-v{version}.yaml"


def latest_version(root: Path) -> int:
    d = root / "lab"
    if not d.is_dir():
        return 0
    versions = [int(m.group(1)) for f in d.iterdir() if (m := _PLAN_RE.match(f.name))]
    return max(versions) if versions else 0


def load_latest(root: Path) -> dict[str, Any] | None:
    v = latest_version(root)
    if v == 0:
        return None
    return yaml.safe_load(plan_path(root, v).read_text(encoding="utf-8"))


def has_plan(root: Path) -> bool:
    return latest_version(root) > 0


def validate_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Schema + policy checks. Returns findings (blockers stop a freeze/search)."""
    findings: list[dict[str, Any]] = []
    errors = validate("search-plan", plan)
    missing_stop = any("saturation_rule" in e or "budget" in e for e in errors)
    if missing_stop:
        findings.append(
            {
                "check_id": "search.plan_no_stop_rule",
                "severity": "blocker",
                "reason": "a plan needs a saturation rule and a budget (FR-56)",
                "location": {},
                "proposed_action": "",
            }
        )
    for e in errors:
        if "saturation_rule" in e or "budget" in e:
            continue
        findings.append(
            {
                "check_id": "search.plan_invalid",
                "severity": "blocker",
                "reason": e,
                "location": {},
                "proposed_action": "",
            }
        )
    known = set(policy_resources())
    for res in plan.get("resources", []):
        name = res.get("resource")
        if name not in known:
            findings.append(
                {
                    "check_id": "search.coverage_gap",
                    "severity": "info",
                    "reason": f"resource {name!r} is not in the policy catalogue",
                    "location": {},
                    "proposed_action": "",
                }
            )
    return findings


def save_plan(root: Path, plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate and store a new plan version. Blocker findings prevent saving."""
    plan = dict(plan)
    plan.setdefault("schema_version", "0.2")
    plan["version"] = latest_version(root) + 1
    if plan["version"] > 1:
        plan["previous"] = plan["version"] - 1
    findings = validate_plan(plan)
    if any(f["severity"] == "blocker" for f in findings):
        return plan, findings
    lab_dir(root)
    plan_path(root, plan["version"]).write_text(
        yaml.safe_dump(plan, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return plan, findings
