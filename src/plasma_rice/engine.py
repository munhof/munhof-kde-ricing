"""Transactional key changes with conflict-aware rollback and local receipts."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import ALLOWED_FILES, Operation


@dataclass(frozen=True)
class Change:
    operation: Operation
    before: str | None

    @property
    def changed(self) -> bool:
        return self.before != self.operation.value


def plan(ops: list[Operation], backend) -> list[Change]:
    return [Change(op, backend.read(op.file, op.group, op.key)) for op in ops]


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def apply(changes: list[Change], backend, state_dir: Path, profile: str) -> Path | None:
    actual = [c for c in changes if c.changed]
    if not actual:
        return None
    # Stop on state drift between planning and applying.
    for change in changes:
        op = change.operation
        current = backend.read(op.file, op.group, op.key)
        if current != change.before:
            raise RuntimeError(f"Configuration changed since planning: {op.identity}")
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt = state_dir / "receipts" / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex + ".json"
    )
    payload = {
        "schema": 1,
        "profile": profile,
        "timestamp": datetime.now(UTC).isoformat(),
        "operations": [
            {"component": c.operation.component, "file": c.operation.file,
             "group": c.operation.group, "key": c.operation.key,
             "before": c.before, "after": c.operation.value}
            for c in actual
        ],
    }
    done: list[Change] = []
    try:
        for change in actual:
            op = change.operation
            backend.write(op.file, op.group, op.key, op.value)
            done.append(change)
        _write_json_atomic(receipt, payload)
    except Exception:
        for change in reversed(done):
            op = change.operation
            if backend.read(op.file, op.group, op.key) == op.value:
                backend.write(op.file, op.group, op.key, change.before)
        raise
    return receipt


def latest_receipt(state_dir: Path) -> Path | None:
    directory = state_dir / "receipts"
    files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    return files[-1] if files else None


def rollback(backend, state_dir: Path, receipt: Path | None = None) -> tuple[int, list[str]]:
    receipt = receipt or latest_receipt(state_dir)
    if receipt is None:
        raise FileNotFoundError("No transaction to roll back")
    receipt = receipt.resolve()
    allowed = (state_dir / "receipts").resolve()
    if receipt.parent != allowed:
        raise ValueError("Receipt path is outside transaction directory")
    raw = json.loads(receipt.read_text(encoding="utf-8"))
    if raw.get("schema") != 1:
        raise ValueError("Unsupported transaction format")
    entries = raw.get("operations")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Invalid transaction operations")
    for op in entries:
        if not isinstance(op, dict) or op.get("file") not in ALLOWED_FILES:
            raise ValueError("Unsafe transaction target")
        if any(not isinstance(op.get(k), str) or not op[k] or "\n" in op[k]
               for k in ("group", "key", "after")):
            raise ValueError("Invalid transaction key or value")
        if op.get("before") is not None and not isinstance(op["before"], str):
            raise ValueError("Invalid original transaction value")
    # Full preflight: refuse partial rollback if user changed a managed key.
    conflicts: list[str] = []
    for op in entries:
        current = backend.read(op["file"], op["group"], op["key"])
        if current != op["after"]:
            conflicts.append(f"{op['file']} [{op['group']}] {op['key']}")
    if conflicts:
        return 0, conflicts
    restored = []
    try:
        for op in reversed(entries):
            backend.write(op["file"], op["group"], op["key"], op["before"])
            restored.append(op)
    except Exception:
        # Restore desired state for the part already reverted.
        for op in reversed(restored):
            backend.write(op["file"], op["group"], op["key"], op["after"])
        raise
    # A successful rollback removes the receipt. Other receipts are preserved.
    receipt.unlink()
    return len(restored), []
