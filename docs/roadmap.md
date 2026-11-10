# Roadmap

- [x] v0.1 Foundation: declarative manifests, profile allowlists, doctor, plan, apply, rollback, CLI, tests and CI.
- [ ] v0.2 Tiling: verify Polonium integration on Garuda and test real-world layouts, shortcuts and excluded windows.
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
