"""CLI for side-by-side, opt-in Plasma panel and dock presets."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import typer
import yaml

from .shell import (
    PlasmaShellBackend,
    ShellError,
    apply_panel,
    check_conflicts,
    load_panel,
    load_record,
    rollback_panel,
)

shell_app = typer.Typer(no_args_is_help=True, help="Add and revert native Plasma panels/docks")


def _paths(project: Path) -> tuple[Path, Path, Path]:
    config_dir = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))).expanduser()
    state_dir = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))).expanduser()
    return project.resolve(), state_dir / "plasma-rice", config_dir


def _guard_plasma() -> None:
    if os.getenv("XDG_SESSION_TYPE", "").lower() != "wayland":
        raise ShellError("Apply/rollback requires a Wayland session")
    desktop = os.getenv("XDG_CURRENT_DESKTOP", "").lower()
    if "kde" not in desktop and "plasma" not in desktop:
        raise ShellError("Apply/rollback requires KDE Plasma")


def _display_plan(preset: str, project: Path) -> None:
    root, state, _ = _paths(project)
    spec = load_panel(root, preset)
    current = PlasmaShellBackend().inspect()
    prior = load_record(state, preset)
    typer.echo(f"Preset: {spec.name} ({spec.location}, {spec.height}px, {spec.hiding})")
    typer.echo("Widgets: " + ", ".join(w["type"] for w in spec.widgets))
    if prior:
        matched = [p for p in current["panels"] if p["owner"] == prior["token"]]
        typer.echo(
            f"Status: {'already installed (#'+str(matched[0]['id'])+')' if len(matched) == 1 else 'stale receipt; inspection needed'}"
        )
    else:
        collisions = check_conflicts(spec, current, allow_overlap=True)
        for message in collisions:
            typer.echo(f"OVERLAP: {message}")
        typer.echo("Status: would create a NEW panel; existing panels would remain untouched.")
        if collisions:
            typer.echo("Actual apply requires --allow-overlap to acknowledge edge conflicts.")


@shell_app.command("inspect")
def inspect(
    json_output: bool = typer.Option(False, "--json", help="Print raw inventory"),
) -> None:
    """Read existing panels, widget IDs and ownership markers without editing them."""
    try:
        current = PlasmaShellBackend().inspect()
        if json_output:
            typer.echo(json.dumps(current, ensure_ascii=False, indent=2))
            return
        for panel in current["panels"]:
            typer.echo(
                f"#{panel['id']} screen={panel['screen']} {panel['location']} "
                f"height={panel['height']} widgets={','.join(panel['widgets'])}"
                + (" [rice-managed]" if panel.get("owner") else "")
            )
    except (ShellError, OSError, ValueError) as exc:
        typer.echo(f"Inspect failed: {exc}", err=True)
        raise typer.Exit(2) from exc


@shell_app.command("plan")
def plan(
    preset: str = typer.Argument(..., help="topbar or dock"),
    project: Path = typer.Option(Path("."), "--project"),
) -> None:
    """Preview panel/dock deployment. Read-only."""
    try:
        _display_plan(preset, project)
    except (ShellError, OSError, ValueError, yaml.YAMLError) as exc:
        typer.echo(f"Plan failed: {exc}", err=True)
        raise typer.Exit(2) from exc


@shell_app.command("apply")
def apply(
    preset: str = typer.Argument(..., help="topbar or dock"),
    project: Path = typer.Option(Path("."), "--project"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    allow_overlap: bool = typer.Option(False, "--allow-overlap"),
) -> None:
    """Add one new owned panel; never replace or modify existing Garuda panels."""
    try:
        if dry_run:
            _display_plan(preset, project)
            typer.echo("Dry run: no changes.")
            return
        _guard_plasma()
        root, state, config_dir = _paths(project)
        spec = load_panel(root, preset)
        result = apply_panel(
            spec, state, PlasmaShellBackend(), config_dir, allow_overlap=allow_overlap
        )
        if result["already_installed"]:
            typer.echo(f"Already installed: panel #{result['id']}")
        else:
            typer.echo(f"Created {preset} panel #{result['id']}. Existing panels unchanged.")
            if result["backup"]:
                typer.echo(f"Original Plasma layout backup: {result['backup']}")
            typer.echo(f"Revert with: plasma-rice shell rollback {preset}")
    except (ShellError, OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
        typer.echo(f"Apply failed: {exc}", err=True)
        raise typer.Exit(2) from exc


@shell_app.command("rollback")
def rollback(
    preset: str = typer.Argument(..., help="Name of rice-created panel"),
    force_owned: bool = typer.Option(
        False, "--force-owned", help="Remove an edited panel, but only with matching owner token"
    ),
) -> None:
    """Remove only the panel owned by this tool. Never delete an unmanaged panel."""
    try:
        _guard_plasma()
        _, state, _ = _paths(Path("."))
        result = rollback_panel(preset, state, PlasmaShellBackend(), force_owned=force_owned)
        typer.echo(f"Removed rice-managed panel: {preset}")
        if result["backup"]:
            typer.echo(f"Original Plasma layout backup preserved: {result['backup']}")
    except (ShellError, OSError, ValueError, RuntimeError) as exc:
        typer.echo(f"Rollback failed: {exc}", err=True)
        raise typer.Exit(2) from exc


@shell_app.command("status")
def status() -> None:
    """List locally managed panels without modifying KDE."""
    _, state, _ = _paths(Path("."))
    directory = state / "shell"
    paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not paths:
        typer.echo("No panels managed by plasma-rice.")
        return
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        typer.echo(f"{path.stem}: {data.get('status')} (id={data.get('id', 'pending')})")


@shell_app.command("utilities")
def utilities(project: Path = typer.Option(Path("."), "--project")) -> None:
    """Read-only availability check for native KDE utility modules."""
    root, _, _ = _paths(project)
    config = yaml.safe_load((root / "config/shell/utilities.yaml").read_text(encoding="utf-8"))
    for item in config["utilities"]:
        found = shutil.which(item["command"])
        status_text = "OK" if found else "OPTIONAL/MISSING"
        typer.echo(f"{status_text:16} {item['name']}: {found or item['command']}")
