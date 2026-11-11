# munhof-kde-ricing

Configuración reproducible y reversible de **KDE Plasma 6 Wayland sobre Garuda**, utilizando solamente componentes nativos de Plasma y **Polonium**. Inspiración estética: [Clean and Minimal KDE Rice](https://www.reddit.com/r/unixporn/comments/1tenpv1/kde_clean_and_minimal_rice/).

> **v0.8 — Retorno a Plasma nativo.** Dejamos de usar Waybar, Wofi y Quickshell. Sus prototipos se conservan en el historial Git, pero ya no pertenecen a la configuración activa. Los paneles se editan con las herramientas integradas de KDE. No se modifican automáticamente las pantallas ni los ajustes de la cuenta original.

## Arquitectura

SDDM ofrece dos entradas para **el mismo usuario**, sin reinstalar KDE:

- **Plasma Original (Wayland):** configuración original de Garuda.
- **Plasma Rice (Wayland):** configuración independiente de KWin, paneles, widgets, temas y atajos, usando el mismo HOME, aplicaciones y documentos.

El perfil `rice` mantiene KWin, Polonium, KRunner, el administrador de tareas de Plasma, widgets y temas KDE. **No se pueden iniciar ambas sesiones Plasma del mismo usuario simultáneamente.** La entrada estándar «Plasma (Wayland)» NO conmuta los perfiles, por lo que conviene utilizar las dos entradas gestionadas.

Se conserva la [recuperación opcional con otra cuenta](docs/isolated-session.md). La administración de perfiles se explica en [docs/profiles.md](docs/profiles.md).

## Migración desde Waybar/Quickshell

**Ejecutar dentro de Plasma Rice (Wayland)**, sin `sudo`:

```fish
cd ~/Escritorio/proyectos/munhof-kde-ricing
git switch main
git pull --ff-only origin main

# Vista previa de los elementos de nuestro prototipo externo.
python3 scripts/native/retire_external.py

# Desactiva nuestro autostart y detiene solo nuestra instancia Waybar.
python3 scripts/native/retire_external.py --apply

# Comprobar si queda alguna sesión Quickshell iniciada a mano.
pgrep -af quickshell
```

Si Quickshell todavía corre, cerrala con **Ctrl+C en la terminal que la lanzó**. No uses `pkill` global si tenés otras instancias Quickshell. Esta migración no elimina paquetes, paneles Plasma, atajos, monitores ni configuraciones del perfil Original.

Si anteriormente eliminaste los paneles de Rice para usar Waybar, volvé a agregarlos desde el **modo de edición de KDE** (ver abajo). No copies manualmente `plasma-org.kde.plasma.desktop-appletsrc` con Plasma en funcionamiento.

## Diseño con el editor integrado de KDE

**Diseño objetivo por pantalla:**

| Componente | Configuración |
|---|---|
| Panel superior | 38 px, flotante, ancho completo, siempre visible, opacidad adaptativa |
| Dock inferior | 54 px, flotante, longitud ajustada al contenido, centrado, auto-ocultación |
| Panel superior (widgets) | Lanzador, paginador, espaciador, bandeja del sistema, reloj |
| Dock (widgets) | Administrador de tareas solo con iconos, mostrar escritorio |
| Estética | Breeze Dark o tema oscuro de Garuda, acento violeta, blur de KWin |
| Distribución | Polonium existente; gap de referencia 10 px |

En cada monitor: **clic derecho en el escritorio → Entrar en modo edición → Añadir panel** (si falta) → seleccionar el panel y configurar su posición, estilo **Flotante**, altura, longitud, visibilidad y widgets. Repetir en el segundo monitor. No agregues múltiples docks superpuestos sobre un mismo borde.

Los detalles para el Lenovo 1920×1200 y la pantalla externa 1920×1080, con capturas previas y plan de reversión, están en [docs/native-appearance.md](docs/native-appearance.md).

```fish
# Consulta de paneles sin modificaciones:
uv run plasma-rice shell inspect

# Comprobar el script de tiling sin aplicar cambios:
uv run plasma-rice plan --component tiling
```

## Instalación de los dos perfiles (si todavía no la hiciste)

```fish
uv sync --extra dev
uv run pytest -q
python3 scripts/session/install_profiles.py --user munhof
sudo python3 scripts/session/install_profiles.py --user munhof --apply
```

El instalador SDDM requiere permiso administrativo para registrar las entradas, pero no sustituye la configuración visual de tu sesión en ejecución. **No vuelvas a ejecutarlo para actualizar colores, dock o widgets**: eso se hace desde el editor de Plasma dentro del perfil Rice.

## Estructura del proyecto

- `src/plasma_rice/`: CLI, captura declarativa KConfig, preflight y rollback.
- `config/shell/`: recetas de referencia para panel superior, dock y utilidades nativas.
- `scripts/session/`: sesiones SDDM, perfiles Original/Rice y recuperación.
- `scripts/native/retire_external.py`: limpieza controlada del prototipo anterior.
- `docs/native-appearance.md`: guía de diseño visual y trabajo manual en Plasma.
- `tests/`: validaciones automatizadas; no reemplazan una prueba real en KWin.

## Seguridad y límites

- Configurá el rice **únicamente dentro de «Plasma Rice (Wayland)»**.
- Los dos perfiles comparten algunas configuraciones fuera de la allowlist, como KScreen y servicios systemd de usuario. No cambies la escala global de monitores suponiendo que está aislada.
- No ejecutes acciones destructivas sobre paneles sin inspeccionar y respaldar previamente su estado.
- Los paneles nativos pueden tener un estilo flotante, pero **no replican exactamente** múltiples islas Waybar independientes; esa diferencia visual es deliberada para conservar la integración con Polonium.
- Los cambios a `config/shell/*.yaml` son documentación declarativa para posteriores automatizaciones. El modo edición de Plasma continúa siendo el método principal y confiable de aplicar el estilo.

Consulta [roadmap](docs/roadmap.md), [arquitectura de Polonium](docs/polonium.md) y [módulo opcional de paneles nativos](docs/shell.md).
