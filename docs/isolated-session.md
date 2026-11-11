# Recuperación opcional con cuenta independiente

El modo principal utiliza dos perfiles en la cuenta munhof. Esta es una alternativa para iniciar KDE con otro usuario si el perfil habitual no funciona.

Crear la cuenta de manera explícita (solo si no existe):

    sudo useradd -m -s /bin/bash kde-rice
    sudo passwd kde-rice

Dentro del repositorio, realizar la vista previa:

    python3 scripts/session/install.py --user kde-rice

Instalar la sesión opcional en SDDM:

    sudo python3 scripts/session/install.py --user kde-rice --apply

En SDDM seleccionar el usuario kde-rice y Plasma Rice Recovery (Wayland). Esta cuenta tiene un HOME completamente independiente del usuario munhof.

Esta instalación no se ejecuta al crear los dos perfiles principales. El instalador de recuperación no crea ni borra cuentas automáticamente, ni activa autologin.

Para quitar la entrada de recuperación después de cerrar sesión:

    sudo rm /usr/share/wayland-sessions/munhof-plasma-rice-recovery.desktop

No borrar la cuenta o su directorio home sin revisar los archivos. Para restaurar el entorno principal, es preferible entrar a Plasma Original (Wayland) o ejecutar profilectl restore-original desde una TTY sin Plasma activo.
