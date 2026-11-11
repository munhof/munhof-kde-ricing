# Plasma Shell — additive topbar, dock and native utilities

## Scope

This v0.3 module manages **only new panels** via the [official Plasma scripting API](https://develop.kde.org/docs/plasma/scripting/). It invokes `qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript` and adds a token (`plasmaRiceOwner`) to the created panel's General config group. The project's record is stored in `${XDG_STATE_HOME:-~/.local/state}/plasma-rice/shell/`.

It deliberately **does not** modify existing panels, change your wallpaper, alter KDE Activities, override shortcuts, install third-party plasmoids, alter KScreen or PowerDevil, or disable the old taskbar.

## Presets

- `topbar`: 34px, full width, launcher, virtual-desktop pager, system tray, clock, lock/logout.
- `dock`: 48px, bottom, content-fit, centered, autohide, icon-only task manager with example launchers and show-desktop button.

Edit `config/shell/*.yaml` before deployment to adjust height, widget order and visibility mode. Only a fixed allowlist of native widgets is accepted; widget configuration values are JSON-encoded before embedding in the JavaScript API.

## Read-only preflight

```bash
uv run plasma-rice shell inspect
uv run plasma-rice shell utilities
uv run plasma-rice shell plan topbar
uv run plasma-rice shell apply topbar --dry-run
```

These commands do not change the desktop.

## Deploy/revert

Create a **Snapper snapshot first**. Run `uv run plasma-rice shell apply topbar`; if an existing top panel occupies the same edge it will refuse to proceed. You can explicitly allow an additional panel with `--allow-overlap`.

Revert with `uv run plasma-rice shell rollback topbar`. This removes only the panel with the receipt's ownership token. If you changed the panel's widgets, height, hiding mode or alignment, rollback will refuse to remove it unless you use `--force-owned`. Even then it requires the ownership token.

A copy of the original `plasma-org.kde.plasma.desktop-appletsrc` is kept under `~/.local/state/plasma-rice/backups/` before a panel is created. The tool does not copy this file back automatically because doing so could overwrite independent changes to your desktop.

## Known limitations / testing

- **Not yet tested on a live Plasma 6.8 session**; verify the scripting API through `shell inspect` before applying. Automated CI uses a fake backend, not plasmashell.
- The Panel constructor chooses a display according to Plasma's own defaults; this version does not implement per-output binding or multi-monitor profiles. Existing monitor layouts remain untouched.
- Applet appearance remains under Plasma themes; these presets do not achieve Waybar-like transparency or a floating island without additional styling.
- A power interruption after D-Bus panel creation may leave a pending local receipt; **do not delete that receipt blindly**. It contains the ownership token used for safe recovery.
- Modifications to pinned launchers after deployment count as widget configuration changes, which currently are not compared by automatic rollback; do not use `--force-owned` unless you're sure the dock can be removed.
- This module cannot export arbitrary existing Garuda panels. It only reproduces panels it creates.

### Utilities

The `shell utilities` command checks presence of KDE-native tools and optional Playerctl. Plasma itself already provides notifications, energy, network and volume controls via its system tray. This project currently does not install apps or configure global shortcuts.
