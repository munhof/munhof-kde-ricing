import pytest
from plasma_rice.config import Operation
from plasma_rice.engine import apply, latest_receipt, plan, rollback


class FakeBackend:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.fail = None

    def read(self, file, group, key):
        return self.values.get((file, group, key))

    def write(self, file, group, key, value):
        identity = (file, group, key)
        if identity == self.fail:
            raise OSError("simulated disk failure")
        if value is None:
            self.values.pop(identity, None)
        else:
            self.values[identity] = value


def op(key, value):
    return Operation("test", "kwinrc", "Plugins", key, value)


def test_apply_rollback_restores_missing_key(tmp_path):
    backend = FakeBackend()
    transaction = apply(plan([op("blurEnabled", "true")], backend), backend, tmp_path, "laptop")
    assert transaction.exists()
    assert backend.read("kwinrc", "Plugins", "blurEnabled") == "true"
    assert rollback(backend, tmp_path) == (1, [])
    assert backend.read("kwinrc", "Plugins", "blurEnabled") is None
    assert latest_receipt(tmp_path) is None


def test_apply_idempotent(tmp_path):
    backend = FakeBackend()
    ops = [op("blurEnabled", "true")]
    assert apply(plan(ops, backend), backend, tmp_path, "laptop") is not None
    assert apply(plan(ops, backend), backend, tmp_path, "laptop") is None
    assert len(list((tmp_path / "receipts").glob("*.json"))) == 1


def test_rollback_refuses_external_changes(tmp_path):
    backend = FakeBackend()
    apply(plan([op("blurEnabled", "true")], backend), backend, tmp_path, "laptop")
    backend.write("kwinrc", "Plugins", "blurEnabled", "false")
    assert rollback(backend, tmp_path) == (0, ["kwinrc [Plugins] blurEnabled"])
    assert backend.read("kwinrc", "Plugins", "blurEnabled") == "false"
    assert latest_receipt(tmp_path) is not None


def test_reverts_changes_on_partial_failure(tmp_path):
    backend = FakeBackend({("kwinrc", "Plugins", "existing"): "before"})
    ops = [op("existing", "after"), op("bad", "true")]
    backend.fail = ("kwinrc", "Plugins", "bad")
    with pytest.raises(OSError):
        apply(plan(ops, backend), backend, tmp_path, "laptop")
    assert backend.read("kwinrc", "Plugins", "existing") == "before"
    assert latest_receipt(tmp_path) is None


def test_apply_rejects_concurrent_drift(tmp_path):
    backend = FakeBackend()
    p = plan([op("blurEnabled", "true")], backend)
    backend.write("kwinrc", "Plugins", "blurEnabled", "false")
    with pytest.raises(RuntimeError, match="changed since planning"):
        apply(p, backend, tmp_path, "laptop")


def test_rollback_refuses_tampered_receipt(tmp_path):
    import json
    backend = FakeBackend()
    receipt = apply(plan([op("blurEnabled", "true")], backend), backend, tmp_path, "laptop")
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["operations"][0]["file"] = "../other-file"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe transaction"):
        rollback(backend, tmp_path)
    assert backend.read("kwinrc", "Plugins", "blurEnabled") == "true"


def test_rollback_restores_existing_value(tmp_path):
    backend = FakeBackend({("kwinrc", "Plugins", "blurEnabled"): "false"})
    apply(plan([op("blurEnabled", "true")], backend), backend, tmp_path, "laptop")
    assert rollback(backend, tmp_path) == (1, [])
    assert backend.read("kwinrc", "Plugins", "blurEnabled") == "false"
