"""F5b (part): a synthetic object root with snapshots and checkpoints.

Used by M1-04 (state), M1-05 (freshness) and M1-11 (status). Output is synthetic
(H6). The full F5b — objects at A0/A2/A12/A14/A16 — is extended by those cards.
"""

from __future__ import annotations

from pathlib import Path

from research_harness.state.store import Store

HUMAN = {"kind": "human", "name": "fixture", "version": "0.1.0"}
AGENT = {"kind": "model", "name": "fixture", "version": "0.1.0"}


def build_object_with_checkpoints(dest: Path) -> Path:
    """Create an object root, an initial snapshot, and two author checkpoints."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "object.json").write_text('{"synthetic": true}\n', encoding="utf-8")
    store = Store(dest)
    store.init(HUMAN)

    unit = dest / "manuscript" / "01 Вступ"
    unit.mkdir(parents=True, exist_ok=True)
    (unit / "text.md").write_text("# Вступ\n\nsynthetic\n", encoding="utf-8")
    store.checkpoint(by="human", message="add intro (synthetic)")

    (unit / "text.md").write_text("# Вступ\n\nsynthetic, revised\n", encoding="utf-8")
    store.checkpoint(by="agent", request="розшир вступ (synthetic)")
    return dest
