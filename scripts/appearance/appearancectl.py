#!/usr/bin/python3
"""Experimental Waybar + Wofi appearance for the *managed Rice profile only*.

Safe by default: installing copies assets only into the user's own home.
Starting Waybar never removes Plasma panels. A separate explicit command can
remove the native panels inside Rice after the user verifies Waybar on both
monitors; a backup is saved before removal.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

HOME = Path.home()
DATA = HOME / ".local/share/munhof-kde-ricing/appearance"
STATE = HOME / ".local/state/munhof-kde-ricing/appearance"
PROFILE_STATE = HOME / ".local/state/munhof-kde-ricing/profiles/state.json"
BIN = HOME / ".local/bin/munhof-rice-appearance"
AUTOSTART = HOME / ".config/autostart/munhof-rice-appearance.desktop"
ASSETS = (
    "waybar/config.jsonc", "waybar/style.css", "wofi/config", "wofi/style.css",
)
SOURCE = Path(__file__).resolve().parents[2]
MARKER = "__MUNHOF_RICE__"
SIZING = {
    "compact": (34, 48, 12, 21, 7),
    "balanced": (42, 60, 14, 27, 10),
    "touch": (54, 76, 17, 36, 14),
}
TUNED_BAR = DATA / "waybar/tuned-config.json"
TUNED_STYLE = DATA / "waybar/tuned-style.css"
TUNED_WOFI = DATA / "wofi/tuned-config"
TUNED_WOFI_STYLE = DATA / "wofi/tuned-style.css"



class AppearanceError(RuntimeError):
    """A requested appearance operation cannot be performed safely."""


def active_profile() -> str | None:
    try:
        state = json.loads(PROFILE_STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(state, dict) and state.get("schema") == 1:
        return state.get("active")
    return None


def require_rice() -> None:
    if os.geteuid() == 0:
        raise AppearanceError("Do not run appearance commands with sudo")
    if active_profile() != "rice":
        raise AppearanceError("Start or modify UI only inside managed Plasma Rice (Wayland)")
    if os.getenv("XDG_SESSION_TYPE", "").lower() != "wayland":
        raise AppearanceError("Wayland session required")


def _source_files(source: Path) -> dict[Path, bytes]:
    return {
        DATA / name: (source / "appearance" / name).read_bytes() for name in ASSETS
    } | {BIN: (source / "scripts/appearance/appearancectl.py").read_bytes()}


def install(source: Path = SOURCE, update: bool = False) -> int:
    if os.geteuid() == 0:
        raise AppearanceError("Install as your normal user, not via sudo")
    files = _source_files(source)
    collisions = [path for path, content in files.items()
                  if (path.exists() or path.is_symlink()) and (
                      path.is_symlink() or path.read_bytes() != content
                  )]
    if collisions and not update:
        raise AppearanceError(
            "Existing appearance files differ; use install --update after reviewing: "
            + ", ".join(str(path) for path in collisions)
        )
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.exists() and path.read_bytes() == content:
            continue
        if path.exists() and update:
            backup = STATE / "backups" / stamp / path.relative_to(HOME)
            backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(path, backup)
        temp = path.with_name(path.name + ".new")
        with temp.open("xb") as file:
            file.write(content)
        temp.chmod(0o755 if path == BIN else 0o600)
        temp.replace(path)
    return len(files)


def _pid_file() -> Path:
    return STATE / "waybar.pid"


def _bar_files() -> tuple[Path, Path]:
    if TUNED_BAR.exists() != TUNED_STYLE.exists():
        raise AppearanceError("Incomplete tuned Waybar files; rerun tune --apply")
    if TUNED_BAR.is_file():
        return TUNED_BAR, TUNED_STYLE
    return DATA / "waybar/config.jsonc", DATA / "waybar/style.css"


def _wofi_files() -> tuple[Path, Path]:
    if TUNED_WOFI.exists() != TUNED_WOFI_STYLE.exists():
        raise AppearanceError("Incomplete tuned Wofi files; rerun tune --apply")
    if TUNED_WOFI.is_file():
        return TUNED_WOFI, TUNED_WOFI_STYLE
    return DATA / "wofi/config", DATA / "wofi/style.css"


def managed_waybar_pid() -> int | None:
    try:
        pid = int(_pid_file().read_text(encoding="utf-8"))
        raw = (Path("/proc") / str(pid) / "cmdline").read_bytes().decode(errors="replace")
        if ("waybar" in raw and any(str(p) in raw for p in
                              (DATA / "waybar/config.jsonc", TUNED_BAR))):
            os.kill(pid, 0)
            return pid
    except (OSError, ValueError, ProcessLookupError):
        pass
    return None


def start() -> int:
    require_rice()
    for binary in ("waybar",):
        if shutil.which(binary) is None:
            raise AppearanceError(f"{binary} missing; install via pacman")
    config, style = _bar_files()
    if not config.is_file() or not style.is_file():
        raise AppearanceError("Run install first")
    pid = managed_waybar_pid()
    if pid is not None:
        print(f"Waybar already running: PID {pid}")
        return pid
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    log = STATE / "waybar.log"
    with log.open("ab") as out:
        proc = subprocess.Popen(
            [
                "waybar", "-c", str(config),
                "-s", str(style),
            ],
            stdout=out, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    time.sleep(0.8)
    if proc.poll() is not None:
        raise AppearanceError(f"Waybar exited ({proc.returncode}). Inspect {log}")
    _pid_file().write_text(f"{proc.pid}\n", encoding="utf-8")
    _pid_file().chmod(0o600)
    print(f"Rice Waybar started: PID {proc.pid}. Both connected outputs are targeted.")
    return proc.pid


def stop() -> bool:
    if os.geteuid() == 0:
        raise AppearanceError("Do not run as root")
    pid = managed_waybar_pid()
    if pid is None:
        print("No managed Waybar running.")
        _pid_file().unlink(missing_ok=True)
        return False
    os.kill(pid, signal.SIGTERM)
    _pid_file().unlink(missing_ok=True)
    print(f"Requested stop of managed Waybar PID {pid}")
    return True



def render_tuned(
    bar_config: list[dict], bar_css: str,
    wofi_config: str, wofi_css: str,
    settings: dict[str, int], reserve_space: bool = False,
) -> dict[str, bytes]:
    """Pure sizing renderer: no changes to KDE files, screens or presets."""
    expected = {"bar_height", "dock_height", "font_size", "icon_size", "edge_gap"}
    limits = {
        "bar_height": (28, 80), "dock_height": (40, 96),
        "font_size": (11, 22), "icon_size": (18, 40), "edge_gap": (0, 28),
    }
    if set(settings) != expected:
        raise AppearanceError("Invalid sizing fields")
    for name, (minimum, maximum) in limits.items():
        if type(settings[name]) is not int or not minimum <= settings[name] <= maximum:
            raise AppearanceError(f"{name} must be between {minimum} and {maximum}")
    if settings["dock_height"] < settings["icon_size"] + 13:
        raise AppearanceError("Dock is too short for its icons and padding")
    if not isinstance(bar_config, list) or [
        b.get("name") for b in bar_config if isinstance(b, dict)
    ] != ["rice-topbar", "rice-dock"]:
        raise AppearanceError("Unexpected Waybar template")
    bars = json.loads(json.dumps(bar_config))
    for bar in bars:
        # On KWin/Polonium this zone can displace or overlap tiled windows.
        # Non-exclusive overlays are the safe default; opt in only after testing.
        bar["exclusive"] = reserve_space
        bar["fixed-center"] = True
        bar.pop("output", None)
        bar["margin-left"] = max(12, settings["edge_gap"] + 6)
        bar["margin-right"] = max(12, settings["edge_gap"] + 6)
    bars[0]["height"] = settings["bar_height"]
    bars[0]["margin-top"] = settings["edge_gap"]
    bars[1]["height"] = settings["dock_height"]
    bars[1]["margin-bottom"] = settings["edge_gap"]
    padding = max(5, (settings["dock_height"] - settings["icon_size"] - 12) // 2)
    css = bar_css.rstrip() + f"""

/* Generated by Plasma Rice: sizing overrides */
* {{ font-size: {settings['font_size']}px; }}
#custom-launcher {{ font-size: {settings['font_size'] + 8}px; }}
#custom-identity {{ font-size: {max(settings['font_size'] - 2, 10)}px; }}
#custom-appmenu, #custom-terminal, #custom-browser,
#custom-editor, #custom-files, #custom-runner {{
  font-size: {settings['icon_size']}px;
  padding: {padding}px {padding + 6}px;
}}
"""
    width = settings["font_size"] * 30 + 230
    height = settings["font_size"] * 20 + 270
    replacements = {
        "width": width, "height": height,
        "image_size": settings["font_size"] * 2 + 6,
    }
    lines = []
    found = set()
    for line in wofi_config.splitlines():
        key = line.partition("=")[0].strip()
        if key in replacements:
            lines.append(f"{key}={replacements[key]}")
            found.add(key)
        else:
            lines.append(line)
    lines.extend(f"{key}={value}" for key, value in replacements.items() if key not in found)
    wofi_css += f"""

/* Generated by Plasma Rice: launcher sizing */
* {{ font-size: {settings['font_size'] + 1}px; }}
#input {{ padding: {settings['font_size']}px; }}
#entry {{ padding: {max(6, settings['font_size'] - 3)}px {settings['font_size']}px; }}
"""
    return {
        "waybar/tuned-config.json": (json.dumps(bars, ensure_ascii=False, indent=2) + "\n").encode(),
        "waybar/tuned-style.css": css.encode(),
        "wofi/tuned-config": ("\n".join(lines) + "\n").encode(),
        "wofi/tuned-style.css": wofi_css.encode(),
    }


def _write_tuned(path: Path, content: bytes) -> None:
    if path.is_symlink():
        raise AppearanceError(f"Refusing symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with temp.open("xb") as out:
            out.write(content)
        temp.chmod(0o600)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def tune(
    preset: str = "balanced", overrides: dict[str, int | None] | None = None,
    apply: bool = False, reserve_space: bool = False,
) -> dict[str, int]:
    require_rice()
    if preset not in SIZING:
        raise AppearanceError(f"Unknown sizing preset: {preset}")
    settings = dict(zip(
        ("bar_height", "dock_height", "font_size", "icon_size", "edge_gap"),
        SIZING[preset], strict=True
    ))
    settings.update({name: val for name, val in (overrides or {}).items()
                     if val is not None})
    data = render_tuned(
        json.loads((DATA / "waybar/config.jsonc").read_text(encoding="utf-8")),
        (DATA / "waybar/style.css").read_text(encoding="utf-8"),
        (DATA / "wofi/config").read_text(encoding="utf-8"),
        (DATA / "wofi/style.css").read_text(encoding="utf-8"),
        settings, reserve_space=reserve_space,
    )
    print(f"Visual sizing {preset}: {json.dumps(settings, sort_keys=True)}")
    print(f"Waybar exclusive zone: {reserve_space} (experimental if enabled)")
    if not apply:
        print("Dry run: no changes. Add --apply to generate the active layout.")
        return settings
    # Verify all destinations before any write.
    for relative in data:
        if (DATA / relative).is_symlink():
            raise AppearanceError(f"Refusing symlinked output: {relative}")
    for relative, content in data.items():
        _write_tuned(DATA / relative, content)
    print("Sizing saved. Use 'restart' to reload Waybar.")
    return settings


def restart() -> int:
    require_rice()
    pid = managed_waybar_pid()
    if pid is not None:
        stop()
        for _ in range(20):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            raise AppearanceError("Managed Waybar did not stop; refusing duplicate")
    return start()


def launcher() -> None:
    require_rice()
    config, style = _wofi_files()
    if shutil.which("wofi") is None:
        raise AppearanceError("Wofi is missing; install via pacman")
    result = subprocess.run(
        ["wofi", "--show", "drun", "--conf", str(config),
         "--style", str(style)],
        check=False,
    )
    if result.returncode not in (0, 1):
        raise AppearanceError(f"Wofi exited with status {result.returncode}")


def desktops() -> str:
    if shutil.which("qdbus6") is None:
        return "1  ·  2  ·  3  ·  4"
    result = subprocess.run(
        ["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.currentDesktop"],
        check=False, capture_output=True, text=True, timeout=3,
    )
    try:
        index = int(result.stdout.strip())
    except ValueError:
        index = 1
    return "  ".join(f"● {i}" if i == index else str(i) for i in range(1, 5))


def next_desktop() -> None:
    require_rice()
    subprocess.run(
        ["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.nextDesktop"],
        check=True, timeout=4,
    )


LAUNCHERS = {
    "terminal": ("konsole",),
    "files": ("dolphin",),
    "editor": ("code", "codium", "kate"),
    "browser": ("firefox", "firedragon", "brave", "chromium"),
    "runner": ("krunner",),
}


def launch(kind: str) -> None:
    require_rice()
    candidates = LAUNCHERS[kind]
    executable = next((shutil.which(name) for name in candidates if shutil.which(name)), None)
    if executable is None:
        raise AppearanceError(f"No installed app found for {kind}: {candidates}")
    subprocess.Popen([executable], start_new_session=True)


def enable_autostart() -> None:
    if os.geteuid() == 0:
        raise AppearanceError("Do not run as root")
    if not BIN.is_file():
        raise AppearanceError("Run install first")
    content = (
        "[Desktop Entry]\nType=Application\nName=Munhof Rice Appearance\n"
        "Comment=Only activates Waybar when the managed Rice profile is active\n"
        f"Exec={BIN} start\nOnlyShowIn=KDE;\nX-KDE-autostart-phase=2\n"
    )
    AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    if AUTOSTART.exists() and AUTOSTART.read_text(encoding="utf-8") != content:
        raise AppearanceError(f"Refusing to replace an existing autostart: {AUTOSTART}")
    AUTOSTART.write_text(content, encoding="utf-8")
    print(f"Installed profile-gated autostart: {AUTOSTART}")


def disable_autostart() -> None:
    if AUTOSTART.is_symlink():
        raise AppearanceError("Refusing to delete a symlink")
    if AUTOSTART.is_file():
        content = AUTOSTART.read_text(encoding="utf-8")
        if f"Exec={BIN} start" not in content:
            raise AppearanceError("Autostart differs from our managed entry")
        AUTOSTART.unlink()
    print("Appearance autostart disabled.")


def replace_panels(confirm: bool = False) -> None:
    """Explicit, Rice-only destructive change. Snapshot first, then remove panels."""
    require_rice()
    if not confirm:
        raise AppearanceError(
            "Requires --confirm after verifying Waybar on BOTH displays."
        )
    if managed_waybar_pid() is None:
        raise AppearanceError("Waybar must be visibly running before removing KDE panels")
    source = HOME / ".config/plasma-org.kde.plasma.desktop-appletsrc"
    if not source.is_file() or source.is_symlink():
        raise AppearanceError("Missing or unsafe Plasma panel config")
    backup = STATE / "plasma-panels-before-waybar.ini"
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not backup.exists():
        shutil.copy2(source, backup)
        backup.chmod(0o600)
    script = (
        "var old=panels().slice();"
        "old.forEach(function(p){p.remove();});"
        f"print('{MARKER}'+JSON.stringify({{removed:old.length}}));"
    )
    result = subprocess.run(
        ["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
         "org.kde.PlasmaShell.evaluateScript", script],
        check=False, capture_output=True, text=True, timeout=15,
    )
    if result.returncode or MARKER not in result.stdout:
        raise AppearanceError("Plasma panel removal failed; backup kept at " + str(backup))
    print(result.stdout.split(MARKER, 1)[1])
    print("Only the active Rice layout was modified; Original snapshot remains.")
    print(f"Panel backup: {backup}")


def doctor() -> None:
    print("Active managed profile:", active_profile() or "(uninitialized)")
    print("Wayland:", os.getenv("XDG_SESSION_TYPE"))
    for tool in ("waybar", "wofi", "qdbus6", "pavucontrol", "fc-match"):
        print(f"{tool}: {shutil.which(tool) or '(not installed / optional)'}")
    print("Appearance installed:", BIN.is_file() and all((DATA / name).is_file() for name in ASSETS))
    print("Managed Waybar PID:", managed_waybar_pid())
    print("Autostart enabled:", AUTOSTART.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--update", action="store_true")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("restart")
    sizing = sub.add_parser("tune", help="Preview or apply UI sizing")
    sizing.add_argument("--preset", choices=("compact", "balanced", "touch"),
                        default="balanced")
    sizing.add_argument("--apply", action="store_true")
    sizing.add_argument("--reserve-space", action="store_true",
                        help="EXPERIMENTAL: KWin may conflict with Polonium")
    for key in ("bar_height", "dock_height", "font_size", "icon_size", "edge_gap"):
        sizing.add_argument("--" + key.replace("_", "-"), type=int, default=None)
    sub.add_parser("launcher")
    sub.add_parser("desktops")
    sub.add_parser("next-desktop")
    p = sub.add_parser("launch")
    p.add_argument("app", choices=tuple(LAUNCHERS))
    sub.add_parser("enable-autostart")
    sub.add_parser("disable-autostart")
    replacement = sub.add_parser("replace-panels")
    replacement.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            doctor()
        elif args.command == "install":
            print(f"Installed {install(update=args.update)} user-owned appearance files.")
        elif args.command == "start":
            start()
        elif args.command == "stop":
            stop()
        elif args.command == "restart":
            restart()
        elif args.command == "tune":
            keys = ("bar_height", "dock_height", "font_size", "icon_size", "edge_gap")
            tune(args.preset, {key: getattr(args, key) for key in keys},
                 apply=args.apply, reserve_space=args.reserve_space)
        elif args.command == "launcher":
            launcher()
        elif args.command == "desktops":
            print(desktops())
        elif args.command == "next-desktop":
            next_desktop()
        elif args.command == "launch":
            launch(args.app)
        elif args.command == "enable-autostart":
            enable_autostart()
        elif args.command == "disable-autostart":
            disable_autostart()
        elif args.command == "replace-panels":
            replace_panels(confirm=args.confirm)
        return 0
    except (OSError, ValueError, AppearanceError, subprocess.SubprocessError) as exc:
        print(f"Rice appearance error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
