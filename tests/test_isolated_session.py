"""Isolated session tests: no KDE, root, or account creation needed."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bootstrap = load("isolated_bootstrap", "scripts/session/bootstrap.py")
installer = load("isolated_installer", "scripts/session/install.py")
RECIPE = json.loads((ROOT / "session/recipe.json").read_text(encoding="utf-8"))


def test_recipe_contains_complete_riced_desktop():
    recipe = bootstrap.validate_recipe(RECIPE)
    assert recipe["panels"][0]["location"] == "top"
    assert recipe["panels"][1]["location"] == "bottom"
    assert recipe["color_scheme"] == "BreezeDark"
    assert recipe["kwin"]["Tiling"]["padding"] == "10"


def test_generated_js_replaces_panels_inside_isolated_account():
    script = bootstrap.render_script(RECIPE)
    assert "old.forEach(function(p){p.remove();})" in script
    assert "new Panel()" in script
    assert "knownWidgetTypes" in script
    assert "plasmaRiceOwner" in script
    if shutil.which("node"):
        result = subprocess.run(
            ["node", "--check", "-"], input=script, capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr


def test_parse_result():
    assert bootstrap.parse_result(bootstrap.MARKER + '{"ok":true,"created":[1,2]}')["ok"]
    with pytest.raises(RuntimeError, match="failed"):
        bootstrap.parse_result(bootstrap.MARKER + '{"ok":false,"error":"missing"}')
    with pytest.raises(RuntimeError, match="did not report"):
        bootstrap.parse_result("wrong")


@pytest.mark.parametrize("field", ["panels", "kwin", "color_scheme", "schema"])
def test_recipe_tampering_rejected(field):
    data = json.loads(json.dumps(RECIPE))
    data[field] = None
    with pytest.raises(ValueError):
        bootstrap.validate_recipe(data)


def test_unknown_widget_rejected():
    data = json.loads(json.dumps(RECIPE))
    data["panels"][0]["widgets"].append("org.attacker.js")
    with pytest.raises(ValueError, match="Unknown widget"):
        bootstrap.validate_recipe(data)


def test_installer_has_no_account_creation():
    text = (ROOT / "scripts/session/install.py").read_text(encoding="utf-8")
    assert "useradd" in text  # Only documentation in error message, never invoked.
    assert "subprocess.run" not in text
    assert "os.system" not in text


def test_session_is_restricted_to_dedicated_user():
    source = (ROOT / "session/wayland-session.sh").read_text(encoding="utf-8")
    assert "@RICE_ACCOUNT@" in source
    assert "$(id -un)" in source
    assert "exec /usr/bin/startplasma-wayland" in source


def test_installer_writes_only_named_session_file():
    assert installer.SESSION_DESKTOP == Path(
        "/usr/share/wayland-sessions/munhof-plasma-rice-recovery.desktop"
    )
    assert str(installer.RECIPE_PATH).startswith("/usr/local/share/")
    assert str(installer.INSTALL_BIN).startswith("/usr/local/libexec/")
    assert installer.SESSION_DESKTOP.name != "plasma.desktop"
