from pathlib import Path

import pytest

from plasma_rice.capture import build_manifest, save_manifest, validate_output
from plasma_rice.config import ManifestError, load_component
from plasma_rice.engine import plan


class FakeBackend:
    def __init__(self, values):
        self.values = values
        self.reads = []

    def read(self, file, group, key):
        self.reads.append((file, group, key))
        return self.values.get((file, group, key))


def cfg(group, key):
    return ("kwinrc", group, key)


def test_capture_only_known_global_keys():
    values = {
        cfg("Plugins", "poloniumEnabled"): "true",
        cfg("Tiling", "padding"): "10",
        cfg("Script-polonium", "Borders"): "1",
        cfg("Script-polonium", "DefaultEngine"): "0",
        cfg("Script-polonium", "FilterCaption"): "private app window title",
        cfg("General", "secret"): "private-value",
    }
    backend = FakeBackend(values)
    manifest = build_manifest(backend)
    keys = [(op["group"], op["key"]) for op in manifest["operations"]]
    assert keys == [
        ("Plugins", "poloniumEnabled"),
        ("Tiling", "padding"),
        ("Script-polonium", "Borders"),
        ("Script-polonium", "DefaultEngine"),
    ]
    assert cfg("General", "secret") not in backend.reads
    assert cfg("Script-polonium", "FilterCaption") not in backend.reads


def test_private_filters_require_opt_in():
    backend = FakeBackend({
        cfg("Plugins", "poloniumEnabled"): "true",
        cfg("Script-polonium", "FilterCaption"): "private window",
    })
    manifest = build_manifest(backend, include_filters=True)
    assert any(op["key"] == "FilterCaption" for op in manifest["operations"])


def test_capture_requires_enabled_polonium():
    with pytest.raises(ManifestError, match="Enable Polonium"):
        build_manifest(FakeBackend({}))


def test_capture_skips_absent_and_empty_values():
    backend = FakeBackend({
        cfg("Plugins", "poloniumEnabled"): "true",
        cfg("Tiling", "padding"): "",
    })
    manifest = build_manifest(backend)
    assert [op["key"] for op in manifest["operations"]] == ["poloniumEnabled"]


def test_capture_manifest_roundtrip_into_component_loader(tmp_path):
    backend = FakeBackend({
        cfg("Plugins", "poloniumEnabled"): "true",
        cfg("Tiling", "padding"): "10",
    })
    out = validate_output(tmp_path, Path("components/tiling-captured/manifest.yaml"))
    save_manifest(out, build_manifest(backend))
    ops, requirements = load_component(tmp_path, "tiling-captured")
    assert len(ops) == 2
    assert requirements["kwin_script"] == "polonium"
    assert all(not change.changed for change in plan(ops, backend))


def test_capture_does_not_overwrite_existing_manifest(tmp_path):
    out = validate_output(tmp_path, Path("components/tiling-captured/manifest.yaml"))
    manifest = build_manifest(FakeBackend({cfg("Plugins", "poloniumEnabled"): "true"}))
    save_manifest(out, manifest)
    first = out.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        save_manifest(out, manifest)
    assert out.read_text(encoding="utf-8") == first


@pytest.mark.parametrize(
    "output",
    [
        Path("../outside/manifest.yaml"),
        Path("components/outside/other.yaml"),
        Path("components/../../other/manifest.yaml"),
        Path("components/BAD-NAME/manifest.yaml"),
    ],
)
def test_capture_rejects_unsafe_path(tmp_path, output):
    with pytest.raises(ValueError):
        validate_output(tmp_path, output)


def test_capture_rejects_multiline_value():
    backend = FakeBackend({
        cfg("Plugins", "poloniumEnabled"): "true",
        cfg("Script-polonium", "Borders"): "1\n2",
    })
    with pytest.raises(ManifestError, match="multiline"):
        build_manifest(backend)
