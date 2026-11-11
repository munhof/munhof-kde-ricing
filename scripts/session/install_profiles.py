#!/usr/bin/python3
"""Install two managed KDE Wayland sessions for one existing, ordinary user.

This does not change existing Plasma settings. First profile capture occurs at
the next managed SDDM login, after the original session has logged out.
"""
from __future__ import annotations

import argparse
import os
import pwd
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER_PATTERN = re.compile(r"[a-z_][a-z0-9_-]*\Z")
WAYLAND_DIR = Path("/usr/share/wayland-sessions")
LIBEXEC_DIR = Path("/usr/local/libexec")
DATA_DIR = Path("/usr/local/share/munhof-kde-ricing")
USER_START = "munhof-plasma-rice-profile-first-run.desktop"


@dataclass(frozen=True)
class FileSpec:
    path: Path
    data: bytes
    mode: int
    home_owned: bool = False


def user_info(name: str, sudo_user: str | None) -> pwd.struct_passwd:
    if not USER_PATTERN.fullmatch(name) or name == "root":
        raise ValueError("Invalid ordinary account name")
    if sudo_user and sudo_user != name:
        raise ValueError("Installer may only target the invoking sudo user")
    try:
        account = pwd.getpwnam(name)
    except KeyError as exc:
        raise ValueError("User account does not exist") from exc
    home = Path(account.pw_dir)
    if (account.pw_uid < 1000 or home != Path("/home") / name
            or home.is_symlink() or not home.is_dir()):
        raise ValueError("Target must be an existing, non-root /home/<user> account")
    for parent in (home / ".config", home / ".config/autostart"):
        if parent.is_symlink():
            raise ValueError(f"Refusing symlinked directory: {parent}")
    return account


def planned_files(user: str, source: Path = ROOT,
                  sudo_user: str | None = None) -> tuple[pwd.struct_passwd, list[FileSpec]]:
    acct = user_info(user, sudo_user)
    manifest = [
        ("session/managed-original.desktop",
         WAYLAND_DIR / "munhof-plasma-original.desktop", 0o644, False),
        ("session/managed-rice.desktop",
         WAYLAND_DIR / "munhof-plasma-rice-managed.desktop", 0o644, False),
        ("session/managed-session.sh",
         LIBEXEC_DIR / "munhof-plasma-rice-managed-session", 0o755, False),
        ("scripts/session/profilectl.py",
         LIBEXEC_DIR / "munhof-plasma-rice-profilectl", 0o755, False),
        ("scripts/session/bootstrap.py",
         LIBEXEC_DIR / "munhof-plasma-rice-profile-first-run", 0o755, False),
        ("session/profile-first-run.desktop",
         Path(acct.pw_dir) / ".config/autostart" / USER_START, 0o644, True),
        ("session/recipe.json",
         DATA_DIR / "recipe.json", 0o644, False),
    ]
    return acct, [
        FileSpec(target, (source / relative).read_bytes(), mode, home_owned)
        for relative, target, mode, home_owned in manifest
    ]


def _matches(file: FileSpec) -> bool:
    return file.path.is_file() and not file.path.is_symlink() and (
        file.path.read_bytes() == file.data
    )


def install(account: pwd.struct_passwd, files: list[FileSpec]) -> list[Path]:
    if os.geteuid() != 0:
        raise PermissionError("Installing SDDM session entries requires sudo")
    if not Path("/usr/bin/startplasma-wayland").is_file():
        raise RuntimeError("Missing /usr/bin/startplasma-wayland")
    # Refuse ALL pre-existing conflicts before creating ANY file.
    conflicts = [str(f.path) for f in files if (f.path.exists() or f.path.is_symlink())
                 and not _matches(f)]
    if conflicts:
        raise FileExistsError("Refusing to overwrite existing files: " + ", ".join(conflicts))
    created: list[Path] = []
    try:
        for item in files:
            if _matches(item):
                continue
            for parent in reversed(_missing_parents(item.path.parent)):
                parent.mkdir(mode=0o755)
                if item.home_owned:
                    os.chown(parent, account.pw_uid, account.pw_gid)
            fd = os.open(item.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, item.mode)
            with os.fdopen(fd, "wb") as stream:
                stream.write(item.data)
            os.chmod(item.path, item.mode)
            if item.home_owned:
                os.chown(item.path, account.pw_uid, account.pw_gid)
            created.append(item.path)
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return created


def _missing_parents(path: Path) -> list[Path]:
    missing: list[Path] = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    if path.is_symlink():
        raise ValueError("Refusing symlinked installation parent")
    return missing


def uninstall(files: list[FileSpec]) -> list[Path]:
    if os.geteuid() != 0:
        raise PermissionError("Uninstall requires sudo")
    removed = []
    # Preserve recipe.json: it may also be used by the optional recovery session.
    for item in files:
        if item.path == DATA_DIR / "recipe.json":
            continue
        if item.path.exists() and not _matches(item):
            raise FileExistsError(f"Uninstall refused modified file: {item.path}")
    for item in files:
        if item.path != DATA_DIR / "recipe.json" and _matches(item):
            item.path.unlink()
            removed.append(item.path)
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True, help="Your existing Linux account, e.g. munhof")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Install session entries")
    group.add_argument("--uninstall", action="store_true", help="Remove exact installed files")
    args = parser.parse_args(argv)
    try:
        account, files = planned_files(args.user, sudo_user=os.getenv("SUDO_USER"))
        for item in files:
            status = "UNCHANGED" if _matches(item) else "CREATE"
            if item.path.exists() and not _matches(item):
                status = "CONFLICT"
            print(f"{status:10} {item.path}")
        if args.apply:
            paths = install(account, files)
            print(f"Installed {len(paths)} files. KDE visual settings NOT modified.")
            print("Log out, then select Plasma Original (Wayland) or Plasma Rice (Wayland).")
        elif args.uninstall:
            paths = uninstall(files)
            print(f"Uninstalled {len(paths)} managed files. Profile snapshots preserved.")
        else:
            print("DRY RUN: no changes. Use sudo python3 ... --apply to install.")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Session installer error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
