from typer.testing import CliRunner
from plasma_rice.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output
    assert "rollback" in result.output


def test_unsafe_session_rejected(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    result = runner.invoke(app, ["rollback"])
    assert result.exit_code == 2
    assert "Wayland" in result.output
