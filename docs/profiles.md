# Dos perfiles de Plasma Wayland con el mismo usuario

## Propósito

La cuenta habitual munhof puede iniciar desde SDDM dos entradas gestionadas:

- Plasma Original (Wayland): restaura sus paneles, dock, atajos y configuración de KWin.
- Plasma Rice (Wayland): utiliza otro perfil de configuraciones de Plasma y un diseño inicial minimalista.

Las dos sesiones usan el mismo HOME, documentos y aplicaciones. KScreen, energía, datos de apps y servicios systemd de usuario quedan compartidos. No se pueden ejecutar simultáneamente dos sesiones Plasma con el mismo usuario.

Importante: la entrada estándar Plasma (Wayland) que instala Garuda NO conmuta perfiles. Siempre seleccioná una de las dos entradas gestionadas al probar.

## Instalación

Desde el repositorio, ejecutar:

    cd ~/Escritorio/proyectos/munhof-kde-ricing
    git pull --ff-only origin main
    uv sync --extra dev
    uv run pytest -q
    python3 scripts/session/install_profiles.py --user munhof

Ese último comando es una vista previa. Para instalar las entradas en SDDM:

    sudo python3 scripts/session/install_profiles.py --user munhof --apply

Cerrá la sesión actual. En SDDM elegí el mismo usuario munhof y Plasma Original (Wayland) o Plasma Rice (Wayland).

## Primer inicio y captura original

El wrapper de sesión ejecuta el administrador de perfiles ANTES de iniciar startplasma-wayland. En el primer ingreso guarda un snapshot de la configuración actual de Plasma. Si elegís Rice, conserva Original, carga una copia inicial y, una sola vez, reemplaza sus paneles por una barra superior, dock inferior y Breeze Dark.

Si cambiás temas, atajos o paneles en Rice, al cerrar sesión y entrar a Original se guardan sus cambios y se restauran los archivos del perfil Original. Al volver a Rice, recupera su apariencia anterior.

Se conmutan solamente estos archivos en ~/.config:

- kwinrc
- kdeglobals
- kglobalshortcutsrc
- plasmarc
- plasmashellrc
- plasma-org.kde.plasma.desktop-appletsrc

No se manipulan KScreen, PowerDevil, claves de acceso, documentos, navegador ni archivos fuera de esa lista.

## Precauciones y recuperación

Cerrá completamente una sesión antes de entrar a la otra. No uses Cambiar de usuario para abrir dos Plasma simultáneos. El gestor detecta procesos plasmashell y kwin_wayland y bloquea el cambio si detecta otra sesión activa.

Si el perfil Rice falla, elegí Plasma Original (Wayland) desde SDDM. Alternativamente, desde una TTY con tu cuenta habitual y sin procesos Plasma activos:

    python3 /usr/local/libexec/munhof-plasma-rice-profilectl status
    python3 /usr/local/libexec/munhof-plasma-rice-profilectl restore-original

Los snapshots se mantienen en ~/.local/state/munhof-kde-ricing/profiles/ y utilizan almacenamiento por versiones. Hay un marcador de transacción pendiente para recuperar cambios interrumpidos.

Desinstalar las entradas (restaurar Original antes de hacerlo):

    sudo python3 scripts/session/install_profiles.py --user munhof --uninstall

Los snapshots no se eliminan automáticamente.

## Recuperación por otra cuenta opcional

El instalador scripts/session/install.py permite una sesión separada de recuperación con la cuenta kde-rice. No es requerida para usar los dos perfiles de munhof. Consultar isolated-session.md.

## Limitaciones

El preset inicial no reproduce todavía exactamente los detalles de Waybar/Wofi/Wlogout, fondos, tipografía y transparencias de la referencia de Reddit. Utiliza paneles Plasma nativos, KWin y Breeze Dark.

La gestión de múltiples monitores continúa a cargo de KDE/KScreen; la generación inicial de paneles Rice no distribuye todavía barras por cada monitor.

Las pruebas unitarias no sustituyen una prueba de login real en Plasma 6.8.2.

Fuentes técnicas:
https://wiki.archlinux.org/title/KDE
https://develop.kde.org/docs/plasma/scripting/
https://develop.kde.org/docs/plasma/scripting/api/
