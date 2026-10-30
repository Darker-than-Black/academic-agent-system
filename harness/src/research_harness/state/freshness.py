"""Freshness and invalidation over the dependency graph (02 §6, FR-10, T09).

Freshness is computed on demand from the current snapshot; it is never stored.
A record carrying ``inputs`` / ``dependencies`` / ``evidence`` / ``result_ref``
(or an excerpt's ``source_id`` + ``source_sha256``) is **stale** when any
artifact it references has a current hash different from the ``sha256`` recorded
in the record, or when any referenced record is itself stale (transitive). Only
dependents are invalidated; unrelated sources, claims and checks stay current.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.hashing import canonical_json_hash, file_hash
from research_harness.core.refs import parse_ref
from research_harness.state import snapshot as snap

_PART_FILE = {
    "text": "text.md",
    "brief": "brief.md",
    "summary": "summary.md",
    "claims": "claims.json",
}

_ID_PREFIX = [
    ("RR-", "result"),
    ("CR-", "check_run"),
    ("DEF-", "definition"),
    ("AR-", "approval_request"),
    ("AP-", "approval"),
    ("PG-", "paragraph"),
    ("SUB-", "submission"),
    ("PUB-", "publication"),
    ("RC-", "reviewer_comment"),
    ("TK-", "thesis_task"),
    ("NV-", "novelty"),
    ("AS-", "asset"),
]
_ID_SINGLE = {
    "S": "source",
    "E": "excerpt",
    "C": "claim",
    "R": "run",
    "D": "dataset",
    "P": "premise",
    "M": "material",
    "F": "finding",
    "U": "unit",
}


def kind_from_id(rid: str) -> str:
    for pref, kind in _ID_PREFIX:
        if rid.startswith(pref):
            return kind
    head = rid.split("-", 1)[0]
    return _ID_SINGLE.get(head[:1], "artifact") if head else "artifact"


@dataclass
class ObjectGraph:
    id_to_record: dict[str, dict[str, Any]] = field(default_factory=dict)
    id_to_hash: dict[str, str] = field(default_factory=dict)
    id_to_path: dict[str, str] = field(default_factory=dict)  # record id -> relpath of its file
    part_hash: dict[tuple[str, str], str] = field(default_factory=dict)  # (unit_id, part) -> hash
    unit_dir: dict[str, str] = field(default_factory=dict)  # unit id -> folder relpath


def _iter_records(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, dict):
        return [obj] if "id" in obj else []
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict) and "id" in x]
    return []


def _front_matter_id(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    _, _, rest = text.partition("\n")
    body, sep, _ = rest.partition("\n---")
    if not sep:
        return None
    try:
        data = yaml.safe_load(body)
    except yaml.YAMLError:
        return None
    return data.get("id") if isinstance(data, dict) else None


def load_graph(root: Path) -> ObjectGraph:
    g = ObjectGraph()
    for rel, _stored in snap.managed_files(root):
        p = root / rel
        name = Path(rel).name
        if name == "text.md":
            uid = _front_matter_id(p.read_text(encoding="utf-8"))
            if uid:
                folder = str(Path(rel).parent)
                g.unit_dir[uid] = folder
                for part, fname in _PART_FILE.items():
                    fp = root / folder / fname
                    if fp.is_file():
                        g.part_hash[(uid, part)] = file_hash(fp)
            continue
        if rel.endswith(".json") or rel.endswith(".jsonl"):
            try:
                if rel.endswith(".jsonl"):
                    objs: list[Any] = [
                        json.loads(line)
                        for line in p.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                else:
                    objs = [json.loads(p.read_text(encoding="utf-8"))]
            except json.JSONDecodeError:
                continue
            for top in objs:
                for rec in _iter_records(top):
                    rid = rec["id"]
                    g.id_to_record[rid] = rec
                    g.id_to_hash[rid] = canonical_json_hash(rec)
                    g.id_to_path[rid] = rel
    return g


def _edges(rec: dict[str, Any]) -> list[tuple[str, str | None, str | None]]:
    """Outgoing (target_id, part, recorded_sha_or_None)."""
    edges: list[tuple[str, str | None, str | None]] = []
    for key in ("inputs", "dependencies"):
        for item in rec.get(key) or []:
            if isinstance(item, dict) and "ref" in item:
                r = parse_ref(item["ref"])
                edges.append((r.id, r.part, item.get("sha256")))
    for item in rec.get("evidence") or []:
        if isinstance(item, dict) and "id" in item:
            edges.append((item["id"], None, None))
    rr = rec.get("result_ref")
    if isinstance(rr, str):
        r = parse_ref(rr)
        edges.append((r.id, r.part, None))
    sid = rec.get("source_id")
    if isinstance(sid, str):
        edges.append((sid, None, rec.get("source_sha256")))
    return edges


def _resolve_current(g: ObjectGraph, target_id: str, part: str | None) -> str | None:
    if part:
        return g.part_hash.get((target_id, part))
    return g.id_to_hash.get(target_id)


def compute_stale(root: Path, graph: ObjectGraph | None = None) -> set[str]:
    """Return the set of stale display refs (``<kind>:<id>``)."""
    g = graph or load_graph(root)
    memo: dict[str, bool] = {}

    def stale(tid: str, stack: set[str]) -> bool:
        if tid in memo:
            return memo[tid]
        rec = g.id_to_record.get(tid)
        if rec is None:
            return False  # leaf file-part or unknown artifact: not itself stale
        edges = _edges(rec)
        if not edges:
            memo[tid] = False
            return False
        if tid in stack:
            return False  # cycle guard
        stack.add(tid)
        direct = any(
            recorded is not None and _resolve_current(g, t, p) != recorded
            for (t, p, recorded) in edges
        )
        trans = any(stale(t, stack) for (t, _p, _r) in edges)
        stack.discard(tid)
        memo[tid] = direct or trans
        return memo[tid]

    out: set[str] = set()
    for rid, rec in g.id_to_record.items():
        if _edges(rec) and stale(rid, set()):
            out.add(f"{kind_from_id(rid)}:{rid}")
    return out


def is_stale(root: Path, ref: str) -> bool:
    return ref in compute_stale(root)


# --- approvals -------------------------------------------------------------
def _snapshot_file_hash(root: Path, snapshot_id: str, relpath: str) -> str | None:
    manifest = snap.load_snapshot(root, snapshot_id)
    for e in manifest["files"]:
        if e["path"] == relpath:
            return e["sha256"]
    return None


def _ref_relpath(g: ObjectGraph, ref_str: str) -> str | None:
    r = parse_ref(ref_str)
    if r.kind == "unit" and r.part:
        folder = g.unit_dir.get(r.id)
        if folder is None:
            return None
        return str(Path(folder) / _PART_FILE.get(r.part, f"{r.part}.md"))
    return g.id_to_path.get(r.id)


def approval_valid(root: Path, approval: dict[str, Any], graph: ObjectGraph | None = None) -> bool:
    """An approval is valid for the current snapshot iff its manifest matches, or
    every ref it was bound to still has the hash it had in the approved snapshot
    (02 §6, step 3). An approval for snapshot X never counts for snapshot Y."""
    g = graph or load_graph(root)
    cur = snap.read_current(root)
    if cur is None:
        return False
    current_manifest = snap.load_snapshot(root, cur)["manifest_sha256"]
    target = approval.get("target", {})
    if target.get("manifest_sha256") == current_manifest:
        return True
    refs = target.get("refs") or []
    snap_id = target.get("snapshot_id")
    if not refs or not snap_id:
        return False
    for ref_str in refs:
        relpath = _ref_relpath(g, ref_str)
        if relpath is None:
            return False
        then = _snapshot_file_hash(root, snap_id, relpath)
        now = _snapshot_file_hash(root, cur, relpath)
        if then is None or now is None or then != now:
            return False
    return True


def freshness_report(root: Path) -> dict[str, Any]:
    g = load_graph(root)
    stale = sorted(compute_stale(root, g))
    return {
        "stale": stale,
        "stale_count": len(stale),
        "record_count": len(g.id_to_record),
    }
