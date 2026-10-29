"""The state store: commit protocol, idempotency, checkpoints (02 §5.3–§5.6).

A :class:`Store` is bound to an object root (the folder containing ``.rh/``).
Workspace/object resolution is added in M1-06; here the root is given directly.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import BlockedError, InvalidInputError
from research_harness.core.hashing import (
    TEXT_SUFFIXES,
    canonical_json_hash,
    file_hash,
    normalize_text_bytes,
)
from research_harness.core.ids import new_operation_id, new_snapshot_id
from research_harness.state import dirty as dirtymod
from research_harness.state import snapshot as snap
from research_harness.state.events import append_event, make_event
from research_harness.state.faults import fault_point
from research_harness.state.lock import acquire, release
from research_harness.state.recovery import recover

CONFIG_SIGNATURE = "research_harness"  # part of the idempotency key (config hash)


@dataclass
class CommitResult:
    snapshot_id: str
    reused: bool
    findings: list[dict[str, Any]]
    unattributed_snapshot: str | None = None


class Store:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    # --- paths ---
    @property
    def rhd(self) -> Path:
        return self.root / ".rh"

    @property
    def lock_path(self) -> Path:
        return self.rhd / "lock"

    @property
    def events_path(self) -> Path:
        return self.rhd / "events.jsonl"

    def _ensure_dirs(self) -> None:
        for sub in ("objects", "snapshots", "staging", "quarantine"):
            (self.rhd / sub).mkdir(parents=True, exist_ok=True)

    # --- file set / idempotency ---
    def _compute_files(self, staged: dict[str, bytes] | None) -> list[dict[str, Any]]:
        staged = staged or {}
        entries: dict[str, dict[str, Any]] = {}
        for rel, stored in snap.managed_files(self.root):
            if rel in staged:
                continue  # staged override computed below
            p = self.root / rel
            entries[rel] = {
                "path": rel,
                "sha256": file_hash(p),
                "size": p.stat().st_size,
                "stored": stored,
            }
        for rel, data in staged.items():
            stored = not any(rel.startswith(pre) for pre in snap.STORED_FALSE_PREFIXES)
            if Path(rel).suffix.lower() in TEXT_SUFFIXES:
                hashed = hashlib.sha256(normalize_text_bytes(data)).hexdigest()
            else:
                hashed = hashlib.sha256(data).hexdigest()
            entries[rel] = {"path": rel, "sha256": hashed, "size": len(data), "stored": stored}
        return [entries[k] for k in sorted(entries)]

    @staticmethod
    def _idempotency_key(command: str, args: dict[str, Any], files: list[dict[str, Any]]) -> str:
        signature = {
            "command": command,
            "args": args,
            "config": CONFIG_SIGNATURE,
            "files": [[e["path"], e["sha256"]] for e in files],
        }
        return canonical_json_hash(signature)

    def _find_by_key(self, key: str) -> str | None:
        for s in snap.all_snapshots(self.root):
            if s.get("operation", {}).get("idempotency_key") == key:
                return s["id"]
        return None

    # --- commit ---
    def commit(
        self,
        *,
        command: str,
        args: dict[str, Any] | None,
        producer: dict[str, Any],
        staged: dict[str, bytes] | None = None,
        write_set: set[str] | None = None,
        request: str | None = None,
        tags: list[str] | None = None,
        is_checkpoint: bool = False,
    ) -> CommitResult:
        args = args or {}
        self._ensure_dirs()

        fault_point("recovery_lock")
        findings = recover(self.root, repair=True)
        op_id = new_operation_id()
        acquire(self.lock_path, op_id, command)
        unattributed: str | None = None
        try:
            fault_point("dirty_check")
            dirty = dirtymod.dirty_set(self.root)
            if not is_checkpoint:
                ws = write_set or (set(staged) if staged else set())
                outside = dirty - ws
                if outside:
                    unattributed = self._snapshot_tree(
                        command="checkpoint",
                        args={"auto": "unattributed"},
                        producer={"kind": "unattributed", "name": "rh", "version": "0.1.0"},
                        request=None,
                    )
                    findings.append(
                        {
                            "check_id": "state.unattributed_recorded",
                            "severity": "info",
                            "reason": f"recorded {len(outside)} unattributed change(s) first",
                        }
                    )
                overlap = dirty & ws
                if overlap:
                    raise BlockedError("error.dirty_overlap", params={"n": len(overlap)})

            # staging
            fault_point("staging")
            if staged:
                staging_dir = self.rhd / "staging" / op_id
                for rel, data in staged.items():
                    dest = staging_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)

            files = self._compute_files(staged)
            key = self._idempotency_key(command, args, files)
            existing = self._find_by_key(key)
            if existing is not None:
                shutil.rmtree(self.rhd / "staging" / op_id, ignore_errors=True)
                return CommitResult(
                    existing, reused=True, findings=findings, unattributed_snapshot=unattributed
                )

            parent = snap.read_current(self.root)
            operation = {
                "id": op_id,
                "command": command,
                "args_normalized": args,
                "idempotency_key": key,
            }
            if request is not None:
                operation["request"] = request
            manifest = self._assemble_manifest(files, operation, producer, parent, tags)

            fault_point("blobs")
            self._write_blobs(manifest, staged)

            fault_point("snapshot")
            snap.write_snapshot(self.root, manifest)  # COMMIT POINT

            fault_point("materialize")
            if staged:
                for rel, data in staged.items():
                    snap.atomic_write_bytes(self.root / rel, data)

            fault_point("current")
            snap.write_current(self.root, manifest["id"])

            fault_point("event")
            append_event(
                self.events_path,
                make_event(
                    "commit", snapshot_id=manifest["id"], operation_id=op_id, command=command
                ),
            )

            fault_point("cleanup")
            shutil.rmtree(self.rhd / "staging" / op_id, ignore_errors=True)
            return CommitResult(
                manifest["id"], reused=False, findings=findings, unattributed_snapshot=unattributed
            )
        finally:
            release(self.lock_path)

    def _assemble_manifest(
        self,
        files: list[dict[str, Any]],
        operation: dict[str, Any],
        producer: dict[str, Any],
        parent: str | None,
        tags: list[str] | None,
    ) -> dict[str, Any]:
        manifest: dict[str, Any] = {
            "schema_version": "0.2",
            "id": new_snapshot_id(),
            "created_at": default_clock().now_rfc3339(),
            "producer": producer,
            "parent": parent,
            "operation": operation,
            "files": files,
            "tags": tags or [],
        }
        manifest["manifest_sha256"] = canonical_json_hash(manifest)
        return manifest

    def _write_blobs(self, manifest: dict[str, Any], staged: dict[str, bytes] | None) -> None:
        staged = staged or {}
        for entry in manifest["files"]:
            if not entry["stored"]:
                continue
            bp = snap.blob_path(self.root, entry["sha256"])
            if bp.exists():
                continue
            rel = entry["path"]
            data = staged[rel] if rel in staged else (self.root / rel).read_bytes()
            snap.atomic_write_bytes(bp, data)

    def _snapshot_tree(
        self, *, command: str, args: dict[str, Any], producer: dict[str, Any], request: str | None
    ) -> str:
        """Commit the current working tree as-is (used for checkpoints)."""
        files = self._compute_files(None)
        key = self._idempotency_key(command, args, files)
        existing = self._find_by_key(key)
        if existing is not None:
            return existing
        parent = snap.read_current(self.root)
        operation = {
            "id": new_operation_id(),
            "command": command,
            "args_normalized": args,
            "idempotency_key": key,
        }
        if request is not None:
            operation["request"] = request
        manifest = self._assemble_manifest(files, operation, producer, parent, None)
        self._write_blobs(manifest, None)
        snap.write_snapshot(self.root, manifest)
        snap.write_current(self.root, manifest["id"])
        append_event(
            self.events_path,
            make_event(
                "commit", snapshot_id=manifest["id"], operation_id=operation["id"], command=command
            ),
        )
        return manifest["id"]

    # --- high-level operations ---
    def init(self, producer: dict[str, Any]) -> CommitResult:
        self._ensure_dirs()
        return self.commit(command="init", args={}, producer=producer, is_checkpoint=True)

    def checkpoint(
        self,
        *,
        by: str,
        request: str | None = None,
        units: list[str] | None = None,
        note: str | None = None,
    ) -> CommitResult:
        if by == "agent" and not request:
            raise InvalidInputError("error.checkpoint_request_required")
        producer = {"kind": "human" if by == "human" else "model", "name": "rh", "version": "0.1.0"}
        args: dict[str, Any] = {"by": by}
        if units:
            args["units"] = sorted(units)
        if note:
            args["message"] = note
        return self.commit(
            command="checkpoint", args=args, producer=producer, request=request, is_checkpoint=True
        )

    def history(self) -> list[dict[str, Any]]:
        snaps = sorted(snap.all_snapshots(self.root), key=lambda s: (s["created_at"], s["id"]))
        out = []
        for s in snaps:
            op = s.get("operation", {})
            out.append(
                {
                    "snapshot_id": s["id"],
                    "command": op.get("command"),
                    "producer": s.get("producer", {}),
                    "request": op.get("request"),
                    "created_at": s["created_at"],
                    "parent": s.get("parent"),
                }
            )
        return out
