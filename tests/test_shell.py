import json
import re
from pathlib import Path

import pytest

from plasma_rice.shell import (
    SENTINEL,
    PanelSpec,
    PlasmaShellBackend,
    ShellError,
    _parse_response,
    apply_panel,
    check_conflicts,
    create_script,
    load_panel,
    load_record,
    rollback_panel,
)

ROOT = Path(__file__).resolve().parents[1]


def available():
    return [
        "org.kde.plasma.kickoff",
        "org.kde.plasma.pager",
        "org.kde.plasma.panelspacer",
        "org.kde.plasma.systemtray",
        "org.kde.plasma.digitalclock",
        "org.kde.plasma.lock_logout",
        "org.kde.plasma.icontasks",
        "org.kde.plasma.showdesktop",
    ]


class FakeBackend:
    def __init__(self, initial=None):
        self.initial = initial or []
        self.owned = []

    def inspect(self):
        return {"panels": self.initial + self.owned, "widgets": available()}

    def eval(self, script):
        if "var desired=" in script and "new Panel()" in script:
            token = json.loads(re.search(r"var owner=(\"[^\"]+\")", script).group(1))
            name = json.loads(re.search(r"var desired=(\{.+?\});var owner=", script).group(1))
            self.owned.append({
                "id": 100,
                "owner": token,
                "location": name["location"],
                "screen": 0,
                "widgets": [w["type"] for w in name["widgets"]],
            })
            return {"id": 100, "owner": token}
        if "p.remove()" in script:
            self.owned.clear()
            return {"removed": True}
        raise AssertionError("Unexpected JavaScript")


def test_load_both_presets():
    top = load_panel(ROOT, "topbar")
    dock = load_panel(ROOT, "dock")
    assert top.location == "top"
    assert dock.hiding == "autohide"
    assert dock.length_mode == "fit"
    assert all(w["type"].startswith("org.kde.plasma.") for w in dock.widgets)


def test_reject_path_traversal():
    with pytest.raises(ShellError, match="preset name"):
        load_panel(ROOT, "../bad")


def test_widget_allowlist(tmp_path):
    d = tmp_path / "config" / "shell"
    d.mkdir(parents=True)
    p = d / "bad.yaml"
    p.write_text(
        "name: bad\nlocation: top\nheight: 30\nlength_mode: fill\n"
        "hiding: none\nalignment: center\nwidgets:\n  - evil.plugin\n"
    )
    with pytest.raises(ShellError, match="allowlisted"):
        load_panel(tmp_path, "bad")


def test_script_escapes_json_data():
    spec = PanelSpec(
        "topbar", "top", 32, "fill", "none", "center",
        ({"type": "org.kde.plasma.kickoff", "config": {"General": {"icon": "';bad();"}}},)
    )
    js = create_script(spec, "opaque-token")
    assert "var desired=" in js
    assert '";bad();' not in js
    assert "new Panel()" in js


def test_parse_plasma_response():
    assert _parse_response("prefix\n" + SENTINEL + '{"panels":[]}\n') == {"panels": []}
    with pytest.raises(ShellError, match="did not return"):
        _parse_response("no marker")
    with pytest.raises(ShellError, match="test error"):
        _parse_response(SENTINEL + '{"error":"test error"}')


def test_existing_panel_collision_requires_acknowledgement():
    spec = load_panel(ROOT, "topbar")
    existing = {"panels": [{"id": 2, "location": "top", "screen": 0}],
                "widgets": available()}
    with pytest.raises(ShellError, match="share an edge"):
        check_conflicts(spec, existing)
    assert check_conflicts(spec, existing, allow_overlap=True)


def test_panel_creation_and_rollback(tmp_path):
    backend = FakeBackend()
    spec = load_panel(ROOT, "topbar")
    first = apply_panel(spec, tmp_path, backend, tmp_path)
    assert not first["already_installed"]
    assert load_record(tmp_path, "topbar")["status"] == "installed"
    second = apply_panel(spec, tmp_path, backend, tmp_path)
    assert second["already_installed"]
    rolled = rollback_panel("topbar", tmp_path, backend)
    assert rolled["removed"]
    assert load_record(tmp_path, "topbar") is None


def test_panel_collision_never_writes_record(tmp_path):
    backend = FakeBackend([{"id": 1, "location": "bottom", "screen": 0}])
    with pytest.raises(ShellError, match="share an edge"):
        apply_panel(load_panel(ROOT, "dock"), tmp_path, backend, tmp_path)
    assert load_record(tmp_path, "dock") is None


def test_rollback_without_ownership_fails(tmp_path):
    with pytest.raises(ShellError, match="No managed panel"):
        rollback_panel("topbar", tmp_path, FakeBackend())


def test_qdbus_script_is_read_only_when_inspecting():
    from plasma_rice.shell import inventory_script

    js = inventory_script()
    assert "panels().map" in js
    assert "new Panel()" not in js
    assert "remove()" not in js


def test_backend_uses_injected_executor():
    backend = PlasmaShellBackend(
        execute=lambda _: SENTINEL + '{"panels":[],"widgets":[]}'
    )
    assert backend.inspect() == {"panels": [], "widgets": []}
