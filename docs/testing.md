# Testing

## Automated

Run `uv run pytest -q` and `uv run ruff check src tests`. The in-memory KConfig backend validates planning, drift rejection, rollback, idempotency and failure recovery without changing KDE.

## Manual smoke tests on Garuda

1. Create a Snapper snapshot (when configured).
2. Run `uv run plasma-rice doctor`, then `uv run plasma-rice plan`.
3. Run `uv run plasma-rice apply --dry-run`; inspect intended changes.
4. Run `uv run plasma-rice apply`; verify KWin blur.
5. Reapply and verify idempotence.
6. Run `uv run plasma-rice rollback`; verify prior state restored.
7. Install Polonium separately; then test `plan -c tiling`, followed by applying it only after verification.
8. Check hot-plug displays, suspend/resume, auto rotation and touch input.

CI cannot substitute for manual testing of the real Wayland session.
