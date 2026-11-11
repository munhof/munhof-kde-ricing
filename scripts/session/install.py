"""Install a separate Plasma Rice Wayland session for a dedicated Linux user.

Plan mode is read-only. --apply only installs files; it never edits an existing
user's desktop, passwords, or account and never enables autologin.
"""
from __future__ import annotations

import argparse
import os
import pwd
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

SESSION_NAME = "munhof-plasma-rice.desktop"
INSTALL_BIN = Path("/usr/local/libexec/munhof-plasma-rice-session")
BOOTSTRAP_BIN = Path("/usr/local/libexec/munhof-plasma-rice-first-run")
RECIPE_PATH = Path("/usr/local/share/munhof-kde-ricing/recipe.json")
ACCOUNT_PATH = Path("/usr/local/share/munhof-kde-ricing/account")
SESSION_DESKTOP = Path("/usr/share/wayland-sessions") / SESSION_NAME
AUTOSTART_NAME = "munhof-plasma-rice-first-run.desktop"
ACCOUNT_PATTERN = re.compile(r"[a-z_][a-z0-9_-]*\Z")
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Installation:
    account: str
    home: Path
    uid: int
    gid: int
    files: dict[Path, tuple[bytes, int, bool]]


def account_info(name: str, sudo_user: str | None = None) -> pwd.struct_passwd:
    if not ACCOUNT_PATTERN.fullmatch(name):
        raise ValueError("Invalid account name")
    if name == "root" or name == sudo_user:
        raise ValueError("Use a dedicated test account, never root or your usual account")
    try:
        entry = pwd.getpwnam(name)
    except KeyError as exc:
        raise ValueError(
            f"The dedicated account {name!r} does not exist. "
            f"Create it explicitly: sudo useradd -m -s /bin/bash {name}"
        ) from exc
    home = Path(entry.pw_dir)
    if entry.pw_uid == 0 or not home.is_dir() or home.is_symlink():
        raise ValueError("Dedicated account must have an existing, non-symlink home")
    # The installer runs as root; never follow autostart directory symlinks
    # supplied by an unprivileged account.
    for directory in (home / ".config", home / ".config/autostart"):
        if directory.is_symlink():
            raise ValueError("Refusing to follow a user-provided config directory symlink")
    return entry


def build_installation(account: str, source: Path = ROOT,
                       sudo_user: str | None = None) -> Installation:
    entry = account_info(account, sudo_user)
    home = Path(entry.pw_dir)
    launcher = (source / "session/wayland-session.sh").read_text(encoding="utf-8")
    launcher = launcher.replace("@RICE_ACCOUNT@", account)
    content: dict[Path, tuple[bytes, int, bool]] = {
        INSTALL_BIN: (launcher.encode(), 0o755, False),
        BOOTSTRAP_BIN: ((source / "scripts/session/bootstrap.py").read_bytes(), 0o755, False),
        RECIPE_PATH: ((source / "session/recipe.json").read_bytes(), 0o644, False),
        ACCOUNT_PATH: ((account + "\n").encode(), 0o644, False),
        SESSION_DESKTOP: ((source / "session/wayland-session.desktop").read_bytes(), 0o644, False),
        home / ".config/autostart" / AUTOSTART_NAME:
            ((source / "session/first-run.desktop").read_bytes(), 0o644, True),
    }
    return Installation(account, home, entry.pw_uid, entry.pw_gid, content)


def apply(installation: Installation) -> list[Path]:
    """Refuse every existing conflict before writing anything."""
    if os.geteuid() != 0:
        raise PermissionError("--apply requires root; run with sudo")
    if shutil.which("startplasma-wayland") is None:
        raise RuntimeError("startplasma-wayland not installed")
    conflicts = [path for path, (content, _, _) in installation.files.items()
                 if path.exists() and (path.is_symlink() or path.read_bytes() != content)]
    if conflicts:
        raise FileExistsError("Refusing to overwrite existing files: " + ", ".join(map(str, conflicts)))
    created: list[Path] = []
    for path, (content, mode, is_home_file) in installation.files.items():
        if path.exists():
            continue
        missing: list[Path] = []
        current = path.parent
        while not current.exists():
            missing.append(current)
            current = current.parent
        for folder in reversed(missing):
            folder.mkdir(mode=0o755)
            if is_home_file:
                os.chown(folder, installation.uid, installation.gid)
        # O_EXCL prevents silently replacing an existing file or symlink.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.chmod(path, mode)
        if is_home_file:
            os.chown(path, installation.uid, installation.gid)
        created.append(path)
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default="kde-rice", help="Dedicated test account")
    parser.add_argument("--apply", action="store_true", help="Install files (requires sudo)")
    args = parser.parse_args(argv)
    try:
        install = build_installation(args.user, sudo_user=os.environ.get("SUDO_USER"))
        print("Plasma Rice isolated session installation:")
        print(f"  Dedicated account: {install.account} ({install.home})")
        for target in install.files:
            print(f"  {'EXISTS' if target.exists() else 'CREATE'} {target}")
        if not args.apply:
            print("DRY RUN: no modifications. To execute, use sudo python3 scripts/session/install.py --apply")
            return 0
        created = apply(install)
        print(f"Installed {len(created)} files. No existing KDE user settings were changed.")
        print("Set the test account password if needed: sudo passwd " + install.account)
        print("Log out and select 'Plasma Rice (Wayland)' with user " + install.account)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Installation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
