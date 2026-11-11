"""Read-only compatibility checks."""
from __future__ import annotations

import os
import re
import shutil
import subprocess


def inspect_system() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    wayland = os.getenv("XDG_SESSION_TYPE", "").lower() == "wayland"
    checks.append(("Wayland session", wayland, os.getenv("XDG_SESSION_TYPE", "unknown")))
    desktop = os.getenv("XDG_CURRENT_DESKTOP", "unknown")
    plasma = "kde" in desktop.lower() or "plasma" in desktop.lower()
    checks.append(("KDE Plasma session", plasma, desktop))
    for cmd in ("kreadconfig6", "kwriteconfig6", "kpackagetool6", "qdbus6"):
        path = shutil.which(cmd)
        checks.append((cmd, bool(path), path or "missing"))
    if shutil.which("plasmashell"):
        result = subprocess.run(["plasmashell", "--version"], check=False, text=True, capture_output=True)
        version = result.stdout.strip() or result.stderr.strip()
        match = re.search(r"(\d+)\.(\d+)", version)
        valid = bool(match and int(match.group(1)) >= 6)
        checks.append(("Plasma 6", valid, version))
    else:
        checks.append(("Plasma 6", False, "plasmashell missing"))
    return checks


def check_requirements(requirements: dict[str, dict]) -> list[str]:
    """Verify prerequisites; never install packages or external scripts."""
    errors: list[str] = []
    for name, req in requirements.items():
        for command in req.get("commands", []):
            if not shutil.which(command):
                errors.append(f"{name}: required executable missing: {command}")
        script = req.get("kwin_script")
        if script:
            if not shutil.which("kpackagetool6"):
                continue
            result = subprocess.run(["kpackagetool6", "--type=KWin/Script", "--list"],
                                    check=False, text=True, capture_output=True)
            if result.returncode != 0 or not re.search(rf"\b{re.escape(script)}\b",
                                                         result.stdout, flags=re.IGNORECASE):
                errors.append(f"{name}: install KWin script '{script}' in System Settings first")
    return errors
