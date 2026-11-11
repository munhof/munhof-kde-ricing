# Plasma Rice como sesión Wayland aislada

**Objetivo:** iniciar un segundo KDE Plasma 6 con apariencia minimalista en un usuario de prueba independiente. No se implementa un simple panel adicional en el KDE habitual. El usuario principal nunca debe seleccionarse para esta sesión.

## Por qué otra cuenta

Las sesiones KDE Plasma modernas dependen de servicios administrados por systemd por usuario. Una segunda entrada de SDDM que cambie solo `XDG_CONFIG_HOME` no aísla todos los servicios ni los datos. El aislamiento mediante otro usuario Linux es deliberado: todos sus `~/.config`, `~/.local/share`, navegador, aplicaciones y ajustes de pantalla pertenecen exclusivamente a ese usuario.

## Instalación en Garuda Linux (reversible y sin sobrescribir)

```bash
cd ~/Escritorio/proyectos/munhof-kde-ricing
git pull --ff-only origin main
uv sync --extra dev
uv run pytest -q

# Comprobar que no existía:
id kde-rice

# Crear cuenta de PRUEBA, una sola vez:
sudo useradd -m -s /bin/bash kde-rice
sudo passwd kde-rice

# Mostrar exactamente los archivos que se crearían:
python3 scripts/session/install.py --user kde-rice

# Registrar sesión SDDM y su primer inicio:
sudo python3 scripts/session/install.py --user kde-rice --apply
```

El instalador rechaza archivos existentes cuyo contenido no coincide. No instala software de Internet ni cambia la contraseña. La cuenta se crea y recibe contraseña en pasos separados y explícitos.

Archivos del sistema creados:

```text
/usr/share/wayland-sessions/munhof-plasma-rice.desktop
/usr/local/libexec/munhof-plasma-rice-session
/usr/local/libexec/munhof-plasma-rice-first-run
/usr/local/share/munhof-kde-ricing/recipe.json
/usr/local/share/munhof-kde-ricing/account
/home/kde-rice/.config/autostart/munhof-plasma-rice-first-run.desktop
```

## Primer inicio

1. Cerrá sesión en `munhof`.
2. En SDDM elegí el usuario **kde-rice**.
3. En el selector de sesiones elegí **Plasma Rice (Wayland)**.
4. Ingresá con la contraseña de esa cuenta.
5. El servicio de primer inicio configura la paleta oscura, efectos KWin, **barra superior** con menú/escritorios/bandeja/reloj y **dock inferior** con íconos y ocultación automática.

Para volver al escritorio intacto: cerrá sesión, elegí el usuario **munhof** y su sesión habitual **Plasma (Wayland)**.

El script de inicio se niega a ejecutarse bajo otros usuarios. El primer inicio se marca en `~/.local/state/munhof-kde-ricing/initialized-v1.json` (dentro de `/home/kde-rice`), evitando que se reemplacen los paneles en cada inicio posterior.

## Tiling y aplicaciones de la sesión independiente

Como Polonium fue instalado a nivel de usuario, **el usuario de prueba no lo hereda**. Ingresá como `kde-rice`, abrí Configuración del sistema → Gestión de ventanas → Scripts de KWin → Obtener nuevos… → Polonium, activalo y elegí el mismo layout que te gustó. El preset de `[Tiling] padding=10` ya estará disponible.

KRunner, Dolphin, Konsole, Spectacle, KDE Connect y los widgets de Plasma instalados globalmente estarán disponibles, pero los datos personales y las cuentas de estas aplicaciones no se copiarán. La sesión tiene su propia configuración de monitores; permite múltiples pantallas sin alterar los archivos de KScreen de tu usuario habitual.

## Alcance estético inicial

- Breeze Dark, efecto blur activado, separación nativa 10 px, topbar 34 px y dock 48 px.
- Barra/dock usan widgets nativos Plasma, no Waybar/Wofi todavía.
- **No es una réplica visual exacta del post de Reddit**: quedan pendientes wallpaper, fuentes, flotación, opacidad y launcher externo.
- La primera implementación genera paneles en el monitor que Plasma elija por defecto; todavía **no administra paneles por monitor**. La detección de pantallas funciona con KDE/KScreen.

## Diagnóstico y recuperación

Si el primer inicio no transforma los paneles, revisá como `kde-rice`:

```bash
/usr/local/libexec/munhof-plasma-rice-first-run --dry-run
/usr/local/libexec/munhof-plasma-rice-first-run
```

Se guarda una copia inicial en `/home/kde-rice/.local/state/munhof-kde-ricing/panels-before-first-run.ini` cuando existe la configuración previa. Las operaciones de panel no son atómicas: ante errores es mejor cerrar sesión y regresar a tu usuario habitual antes de diagnosticar.

Para dejar de mostrar la segunda sesión en SDDM, después de cerrar la cuenta de prueba:

```bash
sudo rm /usr/share/wayland-sessions/munhof-plasma-rice.desktop
```

Los demás archivos del instalador están listados arriba; podés borrarlos manualmente si querés desinstalarlo. **No ejecutes `userdel -r` sin revisar:** borraría la carpeta personal de la cuenta de prueba. Ninguna operación del proyecto elimina usuarios ni el contenido de sus homes.

## Cómo iterar

Editá `session/recipe.json` en el repositorio y validalo con `uv run pytest -q`. La instalación v0.4 se niega a sobrescribir un preset desplegado con contenido distinto. El mecanismo de actualización/rollback de recetas dentro de la cuenta de prueba es trabajo pendiente, no está automatizado aún. Nunca edites directamente las configuraciones de tu usuario `munhof` para probar variantes.

Fuentes técnicas:
- https://wiki.archlinux.org/title/SDDM
- https://wiki.archlinux.org/title/KDE
- https://develop.kde.org/docs/plasma/scripting/
- https://develop.kde.org/docs/plasma/scripting/api/
