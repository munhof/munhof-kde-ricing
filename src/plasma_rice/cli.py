"""Safe, explicit CLI for KDE Plasma configuration changes."""
from __future__ import annotations

import json
import os
from pathlib import Path
import typer

from .config import ManifestError, resolve
from .doctor import check_requirements, inspect_system
from .engine import apply as run_apply, latest_receipt, plan as build_plan, rollback as run_rollback
from .kconfig import KConfigBackend, reconfigure_kwin

app = typer.Typer(no_args_is_help=True, help="Declarative KDE Plasma rice configuration")


def _roots(project: Path) -> tuple[Path, Path, KConfigBackend]:
    config_dir = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))).expanduser()
    state_base = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))).expanduser()
    return project.resolve(), state_base / "plasma-rice", KConfigBackend(config_dir)


def _resolve_or_exit(project: Path, component: list[str] | None, profile: str | None):
    try:
        return resolve(project, component or None, profile)
    except (ManifestError, OSError) as exc:
        typer.secho(f"Configuration error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc


def _guard_session() -> None:
    if os.getenv("XDG_SESSION_TYPE", "").lower() != "wayland":
        typer.echo("Apply is restricted to a Wayland session.", err=True)
        raise typer.Exit(2)
    desktop = os.getenv("XDG_CURRENT_DESKTOP", "").lower()
    if "kde" not in desktop and "plasma" not in desktop:
        typer.echo("Apply is restricted to KDE Plasma sessions.", err=True)
        raise typer.Exit(2)


@app.command()
def doctor() -> None:
    """Inspect KDE/Wayland dependencies; never modifies the system."""
    for name, ok, details in inspect_system():
        typer.echo(f"{'OK  ' if ok else 'WARN'} {name}: {details}")


@app.command()
def plan(project: Path = typer.Option(Path("."), help="Repository root"),
         component: list[str] = typer.Option([], "--component", "-c"),
         profile: str | None = typer.Option(None),
         json_output: bool = typer.Option(False, "--json")) -> None:
    """Preview exact KConfig key changes; no writes."""
    root, _, backend = _roots(project)
    profile_name, ops, req = _resolve_or_exit(root, component, profile)
    changes = build_plan(ops, backend)
    missing = check_requirements(req)
    data = {"profile": profile_name, "changes": [
        {"component": c.operation.component, "file": c.operation.file,
         "group": c.operation.group, "key": c.operation.key,
         "old": c.before, "new": c.operation.value, "changed": c.changed} for c in changes
    ], "missing_requirements": missing}
    if json_output:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return
    for item in data["changes"]:
        tag = "CHANGE" if item["changed"] else "UNCHANGED"
        typer.echo(f"{tag:9} {item['file']} [{item['group']}] {item['key']}: "
                   f"{item['old']!r} -> {item['new']!r}")
    for warning in missing:
        typer.echo(f"PREREQUISITE: {warning}")


@app.command()
def apply(project: Path = typer.Option(Path("."), help="Repository root"),
          component: list[str] = typer.Option([], "--component", "-c"),
          profile: str | None = typer.Option(None),
          dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Apply KConfig key changes after safeguards; no sudo, downloads or panel changes."""
    root, state_dir, backend = _roots(project)
    profile_name, ops, req = _resolve_or_exit(root, component, profile)
    changes = build_plan(ops, backend)
    if dry_run:
        for change in changes:
            typer.echo(f"{'CHANGE' if change.changed else 'UNCHANGED'} {change.operation.identity}: "
                       f"{change.before!r} -> {change.operation.value!r}")
        typer.echo("Dry run: no files changed.")
        return
    _guard_session()
    missing = check_requirements(req)
    if missing:
        for error in missing:
            typer.echo(f"ERROR: {error}", err=True)
        raise typer.Exit(2)
    try:
        receipt = run_apply(changes, backend, state_dir, profile_name)
    except Exception as exc:
        typer.echo(f"Apply failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    if receipt:
        typer.echo(f"Applied. Local receipt: {receipt}")
        typer.echo(reconfigure_kwin())
    else:
        typer.echo("Already in desired state; no changes.")


@app.command()
def status() -> None:
    """Display latest local transaction; read-only."""
    _, state_dir, _ = _roots(Path("."))
    receipt = latest_receipt(state_dir)
    typer.echo(f"Latest transaction: {receipt}" if receipt else "No managed transactions.")


@app.command()
def rollback() -> None:
    """Revert latest transaction only if its managed keys are unchanged."""
    _guard_session()
    _, state_dir, backend = _roots(Path("."))
    try:
        count, conflicts = run_rollback(backend, state_dir)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        typer.echo(f"Rollback failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    if conflicts:
        typer.echo("Rollback refused: the following keys changed after apply:", err=True)
        for key in conflicts:
            typer.echo(f"  {key}", err=True)
        raise typer.Exit(2)
    typer.echo(f"Restored {count} key(s).")
    typer.echo(reconfigure_kwin())


if __name__ == "__main__":
    app()
