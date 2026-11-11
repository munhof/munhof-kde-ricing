# v0.7 experimental: islas reales con Quickshell

Este es un **prototipo optativo**, pensado para corregir la captura de Plasma Rice con barras de Waybar de ancho completo. No reemplaza automáticamente Waybar, Wofi, Polonium ni las sesiones SDDM. La versión es para probar **tamaño, superficies reales y hotplug**, no para considerarla aún lista para uso diario.

## Por qué cambiar la capa visual

Waybar puede mostrar píldoras flotantes con CSS, pero su superficie real sigue los límites de cada instancia de barra. La v0.6.1 probó que alternar `exclusive` no resuelve la interferencia entre KWin y Polonium: la zona exclusiva cambia el área de trabajo y el modo no exclusivo permite que las ventanas se extiendan detrás de la barra.

Quickshell usa paneles de QML individuales cuyo tamaño se calcula desde sus componentes. El prototipo crea, en cada monitor conectado:

- Isla superior izquierda: lanzador y etiqueta Rice.
- Isla superior central: etiqueta KDE/Wayland.
- Isla superior derecha: búsqueda y reloj funcional.
- Dock inferior: lanzadores con superficie de tamaño contenido.

No se fija ninguna salida concreta; `Variants { model: Quickshell.screens }` crea y destruye las superficies al conectar o desconectar pantallas. Se mantienen `ExclusionMode.Ignore`, de modo que la capa visual **no solicita cambiar el área de mosaicos**. Las islas pueden superponerse a ventanas que lleguen hasta el borde; es una limitación explícita del prototipo y no una solución definitiva al workarea.

## Probar, sin instalar ni eliminar paneles

En Garuda, una sola vez:

```fish
sudo pacman -S --needed quickshell
```

Dentro de **Plasma Rice (Wayland)** y sin usar `sudo`:

```fish
cd ~/Escritorio/proyectos/munhof-kde-ricing
git pull --ff-only origin main

# Detener solamente la Waybar del proyecto:
~/.local/bin/munhof-rice-appearance stop

# Ejecutar las islas de forma temporal:
quickshell --path "$PWD/appearance/quickshell/shell.qml"
```

Cerrá la prueba con **Ctrl+C** en la misma terminal. Para regresar a Waybar:

```fish
~/.local/bin/munhof-rice-appearance start
```

Si Waybar tiene autostart habilitado, deshabilitalo **únicamente si decidís usar Quickshell más adelante**; de momento no se altera nada en el autostart ni en los paneles KDE.

## Qué probar

1. Abrí tres ventanas: verificá que Polonium distribuya correctamente cuando Quickshell esté activo.
2. Comprobá que el dock inferior no ocupe toda la pantalla a efectos del mouse; su superficie debe tener el ancho de sus botones.
3. Conectá/desconectá la segunda pantalla y comprobá que reaparezcan cuatro islas por monitor.
4. Confirmá que el buscador, reloj, terminal y Dolphin respondan.
5. Si ves ventanas por debajo de las islas, documentá la región: **el siguiente módulo debe sincronizar los gaps/áreas de trabajo de Polonium y KWin**, no volver a activar `exclusive=true`.

No hay inicio automático, migración de paneles ni reemplazo de la barra en esta etapa. Las pruebas de CI solo verifican el diseño declarativo; QML y KWin deben probarse en la sesión real de Plasma 6.8.2.

## Limitaciones reales

- No implementa todavía un gestor de ventanas abiertas, notificaciones, escritorios dinámicos ni menú de energía.
- La etiqueta Rice es estática; el reloj sí se actualiza.
- Al no reservar workarea, puede haber superposición local con ventanas. **No se promete adaptación automática de Polonium** hasta disponer de una integración KWin validada.
- El proyecto continúa conservando el perfil Plasma Original por separado.

Fuentes:
- https://quickshell.org/docs/v0.3.2/types/Quickshell/PanelWindow/
- https://quickshell.org/docs/v0.3.2/types/Quickshell/Quickshell/
- https://archlinux.org/packages/extra/x86_64/quickshell/
