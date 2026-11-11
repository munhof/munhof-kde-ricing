"""Waybar/Wofi prototype tests; do not launch any real desktop processes."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPEARANCE = ROOT / "scripts/appearance/appearancectl.py"


def load():
    spec = importlib.util.spec_from_file_location("rice_appearance_test", APPEARANCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_two_bars_apply_to_all_monitors():
    bars = json.loads((ROOT / "appearance/waybar/config.jsonc").read_text(encoding="utf-8"))
    assert isinstance(bars, list) and len(bars) == 2
    assert {bar["position"] for bar in bars} == {"top", "bottom"}
    assert all("output" not in bar for bar in bars)
    assert bars[0]["name"] == "rice-topbar"
    assert bars[1]["name"] == "rice-dock"
    assert bars[1]["modules-center"]


def test_no_hyprland_or_sway_only_modules():
    bars = json.loads((ROOT / "appearance/waybar/config.jsonc").read_text(encoding="utf-8"))
    all_modules = [module for bar in bars for side in (
        "modules-left", "modules-center", "modules-right"
    ) for module in bar.get(side, [])]
    assert not any(module.startswith(("hyprland/", "sway/", "niri/")) for module in all_modules)


def test_waybar_launcher_and_dock_actions_are_profile_managed():
    bars = json.loads((ROOT / "appearance/waybar/config.jsonc").read_text(encoding="utf-8"))
    clicks = [value["on-click"] for bar in bars for value in bar.values()
              if isinstance(value, dict) and "on-click" in value]
    assert any(" launcher" in cmd for cmd in clicks)
    assert any(" launch files" in cmd for cmd in clicks)
    assert any(" next-desktop" in cmd for cmd in clicks)


def test_wofi_theme_has_search_and_list_not_unimplemented_grid():
    config = (ROOT / "appearance/wofi/config").read_text(encoding="utf-8")
    style = (ROOT / "appearance/wofi/style.css").read_text(encoding="utf-8")
    assert "show=drun" in config
    assert "columns=1" in config
    assert "#input" in style
    assert "#entry:selected" in style


def test_original_profile_refuses_start(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod, "active_profile", lambda: "original")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    with pytest.raises(mod.AppearanceError, match="Rice"):
        mod.start()


def test_non_wayland_refuses_start(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod, "active_profile", lambda: "rice")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    with pytest.raises(mod.AppearanceError, match="Wayland"):
        mod.start()


def test_install_is_user_local_and_no_sudo(tmp_path, monkeypatch):
    mod = load()
    home = tmp_path / "home"
    monkeypatch.setattr(mod, "HOME", home)
    monkeypatch.setattr(mod, "DATA", home / ".local/share/munhof-kde-ricing/appearance")
    monkeypatch.setattr(mod, "STATE", home / ".local/state/munhof-kde-ricing/appearance")
    monkeypatch.setattr(mod, "BIN", home / ".local/bin/munhof-rice-appearance")
    monkeypatch.setattr(mod.os, "geteuid", lambda: 1000)
    assert mod.install(source=ROOT) == 5
    assert mod.BIN.is_file()
    assert (mod.DATA / "waybar/config.jsonc").is_file()
    assert mod.install(source=ROOT) == 5
    (mod.DATA / "waybar/config.jsonc").write_text("modified by user", encoding="utf-8")
    with pytest.raises(mod.AppearanceError, match="--update"):
        mod.install(source=ROOT)
    assert (mod.DATA / "waybar/config.jsonc").read_text(encoding="utf-8") == "modified by user"


def test_no_native_panel_changes_without_explicit_confirmation(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod, "require_rice", lambda: None)
    with pytest.raises(mod.AppearanceError, match="--confirm"):
        mod.replace_panels()


def test_panel_replacement_requires_visible_managed_waybar(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod, "require_rice", lambda: None)
    monkeypatch.setattr(mod, "managed_waybar_pid", lambda: None)
    with pytest.raises(mod.AppearanceError, match="Waybar must be visibly"):
        mod.replace_panels(confirm=True)


def test_desktop_fallback_when_dbus_missing(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod.shutil, "which", lambda _: None)
    assert "1" in mod.desktops()
    assert "4" in mod.desktops()


def test_only_known_app_launchers_accepted():
    mod = load()
    assert "terminal" in mod.LAUNCHERS
    assert "files" in mod.LAUNCHERS
    assert "dangerous" not in mod.LAUNCHERS


def test_three_tuning_profiles_cover_typical_laptop_and_touch():
    mod = load()
    assert mod.SIZING["compact"][0] < mod.SIZING["balanced"][0]
    assert mod.SIZING["balanced"][0] < mod.SIZING["touch"][0]
    cfg = json.loads((ROOT / "appearance/waybar/config.jsonc").read_text(encoding="utf-8"))
    for preset, dimensions in mod.SIZING.items():
        sizes = dict(zip(
            ("bar_height", "dock_height", "font_size", "icon_size", "edge_gap"),
            dimensions, strict=True
        ))
        generated = mod.render_tuned(
            cfg, (ROOT / "appearance/waybar/style.css").read_text(encoding="utf-8"),
            (ROOT / "appearance/wofi/config").read_text(encoding="utf-8"),
            (ROOT / "appearance/wofi/style.css").read_text(encoding="utf-8"),
            sizes,
        )
        bars = json.loads(generated["waybar/tuned-config.json"])
        assert bars[0]["height"] == sizes["bar_height"]
        assert bars[1]["height"] == sizes["dock_height"]
        assert all(bar["exclusive"] is True and "output" not in bar for bar in bars)
        assert f"font-size: {sizes['icon_size']}px" in generated[
            "waybar/tuned-style.css"
        ].decode()
        assert f"width={sizes['font_size'] * 30 + 230}" in generated[
            "wofi/tuned-config"
        ].decode()
        assert len(cfg) == 2


@pytest.mark.parametrize("field,value", [
    ("bar_height", 0),
    ("dock_height", 20),
    ("font_size", 0),
    ("icon_size", 80),
    ("edge_gap", -1),
])
def test_invalid_tuned_dimensions_rejected(field, value):
    mod = load()
    config = json.loads((ROOT / "appearance/waybar/config.jsonc").read_text())
    sizes = dict(zip(
        ("bar_height", "dock_height", "font_size", "icon_size", "edge_gap"),
        mod.SIZING["balanced"], strict=True
    ))
    sizes[field] = value
    with pytest.raises(mod.AppearanceError):
        mod.render_tuned(config, "", "", "", sizes)


def test_tuned_layout_plan_is_read_only(tmp_path, monkeypatch):
    mod = load()
    home = tmp_path / "home"
    data = home / ".local/share/munhof-kde-ricing/appearance"
    for asset in ("waybar/config.jsonc", "waybar/style.css", "wofi/config",
                  "wofi/style.css"):
        dest = data / asset
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / "appearance" / asset).read_bytes())
    monkeypatch.setattr(mod, "DATA", data)
    monkeypatch.setattr(mod, "require_rice", lambda: None)
    settings = mod.tune("balanced")
    assert settings["bar_height"] == 42
    assert not (data / "waybar/tuned-config.json").exists()


def test_tuned_layout_applied_idempotently(tmp_path, monkeypatch):
    mod = load()
    home = tmp_path / "home"
    data = home / ".local/share/munhof-kde-ricing/appearance"
    for asset in ("waybar/config.jsonc", "waybar/style.css", "wofi/config",
                  "wofi/style.css"):
        dest = data / asset
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / "appearance" / asset).read_bytes())
    monkeypatch.setattr(mod, "DATA", data)
    monkeypatch.setattr(mod, "require_rice", lambda: None)
    mod.tune("balanced", apply=True)
    expected = (data / "waybar/tuned-config.json").read_bytes()
    mod.tune("balanced", apply=True)
    assert (data / "waybar/tuned-config.json").read_bytes() == expected
    mod.tune("touch", apply=True)
    assert json.loads((data / "waybar/tuned-config.json").read_text())[1]["height"] == 76
    assert (data / "wofi/tuned-style.css").is_file()


def test_tuned_output_refuses_symlink(tmp_path, monkeypatch):
    mod = load()
    home = tmp_path / "home"
    data = home / ".local/share/munhof-kde-ricing/appearance"
    for asset in ("waybar/config.jsonc", "waybar/style.css", "wofi/config",
                  "wofi/style.css"):
        dest = data / asset
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / "appearance" / asset).read_bytes())
    original = tmp_path / "do-not-touch"
    original.write_text("private", encoding="utf-8")
    (data / "waybar/tuned-config.json").symlink_to(original)
    monkeypatch.setattr(mod, "DATA", data)
    monkeypatch.setattr(mod, "require_rice", lambda: None)
    with pytest.raises(mod.AppearanceError, match="symlink"):
        mod.tune("balanced", apply=True)
    assert original.read_text(encoding="utf-8") == "private"
