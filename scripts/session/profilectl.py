#!/usr/bin/python3
"""Switch two KDE Plasma visual profiles before startplasma-wayland starts.

Both profiles use the SAME Linux account and share applications, documents,
browser data and user services. Only an explicit allowlist of KDE UI config
files is switched. Never run two concurrent Plasma sessions of one user.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

FILES = (
    "kwinrc",
    "kdeglobals",
    "kglobalshortcutsrc",
    "plasmarc",
    "plasmashellrc",
    "plasma-org.kde.plasma.desktop-appletsrc",
)
PROFILES = ("original", "rice")
SYSTEMD_NAMES = {"plasmashell", "kwin_wayland", "kwin_x11"}
STATE_FOLDER = ".local/state/munhof-kde-ricing/profiles"


class ProfileError(RuntimeError):
    """Switch cannot be performed safely."""


def _atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _safe_file(path: Path) -> bool:
    if path.is_symlink():
        raise ProfileError(f"Refusing symlink in managed configuration: {path}")
    if not path.exists():
        return False
    if not path.is_file():
        raise ProfileError(f"Expected regular configuration file: {path}")
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ProfileError(f"Configuration file too large: {path}")
    return True


def running_plasma(uid: int) -> list[int]:
    """Reject simultaneous GUI instances; systemd user manager alone is allowed."""
    pids: list[int] = []
    for candidate in Path("/proc").iterdir():
        if not candidate.name.isdecimal():
            continue
        try:
            if candidate.stat().st_uid != uid:
                continue
            name = (candidate / "comm").read_text(encoding="utf-8").strip()
            if name in SYSTEMD_NAMES:
                pids.append(int(candidate.name))
        except (OSError, ProcessLookupError):
            continue
    return sorted(pids)


class ProfileManager:
    def __init__(self, home: Path):
        self.home = home
        self.config = home / ".config"
        self.root = home / STATE_FOLDER
        self.state = self.root / "state.json"
        self.pending = self.root / "pending.json"
        self.snapshots = self.root / "snapshots"

    def _read_json(self, path: Path) -> dict:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ProfileError(f"Invalid state JSON: {path}")
        return data

    def _snapshot(self) -> str:
        """Immutable snapshot; absence of a file is stored explicitly."""
        sid = uuid.uuid4().hex
        dest = self.snapshots / sid
        dest.mkdir(parents=True, mode=0o700)
        present = []
        for name in FILES:
            source = self.config / name
            if _safe_file(source):
                shutil.copy2(source, dest / name, follow_symlinks=False)
                (dest / name).chmod(0o600)
                present.append(name)
        _atomic_write(dest / "manifest.json", json.dumps({
            "schema": 1, "present": present,
        }).encode())
        return sid

    def _restore(self, sid: str) -> None:
        if not isinstance(sid, str) or len(sid) != 32 or not all(
            c in "0123456789abcdef" for c in sid
        ):
            raise ProfileError("Invalid snapshot reference")
        dest = self.snapshots / sid
        descriptor = self._read_json(dest / "manifest.json")
        present = descriptor.get("present")
        if descriptor.get("schema") != 1 or not isinstance(present, list):
            raise ProfileError("Corrupt profile snapshot")
        if len(present) != len(set(present)) or any(name not in FILES for name in present):
            raise ProfileError("Snapshot contains unexpected configuration paths")
        # Validate ALL managed targets before writing any of them.
        for name in FILES:
            _safe_file(self.config / name)
            if name in present and not _safe_file(dest / name):
                raise ProfileError(f"Missing snapshot data for {name}")
        self.config.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in FILES:
            target = self.config / name
            if name in present:
                _atomic_write(target, (dest / name).read_bytes())
            else:
                target.unlink(missing_ok=True)

    def _write_state(self, state: dict) -> None:
        _atomic_write(self.state, json.dumps(state, indent=2).encode())

    def _recover(self) -> None:
        if not self.pending.exists():
            return
        transaction = self._read_json(self.pending)
        if transaction.get("schema") != 1:
            raise ProfileError("Corrupt pending recovery transaction")
        self._restore(transaction["live_snapshot"])
        self._write_state(transaction["previous"])
        self.pending.unlink()

    def read_state(self) -> dict | None:
        if not self.state.exists():
            return None
        info = self._read_json(self.state)
        if (info.get("schema") != 1 or info.get("active") not in PROFILES
                or set(info.get("snapshots", {})) != set(PROFILES)):
            raise ProfileError("Corrupt profile state")
        return info

    def activate(self, target: str, check_processes: bool = True) -> dict:
        if target not in PROFILES:
            raise ProfileError("Target must be original or rice")
        if os.geteuid() == 0:
            raise ProfileError("Never run profile switching as root")
        if (self.config.is_symlink() or self.root.is_symlink()
                or self.snapshots.is_symlink() or self.snapshots.parent.is_symlink()):
            raise ProfileError("Refusing symlinked profile storage or config directory")
        if check_processes:
            pids = running_plasma(os.getuid())
            if pids:
                raise ProfileError(
                    "Another Plasma session is active (PIDs: "
                    + ", ".join(map(str, pids)) + "). Log out completely first."
                )
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.snapshots.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.root / ".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self._recover()
            current = self.read_state()
            if current is None:
                initial = self._snapshot()
                current = {"schema": 1, "active": "original",
                           "snapshots": {"original": initial, "rice": initial}}
                self._write_state(current)
            if current["active"] == target:
                return {"profile": target, "changed": False}
            outgoing = self._snapshot()
            pending = {"schema": 1, "previous": current,
                       "live_snapshot": outgoing, "target": target}
            _atomic_write(self.pending, json.dumps(pending).encode())
            next_state = json.loads(json.dumps(current))
            next_state["snapshots"][current["active"]] = outgoing
            try:
                self._restore(next_state["snapshots"][target])
                next_state["active"] = target
                self._write_state(next_state)
                self.pending.unlink()
            except Exception:
                self._recover()
                raise
            return {"profile": target, "changed": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("activate", "status", "restore-original"))
    parser.add_argument("profile", nargs="?", choices=PROFILES)
    args = parser.parse_args(argv)
    manager = ProfileManager(Path.home())
    try:
        if args.action == "status":
            print(json.dumps(manager.read_state(), indent=2))
            if manager.pending.exists():
                print("WARNING: interrupted switch pending recovery")
            return 0
        if args.action == "activate" and args.profile is None:
            raise ProfileError("activate requires original or rice")
        target = "original" if args.action == "restore-original" else args.profile
        info = manager.activate(target)
        print("Plasma profile selected: " + info["profile"], file=sys.stderr)
        return 0
    except (OSError, ValueError, ProfileError) as exc:
        print(f"Plasma profile error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
