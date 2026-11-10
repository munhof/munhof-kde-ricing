# Architecture decision record — v0.1

## Purpose

Minimal and reversible KDE Plasma configuration on Garuda. Preserve monitor, touch, power, tablet and SDDM settings.

## Design

YAML manifests declare desired state. The resolver validates profile, component names, and allowed file/group/key operations. The planner compares live KConfig values. Apply writes only changed keys and records a receipt. Rollback detects external changes and refuses to overwrite them.

Components → resolver → plan → apply → KConfig → receipt → rollback.

## Safety boundaries

- Only `kwinrc` is managed in v0.1.
- No arbitrary commands in manifests.
- Apply and rollback require KDE Plasma Wayland.
- No downloads, sudo, package installation, or scripts from unknown sources.
- Snapper snapshots recommended before actual changes.

## Limitations

KConfig is not transactionally atomic across multiple keys. A power loss between writes and receipt persistence may require manual recovery. KWin reload might require logging out and back in. External plugins must be installed separately and are not reverted.
