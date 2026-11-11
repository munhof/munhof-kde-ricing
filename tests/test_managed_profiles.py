"""Offline tests for same-account KDE profile switching and safe session installation."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    module_spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


profiles = load("profile_switcher_test", "scripts/session/profilectl.py")
installer = load("managed_installer_test", "scripts/session/install_profiles.py")


def make_home(tmp_path):
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    return home


def test_initial_profile_captures_existing_desktop(tmp_path):
    home = make_home(tmp_path)
    (home / ".config/kwinrc").write_text("original kwin\n", encoding="utf-8")
    switcher = profiles.ProfileManager(home)
    assert switcher.activate("original", check_processes=False) == {
        "profile": "original", "changed": False
    }
    state = switcher.read_state()
    assert state["active"] == "original"
    assert state["snapshots"]["original"] == state["snapshots"]["rice"]
    assert (home / ".config/kwinrc").read_text(encoding="utf-8") == "original kwin\n"


def test_visual_profiles_are_independent_and_persistent(tmp_path):
    home = make_home(tmp_path)
    winrc = home / ".config/kwinrc"
    shortcuts = home / ".config/kglobalshortcutsrc"
    winrc.write_text("baseline", encoding="utf-8")
    switcher = profiles.ProfileManager(home)
    switcher.activate("original", check_processes=False)

    winrc.write_text("original personalized", encoding="utf-8")
    assert switcher.activate("rice", check_processes=False)["changed"]
    assert winrc.read_text(encoding="utf-8") == "baseline"
    winrc.write_text("rice personalized", encoding="utf-8")
    shortcuts.write_text("rice hotkeys", encoding="utf-8")

    switcher.activate("original", check_processes=False)
    assert winrc.read_text(encoding="utf-8") == "original personalized"
    assert not shortcuts.exists()

    switcher.activate("rice", check_processes=False)
    assert winrc.read_text(encoding="utf-8") == "rice personalized"
    assert shortcuts.read_text(encoding="utf-8") == "rice hotkeys"


def test_profile_switch_refuses_active_plasma(tmp_path, monkeypatch):
    home = make_home(tmp_path)
    monkeypatch.setattr(profiles, "running_plasma", lambda _: [2345])
    with pytest.raises(profiles.ProfileError, match="Another Plasma session"):
        profiles.ProfileManager(home).activate("rice")
    assert not (home / profiles.STATE_FOLDER).exists()


def test_profile_switch_refuses_symlinks(tmp_path):
    home = make_home(tmp_path)
    target = tmp_path / "other"
    target.write_text("do not overwrite", encoding="utf-8")
    (home / ".config/kwinrc").symlink_to(target)
    with pytest.raises(profiles.ProfileError, match="Refusing symlink"):
        profiles.ProfileManager(home).activate("rice", check_processes=False)
    assert target.read_text(encoding="utf-8") == "do not overwrite"


def test_interrupted_switch_recovers_live_configuration(tmp_path):
    home = make_home(tmp_path)
    winrc = home / ".config/kwinrc"
    winrc.write_text("original", encoding="utf-8")
    switcher = profiles.ProfileManager(home)
    switcher.activate("original", check_processes=False)
    old = switcher.read_state()
    saved = switcher._snapshot()

    # Simulate a power loss after a partial profile restore.
    winrc.write_text("partial rice", encoding="utf-8")
    switcher.pending.write_text(json.dumps({
        "schema": 1, "previous": old,
        "live_snapshot": saved, "target": "rice"
    }), encoding="utf-8")
    switcher.activate("original", check_processes=False)
    assert winrc.read_text(encoding="utf-8") == "original"
    assert not switcher.pending.exists()
    assert switcher.read_state()["active"] == "original"


def test_only_allowlisted_visual_files_are_switched(tmp_path):
    home = make_home(tmp_path)
    config = home / ".config"
    (config / "kscreenlockerrc").write_text("keep me", encoding="utf-8")
    (config / "kwinrc").write_text("original", encoding="utf-8")
    switcher = profiles.ProfileManager(home)
    switcher.activate("rice", check_processes=False)
    (config / "kscreenlockerrc").write_text("modified outside", encoding="utf-8")
    switcher.activate("original", check_processes=False)
    assert (config / "kscreenlockerrc").read_text(encoding="utf-8") == "modified outside"
    assert not set(profiles.FILES) & {"kscreenlockerrc", "powerdevilrc", "kscreen"}


def test_installation_plans_two_managed_wayland_sessions(tmp_path, monkeypatch):
    home = tmp_path / "home" / "munhof"
    home.mkdir(parents=True)
    account = SimpleNamespace(pw_dir=str(home), pw_uid=1000, pw_gid=1000)
    monkeypatch.setattr(installer, "user_info", lambda *_: account)
    _, planned = installer.planned_files("munhof", ROOT, sudo_user="munhof")
    paths = {str(item.path) for item in planned}
    assert "/usr/share/wayland-sessions/munhof-plasma-original.desktop" in paths
    assert "/usr/share/wayland-sessions/munhof-plasma-rice-managed.desktop" in paths
    assert "/usr/local/libexec/munhof-plasma-rice-profilectl" in paths
    assert not any("plasma.desktop" == Path(path).name for path in paths)


def test_session_script_runs_switcher_before_startplasma():
    script = (ROOT / "session/managed-session.sh").read_text(encoding="utf-8")
    assert script.index("profilectl activate") < script.index("startplasma-wayland")
    assert '"$profile"' in script


def test_bootstrap_is_guarded_by_managed_rice_profile():
    script = (ROOT / "scripts/session/bootstrap.py").read_text(encoding="utf-8")
    assert "--managed-profile" in script
    assert 'selected.get("active") != "rice"' in script


def test_installer_never_modifies_sddm_autologin_or_user_accounts():
    text = (ROOT / "scripts/session/install_profiles.py").read_text(encoding="utf-8")
    assert "useradd" not in text
    assert "subprocess.run" not in text
    assert "os.system" not in text
    assert "pwd.getpwnam" in text
    assert "os.system" not in text
    assert "subprocess.run" not in text
    assert "sddm.conf" not in text


def test_profile_state_per_user_and_private(tmp_path):
    home = make_home(tmp_path)
    m = profiles.ProfileManager(home)
    m.activate("rice", check_processes=False)
    assert m.root.stat().st_mode & 0o777 == 0o700
    assert m.state.stat().st_mode & 0o777 == 0o600
    assert m.read_state()["active"] == "rice"
