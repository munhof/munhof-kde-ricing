"""Native Plasma panel/dock management via the documented PlasmaShell scripting API.

No existing panel is ever edited. Panels carry an opaque ownership token, and only
panels with a matching token can be removed via the CLI.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .engine import _write_json_atomic

PANEL_NAME = re.compile(r"[a-z][a-z0-9_-]*\Z")
SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*\Z")
LOCATIONS = {"top", "bottom", "left", "right"}
HIDING = {"none", "autohide", "dodgewindows", "windowsgobelow"}
LENGTH_MODES = {"fill", "fit"}
ALIGNMENTS = {"left", "center", "right"}
# Only installed KDE-native widget IDs may be requested by a preset.
WIDGETS = {
    "org.kde.plasma.kickoff",
    "org.kde.plasma.pager",
    "org.kde.plasma.panelspacer",
    "org.kde.plasma.digitalclock",
    "org.kde.plasma.systemtray",
    "org.kde.plasma.icontasks",
    "org.kde.plasma.lock_logout",
    "org.kde.plasma.showdesktop",
    "org.kde.plasma.marginsseparator",
    "org.kde.plasma.appmenu",
}
SENTINEL = "__PLASMA_RICE_JSON__"


class ShellError(ValueError):
    """Invalid or unsafe panel operation."""


@dataclass(frozen=True)
class PanelSpec:
    name: str
    location: str
    height: int
    length_mode: str
    hiding: str
    alignment: str
    widgets: tuple[dict[str, Any], ...]

    def serialize(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "location": self.location,
            "height": self.height,
            "length_mode": self.length_mode,
            "hiding": self.hiding,
            "alignment": self.alignment,
            "widgets": [dict(w) for w in self.widgets],
        }


def _simple_name(name: str) -> str:
    if not PANEL_NAME.fullmatch(name):
        raise ShellError("Invalid preset name")
    return name


def load_panel(root: Path, name: str) -> PanelSpec:
    """Load a strict panel preset; no JS or shell commands allowed in YAML."""
    _simple_name(name)
    path = root / "config" / "shell" / f"{name}.yaml"
    if not path.is_file():
        raise ShellError(f"Missing panel preset: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {"name", "location", "height", "length_mode", "hiding", "alignment", "widgets"}
    if not isinstance(value, dict) or set(value) != required or value["name"] != name:
        raise ShellError("Panel preset must have exactly the documented fields and matching name")
    if value["location"] not in LOCATIONS:
        raise ShellError("Unsupported panel location")
    if value["hiding"] not in HIDING or value["length_mode"] not in LENGTH_MODES:
        raise ShellError("Unsupported panel mode")
    if value["alignment"] not in ALIGNMENTS:
        raise ShellError("Unsupported panel alignment")
    if type(value["height"]) is not int or not 24 <= value["height"] <= 96:
        raise ShellError("Panel height must be an integer between 24 and 96")
    raw_widgets = value["widgets"]
    if not isinstance(raw_widgets, list) or not 1 <= len(raw_widgets) <= 15:
        raise ShellError("Panel needs 1–15 widgets")
    widgets: list[dict[str, Any]] = []
    for raw in raw_widgets:
        if isinstance(raw, str):
            raw = {"type": raw}
        if not isinstance(raw, dict) or set(raw) - {"type", "config"} or "type" not in raw:
            raise ShellError("Invalid widget descriptor")
        if not isinstance(raw["type"], str) or raw["type"] not in WIDGETS:
            raise ShellError(f"Widget not allowlisted: {raw['type']}")
        configs = raw.get("config", {})
        if not isinstance(configs, dict):
            raise ShellError("Widget config must be a mapping")
        clean_config: dict[str, dict[str, str | bool | int]] = {}
        for group, settings in configs.items():
            if not isinstance(group, str) or not SAFE_NAME.fullmatch(group):
                raise ShellError("Invalid widget configuration group")
            if not isinstance(settings, dict):
                raise ShellError("Widget group configuration must be a mapping")
            clean_config[group] = {}
            for key, setting in settings.items():
                if not isinstance(key, str) or not SAFE_NAME.fullmatch(key):
                    raise ShellError("Invalid widget configuration key")
                if type(setting) not in (str, bool, int) or len(str(setting)) > 1024:
                    raise ShellError("Invalid widget config value")
                clean_config[group][key] = setting
        widgets.append({"type": raw["type"], "config": clean_config})
    return PanelSpec(
        name=name,
        location=value["location"],
        height=value["height"],
        length_mode=value["length_mode"],
        hiding=value["hiding"],
        alignment=value["alignment"],
        widgets=tuple(widgets),
    )


def _as_js(value: Any) -> str:
    # JSON data literals are valid JS and prevent JS code injection from YAML values.
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def inventory_script() -> str:
    return (
        "var current=panels().map(function(p){"
        "p.currentConfigGroup=['General'];"
        "return {id:p.id,screen:p.screen,location:p.location,height:p.height,"
        "hiding:p.hiding,length_mode:p.lengthMode,alignment:p.alignment,"
        "owner:String(p.readConfig('plasmaRiceOwner')||''),"
        "widgets:p.widgets().map(function(w){return w.type;})};});"
        f"print('{SENTINEL}'+JSON.stringify({{panels:current,widgets:knownWidgetTypes}}));"
    )


def create_script(spec: PanelSpec, token: str) -> str:
    definition = _as_js(spec.serialize())
    owner = _as_js(token)
    marker = _as_js(SENTINEL)
    return (
        f"var desired={definition};var owner={owner};"
        "var missing=desired.widgets.filter(function(w){return !knownWidgetTypes.includes(w.type);});"
        "if(missing.length){"
        f"print({marker}+JSON.stringify({{error:'Missing widgets: '+missing.map(function(w){{return w.type;}}).join(', ')}}));"
        "}else{"
        "var p=new Panel();"
        "p.location=desired.location;p.height=desired.height;"
        "p.lengthMode=desired.length_mode;p.hiding=desired.hiding;"
        "p.alignment=desired.alignment;"
        "p.currentConfigGroup=['General'];"
        "p.writeConfig('plasmaRiceOwner',owner);"
        "p.writeConfig('plasmaRicePreset',desired.name);"
        "desired.widgets.forEach(function(item){"
        "var w=p.addWidget(item.type);"
        "Object.keys(item.config).forEach(function(group){"
        "w.currentConfigGroup=[group];"
        "Object.keys(item.config[group]).forEach(function(key){"
        "w.writeConfig(key,item.config[group][key]);});"
        "});});"
        f"print({marker}+JSON.stringify({{id:p.id,owner:owner}}));"
        "}"
    )


def remove_script(record: dict[str, Any], force_owned: bool = False) -> str:
    name = _as_js(record["name"])
    token = _as_js(record["token"])
    expected = _as_js(record["spec"])
    marker = _as_js(SENTINEL)
    return (
        f"var targetName={name};var token={token};var desired={expected};"
        "var match=panels().filter(function(p){"
        "p.currentConfigGroup=['General'];"
        "return p.readConfig('plasmaRiceOwner')===token && "
        "p.readConfig('plasmaRicePreset')===targetName;});"
        "var error='';"
        "if(match.length!==1){error='Managed panel missing or ownership ambiguous';}"
        "else{var p=match[0];var same="
        "p.location===desired.location && Number(p.height)===desired.height && "
        "p.lengthMode===desired.length_mode && p.hiding===desired.hiding && "
        "p.alignment===desired.alignment && JSON.stringify(p.widgets().map(function(w){return w.type;}))"
        "===JSON.stringify(desired.widgets.map(function(w){return w.type;}));"
        f"if(!same && !{_as_js(force_owned)}){{error='Managed panel has been edited; refused removal';}}"
        "else{p.remove();}}"
        f"print({marker}+JSON.stringify(error?{{error:error}}:{{removed:true}}));"
    )


def _parse_response(output: str) -> dict[str, Any]:
    at = output.find(SENTINEL)
    if at < 0:
        raise ShellError(f"PlasmaShell did not return a result: {output[:400]!r}")
    start = at + len(SENTINEL)
    try:
        parsed, _ = json.JSONDecoder().raw_decode(output[start:])
    except json.JSONDecodeError as exc:
        raise ShellError("Invalid PlasmaShell result payload") from exc
    if not isinstance(parsed, dict):
        raise ShellError("Unexpected PlasmaShell result")
    if parsed.get("error"):
        raise ShellError(str(parsed["error"]))
    return parsed


class PlasmaShellBackend:
    def __init__(self, execute=None):
        self.execute = execute or self._qdbus

    @staticmethod
    def _qdbus(script: str) -> str:
        if not shutil.which("qdbus6"):
            raise ShellError("qdbus6 is missing")
        result = subprocess.run(
            ["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
             "org.kde.PlasmaShell.evaluateScript", script],
            check=False, capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            raise ShellError(f"PlasmaShell D-Bus failed: {result.stderr.strip()[:300]}")
        return result.stdout

    def eval(self, script: str) -> dict[str, Any]:
        return _parse_response(self.execute(script))

    def inspect(self) -> dict[str, Any]:
        response = self.eval(inventory_script())
        if not isinstance(response.get("panels"), list):
            raise ShellError("PlasmaShell returned no panel inventory")
        if not isinstance(response.get("widgets"), list):
            raise ShellError("PlasmaShell returned no widget inventory")
        return response


def record_file(state_dir: Path, name: str) -> Path:
    return state_dir / "shell" / f"{_simple_name(name)}.json"


def load_record(state_dir: Path, name: str) -> dict[str, Any] | None:
    path = record_file(state_dir, name)
    if not path.exists():
        return None
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or result.get("name") != name:
        raise ShellError("Unsafe managed panel receipt")
    return result


def check_conflicts(spec: PanelSpec, inventory: dict[str, Any],
                    allow_overlap: bool = False) -> list[str]:
    available = inventory["widgets"]
    missing = [w["type"] for w in spec.widgets if w["type"] not in available]
    if missing:
        raise ShellError(f"Required Plasma widgets not installed: {', '.join(missing)}")
    conflicts = [
        f"Panel #{p['id']} already uses the {spec.location} edge of screen {p['screen']}"
        for p in inventory["panels"] if p["location"] == spec.location
    ]
    if conflicts and not allow_overlap:
        raise ShellError(
            "Existing panels will be preserved. New panel would share an edge: "
            + "; ".join(conflicts) + ". Use --allow-overlap to add anyway."
        )
    return conflicts


def apply_panel(spec: PanelSpec, state_dir: Path, backend: PlasmaShellBackend,
                config_dir: Path, allow_overlap: bool = False) -> dict[str, Any]:
    """Add a new owned panel, never changing or deleting an existing panel."""
    current = backend.inspect()
    existing = load_record(state_dir, spec.name)
    if existing is not None:
        owned = [p for p in current["panels"] if p["owner"] == existing.get("token")]
        if len(owned) == 1:
            return {"already_installed": True, "id": owned[0]["id"]}
        raise ShellError("A stale/pending panel record exists; inspect before retrying")
    check_conflicts(spec, current, allow_overlap=allow_overlap)
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    file = record_file(state_dir, spec.name)
    snapshot = state_dir / "backups" / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-panels.ini"
    )
    source = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    if source.is_file():
        snapshot.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(source, snapshot)
        snapshot.chmod(0o600)
    record = {
        "schema": 1,
        "name": spec.name,
        "token": str(uuid.uuid4()),
        "status": "pending",
        "spec": spec.serialize(),
        "created": datetime.now(UTC).isoformat(),
        "backup": str(snapshot) if source.is_file() else None,
    }
    _write_json_atomic(file, record)
    try:
        result = backend.eval(create_script(spec, record["token"]))
        if not isinstance(result.get("id"), int):
            raise ShellError("Panel creation returned no numeric ID")
        record["id"] = result["id"]
        record["status"] = "installed"
        _write_json_atomic(file, record)
    except Exception:
        # Never discard a receipt if Plasma might have created the panel.
        # A pending receipt can be inspected/rolled back by ownership token.
        raise
    return {"already_installed": False, "id": record["id"], "backup": record["backup"]}


def rollback_panel(name: str, state_dir: Path, backend: PlasmaShellBackend,
                   force_owned: bool = False) -> dict[str, Any]:
    record = load_record(state_dir, name)
    if record is None:
        raise ShellError(f"No managed panel named {name}")
    if (record.get("schema") != 1 or
            not isinstance(record.get("token"), str) or
            not isinstance(record.get("spec"), dict)):
        raise ShellError("Corrupted managed panel receipt")
    result = backend.eval(remove_script(record, force_owned=force_owned))
    if not result.get("removed"):
        raise ShellError("PlasmaShell did not confirm removal")
    record_file(state_dir, name).unlink()
    return {"removed": True, "backup": record.get("backup")}
