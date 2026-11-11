#!/usr/bin/python3
"""Initialize Plasma Rice in the dedicated test account, never in the normal account."""
from __future__ import annotations

import argparse
import json
import os
import pwd
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RECIPE = Path("/usr/local/share/munhof-kde-ricing/recipe.json")
ACCOUNT = Path("/usr/local/share/munhof-kde-ricing/account")
MARKER = "__PLASMA_RICE_BOOTSTRAP__"
ALLOWED_LOCATIONS = {"top", "bottom", "left", "right"}
ALLOWED_WIDGETS = {
    "org.kde.plasma.kickoff", "org.kde.plasma.pager", "org.kde.plasma.panelspacer",
    "org.kde.plasma.systemtray", "org.kde.plasma.digitalclock",
    "org.kde.plasma.lock_logout", "org.kde.plasma.icontasks",
    "org.kde.plasma.showdesktop",
}


def validate_recipe(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("Unsupported recipe schema")
    if not isinstance(data.get("id"), str) or not data["id"].replace("-", "").isalnum():
        raise ValueError("Invalid recipe id")
    if data.get("color_scheme") != "BreezeDark" or data.get("desktop_theme") != "breeze-dark":
        raise ValueError("Only known KDE theme names are supported")
    kwin = data.get("kwin")
    if not isinstance(kwin, dict) or set(kwin) != {"Plugins", "Tiling"}:
        raise ValueError("Only approved KWin configuration groups are allowed")
    if set(kwin["Plugins"]) != {"blurEnabled"} or set(kwin["Tiling"]) != {"padding"}:
        raise ValueError("Unsupported KWin settings")
    if kwin["Plugins"]["blurEnabled"] != "true":
        raise ValueError("Blur setting must be true")
    padding = kwin["Tiling"]["padding"]
    if not isinstance(padding, str) or not padding.isdecimal() or not 0 <= int(padding) <= 32:
        raise ValueError("Padding must be between 0 and 32")
    panels = data.get("panels")
    if not isinstance(panels, list) or len(panels) != 2:
        raise ValueError("Expected exactly two panels")
    for panel in panels:
        if not isinstance(panel, dict) or set(panel) != {
            "id", "location", "height", "length_mode", "hiding", "alignment", "widgets"
        }:
            raise ValueError("Unexpected panel fields")
        if panel["id"] not in {"topbar", "dock"} or panel["location"] not in ALLOWED_LOCATIONS:
            raise ValueError("Invalid panel target or location")
        if type(panel["height"]) is not int or not 24 <= panel["height"] <= 64:
            raise ValueError("Panel height out of range")
        if panel["length_mode"] not in {"fill", "fit"}:
            raise ValueError("Unsupported length mode")
        if panel["hiding"] not in {"none", "autohide", "dodgewindows"}:
            raise ValueError("Unsupported hiding mode")
        if panel["alignment"] not in {"center", "left", "right"}:
            raise ValueError("Unsupported alignment")
        if not isinstance(panel["widgets"], list) or not 1 <= len(panel["widgets"]) <= 12:
            raise ValueError("A panel must have 1-12 widgets")
        if any(type(widget) is not str or widget not in ALLOWED_WIDGETS
               for widget in panel["widgets"]):
            raise ValueError("Unknown widget type")
    if [panel["id"] for panel in panels] != ["topbar", "dock"]:
        raise ValueError("Expected topbar followed by dock")
    return data


def render_script(recipe: dict) -> str:
    """Produce a one-shot panel replacement using validated JSON, never raw JS input."""
    data = validate_recipe(recipe)
    settings = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    token = json.dumps("munhof-kde-ricing:" + data["id"])
    marker = json.dumps(MARKER)
    return (
        f"var recipe={settings};var marker={marker};var owner={token};"
        "var required=[];recipe.panels.forEach(function(p){p.widgets.forEach(function(w){"
        "if(required.indexOf(w)<0)required.push(w);});});"
        "var missing=required.filter(function(w){return knownWidgetTypes.indexOf(w)<0;});"
        "if(missing.length){print(marker+JSON.stringify({ok:false,error:'Missing Plasma widgets: '+"
        "missing.join(', ')}));}else{"
        "var old=panels().slice();var already=old.filter(function(p){"
        "p.currentConfigGroup=['General'];return p.readConfig('plasmaRiceOwner')===owner;});"
        "if(already.length===recipe.panels.length){"
        "print(marker+JSON.stringify({ok:true,already:true}));"
        "}else{var created=[];try{recipe.panels.forEach(function(spec){"
        "var p=new Panel();created.push(p);p.location=spec.location;"
        "p.height=spec.height;p.hiding=spec.hiding;"
        "p.lengthMode=spec.length_mode;p.alignment=spec.alignment;"
        "p.currentConfigGroup=['General'];p.writeConfig('plasmaRiceOwner',owner);"
        "p.writeConfig('plasmaRicePanel',spec.id);"
        "spec.widgets.forEach(function(w){p.addWidget(w);});"
        "});old.forEach(function(p){p.remove();});"
        "print(marker+JSON.stringify({ok:true,created:created.map(function(p){return p.id;})}));"
        "}catch(e){created.forEach(function(p){try{p.remove();}catch(ignored){}});"
        "print(marker+JSON.stringify({ok:false,error:String(e)}));}}}"
    )


def parse_result(raw: str) -> dict:
    if MARKER not in raw:
        raise RuntimeError("PlasmaShell did not report script completion")
    data, _ = json.JSONDecoder().raw_decode(raw.split(MARKER, 1)[1].lstrip())
    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError("PlasmaShell bootstrap failed: " + str(data))
    return data


def command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, text=True, capture_output=True, timeout=20)


def apply_appearance(recipe: dict) -> None:
    for binary, arg in (
        ("plasma-apply-colorscheme", recipe["color_scheme"]),
        ("plasma-apply-desktoptheme", recipe["desktop_theme"]),
    ):
        if shutil.which(binary):
            outcome = command([binary, arg])
            if outcome.returncode:
                print(f"Warning: {binary} returned {outcome.returncode}", file=sys.stderr)
    for group, pairs in recipe["kwin"].items():
        for key, value in pairs.items():
            outcome = command([
                "kwriteconfig6", "--file", "kwinrc", "--group", group,
                "--key", key, value
            ])
            if outcome.returncode:
                raise RuntimeError(f"Unable to set KWin {group}/{key}: {outcome.stderr.strip()}")
    if shutil.which("qdbus6"):
        command(["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"])


def apply_panels(recipe: dict) -> dict:
    cmd = [
        "qdbus6", "org.kde.plasmashell", "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript", render_script(recipe),
    ]
    last_error = "PlasmaShell not ready"
    for _ in range(25):
        outcome = command(cmd)
        if outcome.returncode == 0:
            try:
                return parse_result(outcome.stdout)
            except RuntimeError as exc:
                last_error = str(exc)
                if MARKER in outcome.stdout:
                    break  # Actual configuration error, not startup delay.
        else:
            last_error = outcome.stderr.strip() or "PlasmaShell D-Bus unavailable"
        time.sleep(0.5)
    raise RuntimeError(last_error)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate/print recipe only")
    parser.add_argument(
        "--managed-profile", action="store_true",
        help="Apply only when the managed same-user rice profile is active",
    )
    args = parser.parse_args(argv)
    try:
        if os.geteuid() == 0:
            raise PermissionError("Bootstrap must not run as root")
        current_user = pwd.getpwuid(os.getuid()).pw_name
        if args.managed_profile:
            profile_file = (
                Path.home() / ".local/state/munhof-kde-ricing/profiles/state.json"
            )
            if not profile_file.is_file():
                return 0
            selected = json.loads(profile_file.read_text(encoding="utf-8"))
            if selected.get("schema") != 1 or selected.get("active") != "rice":
                return 0
        else:
            required_user = ACCOUNT.read_text(encoding="utf-8").strip()
            if current_user != required_user:
                raise PermissionError("Bootstrap restricted to dedicated test account")
        recipe = validate_recipe(json.loads(RECIPE.read_text(encoding="utf-8")))
        if args.dry_run:
            print(json.dumps(recipe, indent=2))
            return 0
        state = Path.home() / ".local/state/munhof-kde-ricing"
        marker = state / "initialized-v1.json"
        if marker.exists():
            return 0
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        source = Path.home() / ".config/plasma-org.kde.plasma.desktop-appletsrc"
        if source.is_file():
            backup = state / "panels-before-first-run.ini"
            if not backup.exists():
                shutil.copy2(source, backup)
                backup.chmod(0o600)
        apply_appearance(recipe)
        result = apply_panels(recipe)
        marker.write_text(json.dumps({
            "created_at": datetime.now(UTC).isoformat(),
            "recipe": recipe["id"], "result": result,
        }, indent=2), encoding="utf-8")
        marker.chmod(0o600)
        print("Isolated Plasma Rice session initialized", flush=True)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Plasma Rice first-run error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
