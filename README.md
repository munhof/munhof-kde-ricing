# munhof-kde-ricing

Proyecto **declarativo, testeable y reversible** para personalizar KDE Plasma 6 sobre Garuda Linux sin reemplazar KWin ni eliminar Plasma. Inspiración visual: [Clean and Minimal KDE Rice (r/unixporn)](https://www.reddit.com/r/unixporn/comments/1tenpv1/kde_clean_and_minimal_rice/).

> **v0.2 — Tiling.** Además de la CLI reversible, podés capturar los ajustes **globales** que ya funcionan en Polonium y aplicar un preset visual opcional que oculta bordes en ventanas tiled. No modifica los paneles de Garuda ni los monitores.

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

**Validación actual:** el usuario comprobó que Polonium funciona en Plasma 6.8.2. No se probó todavía el preset visual opcional, ni el flujo de captura en una sesión KDE real; la CI valida lógica y serialización.

## Capturar el tiling que ya tenés configurado (v0.2)

No vuelvas a configurar Polonium desde cero: la CLI puede **leer exclusivamente claves permitidas** de `kwinrc` y convertirlas en un componente reproducible.

```bash
# Vista previa, sin crear archivos:
uv run plasma-rice capture --dry-run

# Crear el componente desde el estado real de tu KDE:
uv run plasma-rice capture

# Comprobar que coincide con lo instalado:
uv run plasma-rice plan -c tiling-captured
```

El archivo resultante será `components/tiling-captured/manifest.yaml`; no se sobrescribirá si ya existe. Captura solo parámetros globales y explícitamente presentes de `[Plugins]`, `[Tiling]` y `[Script-polonium]`; **no copia** perfiles de monitores, paneles, reglas ni bases de datos de KDE. Por defecto excluye filtros de procesos y títulos de ventanas por privacidad. Revisá el YAML antes de versionarlo en Git.

Para optar por capturar filtros de exclusión, usar `--include-filters` (pueden revelar nombres de apps o títulos de ventanas); **no se recomienda subirlo sin revisar**.

Para aplicar el componente capturado en otra sesión, primero verificá Polonium y después usá `plan -c tiling-captured` y `apply -c tiling-captured`. Su aplicación es reversible mediante `rollback` mientras las claves no hayan cambiado por fuera.

### Primer cambio visual opcional: ventanas tiled sin bordes

```bash
uv run plasma-rice plan -c minimal-tiling
uv run plasma-rice apply --dry-run -c minimal-tiling
# Luego de revisar y hacer un respaldo:
uv run plasma-rice apply -c minimal-tiling
# Para revertir exactamente la última transacción:
uv run plasma-rice rollback
```

El preset usa `[Script-polonium] Borders=1` (bordes solo para ventanas flotantes según la UI actual de Polonium). **Puede requerir cerrar e iniciar sesión para verse**. Si tu versión de Polonium cambia la semántica del ajuste, no lo apliques hasta comprobarlo en el engranaje de su configuración.

Más detalles: [Polonium y captura](docs/polonium.md).

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
