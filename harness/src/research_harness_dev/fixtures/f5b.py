"""F5b (part): a synthetic object root with snapshots and checkpoints.

Used by M1-04 (state), M1-05 (freshness) and M1-11 (status). Output is synthetic
(H6). The full F5b — objects at A0/A2/A12/A14/A16 — is extended by those cards.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.hashing import canonical_json_hash, file_hash
from research_harness.state import snapshot as snap
from research_harness.state.store import Store

HUMAN = {"kind": "human", "name": "fixture", "version": "0.1.0"}
AGENT = {"kind": "model", "name": "fixture", "version": "0.1.0"}

UNIT_A = "U-AAAA1111"
UNIT_B = "U-BBBB2222"
FOLDER_A = "manuscript/01 Unit A"
FOLDER_B = "manuscript/02 Unit B"


def build_object_with_checkpoints(dest: Path) -> Path:
    """Create an object root, an initial snapshot, and two author checkpoints."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "object.json").write_text('{"synthetic": true}\n', encoding="utf-8")
    store = Store(dest)
    store.init(HUMAN)

    unit = dest / "manuscript" / "01 Вступ"
    unit.mkdir(parents=True, exist_ok=True)
    (unit / "text.md").write_text("# Вступ\n\nsynthetic\n", encoding="utf-8")
    store.checkpoint(by="human", note="add intro (synthetic)")

    (unit / "text.md").write_text("# Вступ\n\nsynthetic, revised\n", encoding="utf-8")
    store.checkpoint(by="agent", request="розшир вступ (synthetic)")
    return dest


# --- F5b dependency graph (M1-05 freshness, T09) ---------------------------
def _wj(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _unit_text(uid: str, title: str, body: str) -> str:
    return f"---\nid: {uid}\ntitle: {title!r}\nkind: section\n---\n\n{body}\n"


def build_f5b(dest: Path) -> Path:
    """Synthetic object with a source→excerpt→claim→check dependency graph (H6).

    Shapes match 02 §12; values are synthetic. Hashes recorded in dependents are
    the current content hashes at build time, so mutating any artifact and
    re-checkpointing marks exactly its dependents stale (T09).
    """
    dest.mkdir(parents=True, exist_ok=True)
    _wj(dest / "object.json", {"schema_version": "0.2", "id": "T-2026-001", "synthetic": True})

    # Units (leaf file artifacts).
    (dest / FOLDER_A).mkdir(parents=True, exist_ok=True)
    (dest / FOLDER_B).mkdir(parents=True, exist_ok=True)
    (dest / FOLDER_A / "text.md").write_text(
        _unit_text(UNIT_A, "Unit A", "synthetic body A"), encoding="utf-8"
    )
    (dest / FOLDER_B / "text.md").write_text(
        _unit_text(UNIT_B, "Unit B", "synthetic body B"), encoding="utf-8"
    )
    text_a = file_hash(dest / FOLDER_A / "text.md")
    text_b = file_hash(dest / FOLDER_B / "text.md")

    # Leaf records: sources, result row, rule pack.
    src1 = {
        "schema_version": "0.2",
        "id": "S-0001",
        "title": "Source 1",
        "fulltext": {"sha256": "a" * 64},
    }
    src2 = {
        "schema_version": "0.2",
        "id": "S-0002",
        "title": "Source 2",
        "fulltext": {"sha256": "b" * 64},
    }
    result = {
        "schema_version": "0.2",
        "id": "RR-0001-0001",
        "run_id": "R-0001",
        "variable_or_metric": "accuracy",
        "value": 0.5,
        "unit": "ratio",
    }
    rulepack = {"schema_version": "0.2", "id": "ua-mon-phd", "version": "2026-10-27"}
    _wj(dest / "sources" / "S-0001.json", src1)
    _wj(dest / "sources" / "S-0002.json", src2)
    _wj(dest / "analysis" / "results" / "RR-0001-0001.json", result)
    _wj(dest / "rules" / "ua-mon-phd.json", rulepack)
    h_src1, h_src2 = canonical_json_hash(src1), canonical_json_hash(src2)
    h_result, h_rulepack = canonical_json_hash(result), canonical_json_hash(rulepack)

    # Excerpts (derived from sources).
    exc1 = {
        "schema_version": "0.2",
        "id": "E-00001",
        "source_id": "S-0001",
        "source_sha256": h_src1,
        "text": "x1",
    }
    exc2 = {
        "schema_version": "0.2",
        "id": "E-00002",
        "source_id": "S-0002",
        "source_sha256": h_src2,
        "text": "x2",
    }
    _wj(dest / "sources" / "excerpts" / "E-00001.json", exc1)
    _wj(dest / "sources" / "excerpts" / "E-00002.json", exc2)
    h_exc1, h_exc2 = canonical_json_hash(exc1), canonical_json_hash(exc2)

    # Claims (cite excerpts / result + their unit text).
    c1 = {
        "schema_version": "0.2",
        "id": "C-0001",
        "unit_id": UNIT_A,
        "kind": "external",
        "evidence": [{"type": "excerpt", "id": "E-00001"}],
        "dependencies": [
            {"ref": f"unit:{UNIT_A}/text", "sha256": text_a},
            {"ref": "excerpt:E-00001", "sha256": h_exc1},
        ],
    }
    c2 = {
        "schema_version": "0.2",
        "id": "C-0002",
        "unit_id": UNIT_B,
        "kind": "external",
        "evidence": [{"type": "excerpt", "id": "E-00002"}],
        "dependencies": [
            {"ref": f"unit:{UNIT_B}/text", "sha256": text_b},
            {"ref": "excerpt:E-00002", "sha256": h_exc2},
        ],
    }
    c3 = {
        "schema_version": "0.2",
        "id": "C-0003",
        "unit_id": UNIT_A,
        "kind": "own_numeric",
        "result_ref": "result:RR-0001-0001",
        "dependencies": [
            {"ref": f"unit:{UNIT_A}/text", "sha256": text_a},
            {"ref": "result:RR-0001-0001", "sha256": h_result},
        ],
    }
    _wj(dest / FOLDER_A / "claims.json", [c1, c3])
    _wj(dest / FOLDER_B / "claims.json", [c2])
    h_c1, h_c2, h_c3 = canonical_json_hash(c1), canonical_json_hash(c2), canonical_json_hash(c3)

    # Check run over every claim + the rule pack.
    check_run = {
        "schema_version": "0.2",
        "id": "CR-0001",
        "checks": [{"id": "UA-SELFPLAG-01", "version": "1"}],
        "inputs": [
            {"ref": "claim:C-0001", "sha256": h_c1},
            {"ref": "claim:C-0002", "sha256": h_c2},
            {"ref": "claim:C-0003", "sha256": h_c3},
            {"ref": "rulepack:ua-mon-phd", "sha256": h_rulepack},
        ],
        "results": [
            {"check_id": "UA-SELFPLAG-01", "item_ref": "claim:C-0001", "result": "pass"},
            {"check_id": "UA-SELFPLAG-01", "item_ref": "claim:C-0002", "result": "pass"},
            {"check_id": "UA-SELFPLAG-01", "item_ref": "claim:C-0003", "result": "pass"},
        ],
    }
    _wj(dest / "analysis" / "checks" / "CR-0001.json", check_run)

    # Commit S1 (the approval's target), then add a G3 approval bound to it.
    store = Store(dest)
    store.init(HUMAN)
    s1 = store.checkpoint(by="human", note="F5b baseline (synthetic)").snapshot_id
    s1_manifest = snap.load_snapshot(dest, s1)["manifest_sha256"]
    approval = {
        "schema_version": "0.2",
        "id": "AP-0001",
        "gate": "G3",
        "target": {
            "snapshot_id": s1,
            "manifest_sha256": s1_manifest,
            "refs": [f"unit:{UNIT_A}/text"],
        },
        "decision": "approved",
        "reason": "synthetic",
        "actor_role": "author",
        "actor_label": "fixture",
        "channel": "tty_confirmation",
        "producer": HUMAN,
    }
    _wj(dest / "approvals" / "AP-0001.json", approval)
    store.checkpoint(by="human", note="F5b approval (synthetic)")
    return dest
