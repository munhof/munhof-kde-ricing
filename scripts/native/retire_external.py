#!/usr/bin/python3
"""Safely disable the retired Waybar launcher and stop only our Waybar process.

No package removal, no global pkill, no changes to Plasma panels, KWin,
Polonium, SDDM, or either profile's stored desktop configuration.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

HOME = Path.home()
AUTOSTART = HOME / ".config/autostart/munhof-rice-appearance.desktop"
STATE = HOME / ".local/state/munhof-kde-ricing/appearance"
WAYBAR_PID = STATE / "waybar.pid"
WAYBAR_ASSETS = HOME / ".local/share/munhof-kde-ricing/appearance/waybar"
LAUNCHER = HOME / ".local/bin/munhof-rice-appearance"
NAME = "Name=Munhof Rice Appearance"


class CleanupError(RuntimeError):
    """Refusing to act on a file or process not owned by the old Rice setup."""


def managed_autostart(path: Path | None = None) -> bool:
    path = path or AUTOSTART
    if path.is_symlink():
        raise CleanupError(f"Autostart is a symlink: {path}")
    if not path.exists():
        return False
    if not path.is_file():
        raise CleanupError(f"Autostart is not a file: {path}")
    contents = path.read_text(encoding="utf-8")
    expected_exec = f"Exec={LAUNCHER} start"
    if NAME not in contents or expected_exec not in contents:
        raise CleanupError(f"Existing autostart is not our managed entry: {path}")
    return True


def managed_waybar_pid(pid_path: Path | None = None) -> int | None:
    pid_path = pid_path or WAYBAR_PID
    if pid_path.is_symlink():
        raise CleanupError(f"Waybar receipt is a symlink: {pid_path}")
    if not pid_path.exists():
        return None
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError as exc:
        raise CleanupError("Invalid managed Waybar receipt") from exc
    if pid < 2:
        raise CleanupError("Invalid managed Waybar PID")
    proc = Path("/proc") / str(pid)
    try:
        cmdline = (proc / "cmdline").read_bytes().split(b"\0")
        args = [a.decode("utf-8", errors="replace") for a in cmdline if a]
    except FileNotFoundError:
        return None  # Stale receipt: process has exited already.
    if not args or Path(args[0]).name != "waybar":
        raise CleanupError(f"PID {pid} is not Waybar; refusing to signal it")
    try:
        config = args[args.index("-c") + 1]
    except (ValueError, IndexError) as exc:
        raise CleanupError(f"PID {pid} is not a managed Waybar instance") from exc
    if config not in {
        str(WAYBAR_ASSETS / "config.jsonc"),
        str(WAYBAR_ASSETS / "tuned-config.json"),
    }:
        raise CleanupError(f"Waybar PID {pid} belongs to a different configuration")
    return pid


def retire(apply: bool = False) -> dict[str, object]:
    if os.geteuid() == 0:
        raise CleanupError("Run as the regular Linux user; never with sudo")
    autostart = managed_autostart()
    pid = managed_waybar_pid()
    print(f"Managed Waybar running: {pid if pid is not None else 'no'}")
    print(f"Managed appearance autostart: {'yes' if autostart else 'no'}")
    print("Plasma panels, KWin and Polonium will remain unchanged.")
    print("Quickshell must be closed in its own terminal (Ctrl+C).")
    if not apply:
        print("DRY RUN: no changes. Use --apply to disable the old appearance.")
        return {"changed": False, "pid": pid, "autostart": autostart}
    if pid is not None:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to our Waybar PID {pid}")
    if WAYBAR_PID.is_file() and not WAYBAR_PID.is_symlink():
        WAYBAR_PID.unlink()
    if autostart:
        AUTOSTART.unlink()
        print("Removed our Waybar autostart entry.")
    print("Legacy packages and configuration files were left untouched.")
    return {"changed": bool(pid is not None or autostart), "pid": pid, "autostart": autostart}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Disable our Waybar only")
    args = parser.parse_args(argv)
    try:
        retire(apply=args.apply)
        return 0
    except (OSError, CleanupError) as exc:
        print(f"Retirement refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
