from pathlib import Path
import pytest
from plasma_rice.config import ManifestError, resolve

ROOT = Path(__file__).resolve().parents[1]


def test_resolve_default():
    profile, ops, req = resolve(ROOT)
    assert profile == "laptop"
    assert [o.key for o in ops] == ["blurEnabled"]
    assert "effects" in req


def test_resolve_tiling():
    _, ops, requirements = resolve(ROOT, ["tiling"])
    assert [o.key for o in ops] == ["poloniumEnabled", "padding"]
    assert requirements["tiling"]["kwin_script"] == "polonium"


def test_duplicate_components_rejected():
    with pytest.raises(ManifestError, match="Repeated"):
        resolve(ROOT, ["effects", "effects"])


def test_no_path_traversal():
    with pytest.raises(ManifestError, match="Invalid component"):
        resolve(ROOT, ["../evil"])


def test_missing_profile_rejected():
    with pytest.raises(ManifestError):
        resolve(ROOT, ["effects"], "missing")
