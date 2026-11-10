# munhof-kde-ricing

Proyecto **declarativo, testeable y reversible** para personalizar KDE Plasma 6 sobre Garuda Linux sin reemplazar KWin ni eliminar Plasma. Inspiración visual: [Clean and Minimal KDE Rice (r/unixporn)](https://www.reddit.com/r/unixporn/comments/1tenpv1/kde_clean_and_minimal_rice/).

> **v0.1 — Foundation.** CLI funcional con `doctor`, `plan`, `apply`, `status`, `rollback`, manifiestos YAML, pruebas y CI. Todavía **no** reproduce el panel ni los bordes redondeados del rice de referencia.

## Principios

- No usa `sudo`, `pacman`, `curl` ni instala complementos externos.
- Modifica exclusivamente claves declaradas de `kwinrc` mediante `kreadconfig6` y `kwriteconfig6`.
- Cada transacción registra los valores anteriores en recibos locales.
- `rollback` se niega a sobrescribir modificaciones posteriores realizadas por el usuario.
- No modifica KScreen, PowerDevil, paneles de Garuda, pantalla táctil, rotación, SDDM ni suspensión.
- Polonium es opcional; debe instalarse primero desde KDE.

## Requisitos

KDE Plasma 6, Wayland, Python 3.11+, `uv` o `pip`, utilidades `kreadconfig6` y `kwriteconfig6`. Para el módulo tiling, también `kpackagetool6` y Polonium previamente instalado.

## Inicio rápido

```bash
git clone https://github.com/munhof/munhof-kde-ricing.git
cd munhof-kde-ricing
uv sync --extra dev
uv run plasma-rice doctor
uv run plasma-rice plan
uv run plasma-rice apply --dry-run
```

Los comandos anteriores no alteran la configuración de Plasma.

**Después de crear un snapshot y revisar el plan**, para aplicar el primer componente (blur):

```bash
uv run plasma-rice apply
uv run plasma-rice status
# Restaurar la última transacción si es necesario:
uv run plasma-rice rollback
```

Para probar Polonium después de instalarlo desde **Configuración del sistema → Gestión de ventanas → Scripts de KWin**, ejecutar:

```bash
uv run plasma-rice plan -c tiling
uv run plasma-rice apply --dry-run -c tiling
# Solo cuando la detección de Polonium y la configuración estén verificadas:
uv run plasma-rice apply -c tiling
```

**Advertencia:** todavía no se realizó una prueba de integración gráfica en tu Lenovo. La gestión del tiling incluye claves tentativas que deben verificarse frente a la versión instalada de Polonium antes de aplicar.

## Configuración

- `config/rice.yaml`: perfil y componentes seleccionados.
- `config/profiles/`: allowlists y perfiles laptop, desktop y tablet.
- `components/`: manifests separados de effects y tiling.
- `src/plasma_rice/`: CLI, backend KConfig, validación y rollback.
- `tests/`: pruebas unitarias sin tocar un sistema KDE.
- `docs/`: arquitectura, roadmap, compatibilidad y smoke tests.

## Verificaciones

```bash
uv run pytest -q
uv run ruff check src tests
```

La CI ejecuta pruebas en Python 3.11 y 3.13. El entorno de CI no comprueba la apariencia ni los gestos reales; estas pruebas requieren una sesión KDE Wayland.

## Seguridad y limitaciones

Los recibos se almacenan en `${XDG_STATE_HOME:-~/.local/state}/plasma-rice/receipts/`; no se suben a Git. Se intenta revertir cambios de una aplicación parcial, pero los cambios KConfig no son atómicos frente a un apagado inesperado. Se recomienda un snapshot de Garuda antes del primer `apply`.

Para los próximos módulos, consultar [roadmap](docs/roadmap.md) y [arquitectura](docs/architecture.md).

## Licencia

MIT.
