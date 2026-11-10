"""Strict, deliberately narrow YAML manifest validation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


ALLOWED_FILES = {"kwinrc"}


class ManifestError(ValueError):
    """Configuration cannot be interpreted safely."""


@dataclass(frozen=True)
class Operation:
    component: str
    file: str
    group: str
    key: str
    value: str

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.file, self.group, self.key)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ManifestError(f"Missing manifest: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"Expected YAML mapping: {path}")
    return data


def load_settings(root: Path) -> dict[str, Any]:
    conf = _load_yaml(root / "config/rice.yaml")
    if conf.get("version") != 1:
        raise ManifestError("config/rice.yaml must have version: 1")
    components = conf.get("components")
    if not isinstance(components, list) or not all(isinstance(x, str) for x in components):
        raise ManifestError("components must be a list of names")
    if not isinstance(conf.get("profile"), str):
        raise ManifestError("profile must be a string")
    return conf


def load_profile(root: Path, name: str) -> dict[str, Any]:
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ManifestError("Invalid profile name")
    profile = _load_yaml(root / "config/profiles" / f"{name}.yaml")
    if profile.get("id") != name:
        raise ManifestError("Profile ID must match file name")
    allow = profile.get("allow")
    if not isinstance(allow, list) or not all(x in ALLOWED_FILES for x in allow):
        raise ManifestError("Profile allow-list must contain only supported KConfig files")
    return profile


def load_component(root: Path, name: str) -> tuple[list[Operation], dict[str, Any]]:
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ManifestError("Invalid component name")
    manifest = _load_yaml(root / "components" / name / "manifest.yaml")
    if manifest.get("id") != name:
        raise ManifestError(f"Component manifest ID mismatch: {name}")
    raw = manifest.get("operations")
    if not isinstance(raw, list) or not raw:
        raise ManifestError(f"Component {name} has no operations")
    ops: list[Operation] = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"file", "group", "key", "value"}:
            raise ManifestError(f"Bad operation in {name}")
        file, group, key, value = (item[k] for k in ("file", "group", "key", "value"))
        if file not in ALLOWED_FILES:
            raise ManifestError(f"Unsupported configuration file: {file}")
        if any(not isinstance(v, str) or not v or "\n" in v for v in (group, key, value)):
            raise ManifestError(f"Invalid KConfig group, key, or value in {name}")
        ops.append(Operation(name, file, group, key, value))
    requirements = manifest.get("requires", {})
    if not isinstance(requirements, dict):
        raise ManifestError(f"Invalid requirements in {name}")
    commands = requirements.get("commands", [])
    if not isinstance(commands, list) or not all(isinstance(x, str) for x in commands):
        raise ManifestError(f"Invalid command list in {name}")
    return ops, requirements


def resolve(root: Path, selected: list[str] | None = None,
            profile_name: str | None = None) -> tuple[str, list[Operation], dict[str, Any]]:
    settings = load_settings(root)
    profile_name = profile_name or settings["profile"]
    profile = load_profile(root, profile_name)
    names = selected if selected else settings["components"]
    if len(names) != len(set(names)):
        raise ManifestError("Repeated components")
    all_ops: list[Operation] = []
    requirements: dict[str, Any] = {}
    used: set[tuple[str, str, str]] = set()
    for name in names:
        ops, req = load_component(root, name)
        for op in ops:
            if op.file not in profile["allow"]:
                raise ManifestError(f"Profile {profile_name} disallows {op.file}")
            if op.identity in used:
                raise ManifestError(f"Overlapping key: {op.identity}")
            used.add(op.identity)
        all_ops.extend(ops)
        requirements[name] = req
    return profile_name, all_ops, requirements
