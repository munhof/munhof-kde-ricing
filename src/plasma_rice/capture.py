"""Capture known global Polonium KConfig keys into a reviewable manifest."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from .config import ManifestError

# Never enumerate unknown KConfig keys, display identities, or arbitrary user data.
CAPTURE_KEYS: tuple[tuple[str, str], ...] = (
    ("Plugins", "poloniumEnabled"),
    ("Tiling", "padding"),
    ("Script-polonium", "Borders"),
    ("Script-polonium", "DefaultEngine"),
    ("Script-polonium", "EngineType"),
    ("Script-polonium", "InsertionPoint"),
    ("Script-polonium", "RotateLayout"),
    ("Script-polonium", "BTreeRotateLayout"),
    ("Script-polonium", "BTreeInsertionStyle"),
    ("Script-polonium", "MaximizeSingle"),
    ("Script-polonium", "ResizeAmount"),
    ("Script-polonium", "SaveOnTileEdit"),
    ("Script-polonium", "TilePopups"),
    ("Script-polonium", "TiledWindowsBelow"),
    ("Script-polonium", "TimerDelay"),
)
FILTER_KEYS: tuple[tuple[str, str], ...] = (
    ("Script-polonium", "FilterProcess"),
    ("Script-polonium", "FilterCaption"),
)


def validate_output(root: Path, output: Path) -> Path:
    """Restrict generated components to a single manifest in components/<name>."""
    repo = root.resolve()
    path = (repo / output).resolve()
    if path.name != "manifest.yaml" or path.parent.parent != (repo / "components").resolve():
        raise ValueError("Output must be components/<name>/manifest.yaml within the repo")
    if re.fullmatch(r"[a-z][a-z0-9_-]*", path.parent.name) is None:
        raise ValueError("Component name must be lowercase alphanumeric with - or _")
    return path


def build_manifest(
    backend, component: str = "tiling-captured", include_filters: bool = False
) -> dict:
    """Read only an allowlisted set of KConfig keys; no writes to KDE."""
    if re.fullmatch(r"[a-z][a-z0-9_-]*", component) is None:
        raise ManifestError("Invalid captured component name")
    if backend.read("kwinrc", "Plugins", "poloniumEnabled") != "true":
        raise ManifestError("Enable Polonium before capturing its configuration")

    operations = []
    for group, key in (*CAPTURE_KEYS, *(FILTER_KEYS if include_filters else ())):
        value = backend.read("kwinrc", group, key)
        if value is None or value == "":
            continue
        if "\n" in value or "\r" in value:
            raise ManifestError(f"Unexpected multiline KConfig value for {group}.{key}")
        operations.append({"file": "kwinrc", "group": group, "key": key, "value": value})
    return {
        "id": component,
        "description": "Captured global Polonium/KWin settings; review before committing.",
        "requires": {
            "commands": ["kreadconfig6", "kwriteconfig6", "kpackagetool6"],
            "kwin_script": "polonium",
        },
        "operations": operations,
    }


def save_manifest(path: Path, manifest: dict) -> None:
    """Create a manifest without overwriting any pre-existing data."""
    output = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(output)
