"""Retire legacy external bars without damaging Plasma profiles or other programs."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location(
        "retire_external_test", ROOT / "scripts/native/retire_external.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare(tmp_path, monkeypatch):
    mod = load()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(mod, "HOME", home)
    monkeypatch.setattr(mod, "AUTOSTART", home / ".config/autostart/munhof-rice-appearance.desktop")
    monkeypatch.setattr(mod, "STATE", home / ".local/state/munhof-kde-ricing/appearance")
    monkeypatch.setattr(mod, "WAYBAR_PID", mod.STATE / "waybar.pid")
    monkeypatch.setattr(mod, "WAYBAR_ASSETS", home / ".local/share/munhof-kde-ricing/appearance/waybar")
    monkeypatch.setattr(mod, "LAUNCHER", home / ".local/bin/munhof-rice-appearance")
    monkeypatch.setattr(mod.os, "geteuid", lambda: 1000)
    mod.AUTOSTART.parent.mkdir(parents=True)
    mod.AUTOSTART.write_text(
        "[Desktop Entry]\nName=Munhof Rice Appearance\n"
        f"Exec={mod.LAUNCHER} start\n", encoding="utf-8"
    )
    return mod


def test_retire_default_is_read_only(tmp_path, monkeypatch):
    mod = prepare(tmp_path, monkeypatch)
    assert mod.retire()["changed"] is False
    assert mod.AUTOSTART.exists()


def test_retire_only_our_autostart(tmp_path, monkeypatch):
    mod = prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "managed_waybar_pid", lambda: None)
    result = mod.retire(apply=True)
    assert result["changed"] is True
    assert not mod.AUTOSTART.exists()
    assert not (tmp_path / "home/.config/plasma-org.kde.plasma.desktop-appletsrc").exists()


def test_never_delete_unknown_autostart(tmp_path, monkeypatch):
    mod = prepare(tmp_path, monkeypatch)
    mod.AUTOSTART.write_text("[Desktop Entry]\nExec=other-app\n", encoding="utf-8")
    with pytest.raises(mod.CleanupError, match="not our managed"):
        mod.retire(apply=True)
    assert mod.AUTOSTART.exists()


def test_never_follow_autostart_symlink(tmp_path, monkeypatch):
    mod = prepare(tmp_path, monkeypatch)
    protected = tmp_path / "protected"
    protected.write_text("keep", encoding="utf-8")
    mod.AUTOSTART.unlink()
    mod.AUTOSTART.symlink_to(protected)
    with pytest.raises(mod.CleanupError, match="symlink"):
        mod.retire(apply=True)
    assert protected.read_text(encoding="utf-8") == "keep"


def test_no_global_process_killer_or_package_uninstall():
    code = (ROOT / "scripts/native/retire_external.py").read_text(encoding="utf-8")
    assert "os.kill(pid, signal.SIGTERM)" in code
    assert "subprocess.Popen" not in code
    assert "pacman -R" not in code
    assert "shutil.rmtree" not in code
    assert "subprocess.run" not in code
