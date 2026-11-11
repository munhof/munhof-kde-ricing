# Roadmap

- [x] v0.1 Foundation: declarative manifests, profile allowlists, doctor, plan, apply, rollback, CLI, tests and CI.
- [x] v0.2 Tiling configuration: capture supported global Polonium keys and a reversible border preset. Manual hot-plug and GUI tests remain.
- [ ] v0.2.1 Keyboard shortcuts, per-desktop layouts, and window exclusion UX.
- [x] v0.3-alpha Plasma Shell: native additive topbar/dock presets, safe ownership, dry run, rollback and utility checks (live KDE testing pending).
- [x] v0.4-alpha: dos sesiones Wayland gestionadas para el mismo usuario, capturas originales, guardado al conmutar, recuperación y opción de cuenta separada.
- [x] v0.5-alpha: Waybar superior y dock inferior en todas las pantallas; Wofi; instalación local, prueba manual y retiro de paneles Plasma bajo confirmación.
- [x] v0.6-alpha: presets compact/balanced/touch, edición validada de dimensiones y test de dos monitores.
- [x] v0.6.1: desactivar exclusividad Waybar por defecto para evitar deformar ventanas bajo Polonium/KWin, manteniendo opt-in experimental.
- [ ] v0.6.2: integración real del workarea con los gaps exteriores de Polonium y dos monitores; sin overlays sobre bordes.
- [ ] v0.5-beta: KWin task manager para el dock, launcher en cuadrícula, wallpaper y pruebas gráficas reales en Plasma 6.8.
- [ ] v0.4-beta: pruebas reales en Plasma 6.8 y perfiles por monitor.
- [ ] v0.3 Appearance: theme, blur, colors, decorations, fonts and wallpapers with reversible adapters.
- [ ] v0.4 Shell: configurable Plasma panel, launcher and power menu; assess Waybar compatibility.
- [ ] v0.5 Profiles: laptop, desktop, tablet, external monitor adaptation.
- [ ] v0.6 Visual regression and multi-monitor testing.

## Acceptance criteria

1. Applying the same manifest twice is idempotent.
2. Rollback restores prior key values or removes previously nonexistent keys.
3. Rollback refuses conflicts introduced after apply.
4. Doctor, plan and dry-run are read-only.
5. No operations reach files outside the profile allowlist.

- [x] v0.7-alpha: prototipo no destructivo de islas Quickshell por monitor, ajustadas al contenido y con hotplug.
- [ ] v0.7-beta: integrar workarea/gaps KWin/Polonium; validar QML en Plasma 6.8, comportamiento multimonitor y gestión de ventanas.

- [x] v0.7.1-alpha: namespace propio de Quickshell, dimensiones de superficie explícitas, diagnóstico de clase y guía de filtros Polonium.
- [ ] v0.7.2: contar ventanas en KWin antes/después, excluir las islas si KWin las expone y test de área de trabajo con Quickshell.
