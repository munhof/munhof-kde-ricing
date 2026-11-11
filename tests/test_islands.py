"""Static safety checks for the optional Quickshell proof-of-concept.

QML rendering and layer shell behavior require manual verification in KWin.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "appearance/quickshell/shell.qml"
ISLAND = ROOT / "appearance/quickshell/Island.qml"


def test_islands_are_per_screen_and_hotplug_aware():
    config = SHELL.read_text(encoding="utf-8")
    assert config.count("Variants {") == 4
    assert config.count("model: Quickshell.screens") == 4
    assert config.count("screen: modelData") == 4
    assert 'edge: "bottom"' in config
    assert 'horizontalPosition: "center"' in config


def test_islands_are_content_sized_not_full_width_surfaces():
    code = ISLAND.read_text(encoding="utf-8")
    assert "implicitWidth: Math.ceil(contents.implicitWidth + 24)" in code
    assert "implicitWidth: panel.implicitWidth" in code
    assert 'horizontalPosition === "left"' in code
    assert 'horizontalPosition === "right"' in code
    assert "exclusionMode: ExclusionMode.Ignore" in code
    assert "exclusiveZone:" not in code
    assert "anchors.fill: parent" in code  # Only within the compact surface.


def test_no_automatic_destructive_operations():
    code = SHELL.read_text(encoding="utf-8")
    forbidden = (
        "kwriteconfig", "plasmashell.evaluateScript", "p.remove()",
        "killall", "pkill", "sudo", "pacman", "rm -rf",
    )
    assert not any(command in code for command in forbidden)
    assert "Polonium" in code


def test_quickshell_layer_surfaces_have_identity_for_own_window_filter():
    code = ISLAND.read_text(encoding="utf-8")
    assert "import Quickshell.Wayland" in code
    assert 'WlrLayershell.namespace: "munhof-rice-island"' in code
    assert "WlrLayershell.layer: WlrLayer.Top" in code
    assert "focusable: false" in code
    assert "exclusionMode: ExclusionMode.Ignore" in code
    assert 'anchors.left: true' not in code
    assert 'anchors.right: true' not in code
