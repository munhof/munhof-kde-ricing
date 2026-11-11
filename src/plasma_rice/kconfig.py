"""Use KDE's own KConfig tools; never parse/rewrite complete KDE INI files."""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path


class KConfigBackend:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir

    def read(self, file: str, group: str, key: str) -> str | None:
        # Random default distinguishes nonexistent keys from empty string values.
        sentinel = f"__plasma_rice_missing_{uuid.uuid4().hex}__"
        cmd = ["kreadconfig6", "--file", str(self.config_dir / file),
               "--group", group, "--key", key, "--default", sentinel]
        result = subprocess.run(cmd, text=True, capture_output=True, check=True)
        value = result.stdout.rstrip("\n")
        return None if value == sentinel else value

    def write(self, file: str, group: str, key: str, value: str | None) -> None:
        cmd = ["kwriteconfig6", "--file", str(self.config_dir / file),
               "--group", group, "--key", key]
        if value is None:
            cmd.append("--delete")
        else:
            cmd.append(value)
        subprocess.run(cmd, check=True, text=True, capture_output=True)


def reconfigure_kwin() -> str:
    """Best-effort; a logout/login may still be needed for scripts."""
    import shutil
    tool = shutil.which("qdbus6") or shutil.which("qdbus")
    if not tool:
        return "KWin wasn't notified (qdbus6 not available); log out and back in."
    result = subprocess.run([tool, "org.kde.KWin", "/KWin", "reconfigure"],
                            check=False, capture_output=True, text=True)
    if result.returncode:
        return "KWin reload failed; log out and back in for changes to take effect."
    return "KWin configuration reload requested."
