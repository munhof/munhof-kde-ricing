# munhof-kde-ricing

Proyecto **declarativo, testeable y reversible** para personalizar KDE Plasma 6 sobre Garuda Linux sin reemplazar KWin ni eliminar Plasma. Inspiración visual: [Clean and Minimal KDE Rice (r/unixporn)](https://www.reddit.com/r/unixporn/comments/1tenpv1/kde_clean_and_minimal_rice/).

> **v0.4 — Sesión Wayland independiente (experimental).** Ahora se puede instalar *Plasma Rice (Wayland)* como segunda sesión de SDDM con una **cuenta Linux dedicada**. En esa cuenta se reemplazan los paneles predeterminados por la barra/dock del rice; el usuario principal de Garuda permanece intacto.

## Nueva opción: segunda sesión **Plasma Rice (Wayland)** (v0.4)

**Para probar el rice sin tocar tu KDE habitual, este es el camino recomendado.** Se utiliza una cuenta de prueba independiente porque Plasma también comparte servicios de usuario administrados por systemd; usar únicamente `XDG_CONFIG_HOME` con la misma cuenta no garantiza aislamiento.

- Instalación explícita de una entrada nueva en SDDM: **Plasma Rice (Wayland)**.
- Usuario independiente: `kde-rice` (no se crea sin pedirlo).
- Primer inicio: Breeze Dark, blur, padding de KWin, barra superior minimalista y dock inferior autohide.
- Se sustituyen los paneles por defecto **solo dentro de la cuenta de prueba**.
- La sesión normal `munhof` / **Plasma (Wayland)** conserva paneles, aplicaciones, monitor, energía y configuraciones.
- El diseño actual usa **paneles Plasma nativos**, todavía no Waybar/Wofi ni copia visual exacta del rice; Polonium debe instalarse para la cuenta de prueba.

```bash
# Dentro del repositorio
git pull --ff-only origin main
uv sync --extra dev
uv run pytest -q

# Crear deliberadamente un usuario nuevo; NO uses tu usuario habitual.
sudo useradd -m -s /bin/bash kde-rice
sudo passwd kde-rice

# Ver el plan sin cambios
python3 scripts/session/install.py --user kde-rice

# Registrar la segunda sesión (con sudo, solo en este paso)
sudo python3 scripts/session/install.py --user kde-rice --apply
```

Después **cerrá sesión**: en SDDM seleccioná el usuario `kde-rice` y la sesión **Plasma Rice (Wayland)**. Al entrar se configura automáticamente el rice inicial. Para volver, cerrá sesión y elegí tu usuario habitual y **Plasma (Wayland)**.

El instalador no ejecuta `useradd`, no altera SDDM autologin, no elimina usuarios y se niega a sobrescribir archivos ajenos. Toda eliminación es deliberada. Leé la [guía de sesión aislada](docs/isolated-session.md) antes de instalar.

## Principios

- La CLI existente no usa `sudo`, `pacman` ni descargas externas. El **instalador optativo de la segunda sesión** sí necesita ejecutarse explícitamente con `sudo` porque registra una entrada en SDDM.
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
