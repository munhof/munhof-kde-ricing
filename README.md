# munhof-kde-ricing

Proyecto **declarativo, testeable y reversible** para personalizar KDE Plasma 6 sobre Garuda Linux sin reemplazar KWin ni eliminar Plasma. Inspiración visual: [Clean and Minimal KDE Rice (r/unixporn)](https://www.reddit.com/r/unixporn/comments/1tenpv1/kde_clean_and_minimal_rice/).

> **v0.6.1 — Compatibilidad Polonium/Waybar (experimental).** Waybar no solicita reservar espacio en KWin por defecto, para evitar la geometría deformada observada en Plasma 6.8.2. Se mantiene la selección de tamaño y la recuperación del perfil Original.

## Perfiles de KDE Plasma con la misma cuenta (v0.4)

**Este es el modo recomendado.** Podés usar el mismo usuario `munhof` con dos sesiones Wayland seleccionables en SDDM:

- **Plasma Original (Wayland)**: recupera la barra superior, dock, atajos, colores y KWin que ya usabas.
- **Plasma Rice (Wayland)**: guarda un estado visual separado y, en su primer inicio, aplica el prototipo con barra y dock minimalistas, Breeze Dark, blur y tiling padding.

Ambas sesiones usan el **mismo $HOME y las mismas aplicaciones**, pero intercambian archivos de configuración visual al entrar. No pueden ejecutarse simultáneamente. **Usá las dos nuevas entradas gestionadas**; elegir la entrada estándar **Plasma (Wayland)** no conmutará el perfil y mostrará el último estado activo.

```bash
cd ~/Escritorio/proyectos/munhof-kde-ricing
git pull --ff-only origin main
uv sync --extra dev
uv run pytest -q

# Preflight: no cambia el sistema
python3 scripts/session/install_profiles.py --user munhof

# Registra ambas entradas en SDDM; NO reemplaza la sesión existente.
sudo python3 scripts/session/install_profiles.py --user munhof --apply
```

Cerrá sesión. Elegí `munhof` y **Plasma Rice (Wayland)** o **Plasma Original (Wayland)** en SDDM. En el primer inicio se conserva una captura del escritorio actual en `~/.local/state/munhof-kde-ricing/profiles/`; los perfiles se guardan al cambiar desde SDDM. Si la inicialización falla, iniciá **Plasma Original (Wayland)**. Si necesitás intervención desde TTY, iniciá sesión como usuario normal y ejecutá `python3 /usr/local/libexec/munhof-plasma-rice-profilectl restore-original` cuando no haya ningún Plasma activo.

**El primer preset no es una réplica exacta de Waybar/Wofi del post de Reddit**; conserva los componentes nativos de Plasma y permite iterar sin afectar tu diseño original. Los perfiles actuales separan `kwinrc`, `kdeglobals`, `kglobalshortcutsrc`, `plasmarc`, `plasmashellrc` y `plasma-org.kde.plasma.desktop-appletsrc`. KScreen, energía y datos personales se comparten.

**Recuperación adicional (opcional):** el proyecto también incluye `scripts/session/install.py` para instalar **Plasma Rice Recovery (Wayland)** bajo una cuenta Linux distinta. No se ejecuta ni exige crear usuarios para habilitar los dos perfiles de `munhof`.

Leé la [guía de los dos perfiles](docs/profiles.md) y la [recuperación opcional](docs/isolated-session.md).


## Probar el aspecto del mock: barras y dock en ambas pantallas (v0.5)

El módulo opcional **Waybar + Wofi** aproxima el mock con una barra superior flotante oscura y un dock inferior con iconos **en todos los monitores conectados**. La barra superior, el dock y sus estilos están versionados en `appearance/`.

```fish
# Dependencias desde los repositorios oficiales de Arch
sudo pacman -S --needed waybar wofi ttf-jetbrains-mono-nerd pavucontrol

# Entrar primero en SDDM con el perfil Plasma Rice (Wayland)
cd ~/Escritorio/proyectos/munhof-kde-ricing
python3 scripts/appearance/appearancectl.py doctor
python3 scripts/appearance/appearancectl.py install
~/.local/bin/munhof-rice-appearance start
~/.local/bin/munhof-rice-appearance launcher
```

Al principio los paneles nativos de KDE seguirán visibles para que puedas confirmar que Waybar aparece en ambas pantallas. **No los elimines automáticamente**. Después de comprobar también el autostart de Waybar:

```fish
~/.local/bin/munhof-rice-appearance enable-autostart
# Solo después de probar dos monitores y reiniciar la sesión Rice:
~/.local/bin/munhof-rice-appearance replace-panels --confirm
```

Esto último guarda un respaldo local y elimina los paneles Plasma **solo del perfil Rice activo**. El perfil Original conserva su snapshot. Para volver a probar sin instalar nada más: `~/.local/bin/munhof-rice-appearance stop`.

**Limitaciones del prototipo:** el dock contiene accesos directos (todavía no es un gestor de ventanas abiertas); Wofi muestra resultados en lista (todavía no reproduce la cuadrícula de aplicaciones del mock); el wallpaper tampoco se cambia automáticamente. Ver [guía completa y recuperación](docs/appearance.md).

## Ajustar tamaños y distribución (v0.6)

La apariencia ahora parte de una barra superior de **42 px** y un dock inferior de **60 px**, con textos e iconos más legibles en tus pantallas 1920×1200/1920×1080. Waybar solicita una zona exclusiva a KWin para no quedar debajo de las ventanas (a verificar en tu entorno).

```fish
# Ejecutar en Plasma Rice
cd ~/Escritorio/proyectos/munhof-kde-ricing
python3 scripts/appearance/appearancectl.py install --update
~/.local/bin/munhof-rice-appearance tune --preset balanced
~/.local/bin/munhof-rice-appearance tune --preset balanced --apply
~/.local/bin/munhof-rice-appearance restart
```

Podés probar `--preset compact` o `--preset touch` y ajustar `--bar-height`, `--dock-height`, `--font-size`, `--icon-size` y `--edge-gap`. El comando sin `--apply` es solo vista previa; con `--apply` genera archivos de diseño propios y no modifica el perfil Original. Más información en [docs/appearance.md](docs/appearance.md).

## Principios

- La CLI de configuración evita `sudo`; los instaladores **optativos** de sesiones SDDM usan `sudo` solo para registrar sus entradas en el sistema.
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


## Barras, docks y utilidades (v0.3 experimental)

Los presets Plasma Shell son **complementarios**. No modifican, eliminan ni migran los paneles que Garuda ya tiene configurados. Se crean como paneles NUEVOS, con widgets de Plasma y un token de propiedad para poder revertirlos. La primera prueba real en Plasma 6.8 debe ser manual: el CI solo prueba la lógica Python.

**Paso 1: inspeccionar los paneles existentes, sin cambios:**

```bash
uv run plasma-rice shell inspect
uv run plasma-rice shell utilities
uv run plasma-rice shell plan topbar
uv run plasma-rice shell plan dock
```

Los ejemplos están en `config/shell/topbar.yaml` (barra superior: kickoff, pager, bandeja, reloj, bloqueo/apagado) y `config/shell/dock.yaml` (dock centrado con tareas solo iconos, aplicaciones favoritas y mostrar escritorio).

**Paso 2: simulación:**

```bash
uv run plasma-rice shell apply topbar --dry-run
uv run plasma-rice shell apply dock --dry-run
```

**Paso 3: aplicación explícita y reversible, solo luego de snapshot:**

```bash
uv run plasma-rice shell apply topbar
# Si el borde superior ya está ocupado, por decisión consciente:
uv run plasma-rice shell apply topbar --allow-overlap

# Al estar conforme con la barra superior, evaluar el dock:
uv run plasma-rice shell apply dock --allow-overlap

# Quitar solo los paneles creados por el proyecto:
uv run plasma-rice shell rollback dock
uv run plasma-rice shell rollback topbar
```

**Importante:** `--allow-overlap` no elimina el panel anterior; permite crear otro en el mismo borde. Si se ve superpuesto, revertí el panel del proyecto. Un panel modificado después de instalarse no se elimina automáticamente: requiere revisar la diferencia o usar `--force-owned`, que sigue exigiendo la marca de propiedad. El backup de la configuración original se conserva en `~/.local/state/plasma-rice/backups/` por si necesitás recuperación manual.

La captura de parámetros de **un panel preexistente** todavía no está implementada. Estos presets reproducen paneles nuevos, no hacen una copia exacta de los que ya usás.

El listado de utilidades en `config/shell/utilities.yaml` es informativo: KRunner, Klipper, Spectacle, KDE Connect, configuración del sistema y reproductores. No instala paquetes, altera atajos ni reemplaza notificaciones. El widget nativo *system tray* conserva los controles de red, audio, batería, portapapeles y notificaciones ya disponibles.

Para alcance técnico, limitaciones de multimonitor y recuperación: [Guía de Plasma Shell](docs/shell.md).

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
