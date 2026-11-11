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

## v0.7.1 — Diagnóstico de Polonium y clases de superficies

**Problema confirmado por observación del usuario:** con Quickshell, el motor distribuye ventanas en subdivisiones propias de un sexto/octavo cliente; sin Quickshell, Polonium vuelve a dividir las aplicaciones normalmente. La causa probable es que las superficies de Quickshell están entrando al contador de ventanas de KWin/Polonium. No hay todavía un registro real de KWin que confirme su clase.

Este parche etiqueta explícitamente cada isla Wayland con el namespace `munhof-rice-island` mediante `WlrLayershell.namespace`. También fija `WlrLayer.Top` y dimensiones QML contenidas, sin cambiar `ExclusionMode.Ignore`. El namespace es una etiqueta para diagnóstico y posibles reglas; **por sí solo no excluye las superficies de Polonium**.

### Verificar qué clase ve KWin

Desde **Plasma Rice**, primero asegurate de no tener instancias duplicadas:

```fish
pgrep -af quickshell
```

Si hay varias, terminá las pruebas anteriores desde sus terminales (Ctrl+C), evitando matar instancias de otros proyectos.

Con **una sola** Quickshell activa, ejecutá:

```fish
qdbus6 org.kde.KWin /KWin org.kde.KWin.queryWindowInfo
```

Hacé clic sobre la isla del dock o una cápsula superior. Inspeccioná `resourceClass`, `resourceName`, `dock` y `normalWindow` si aparecen.

Si **KWin informa una clase de ventana propia de Quickshell**, podés añadirla a las exclusiones sin cambiar ninguna otra:

1. Configuración del sistema → Gestión de ventanas → Guiones de KWin → **Polonium**, engranaje.
2. Pestaña **Filters** → **Ignore Window Classes**.
3. Conservá el contenido existente y **añadí la clase real** detectada en `resourceClass`, separada por coma (por ejemplo `quickshell`, o `munhof-rice-island` **solo si KWin la reportó**).
4. Aplicá y **cerrá sesión / iniciá sesión** en Plasma Rice para que Polonium relea los filtros. El proyecto Polonium indica que sus cambios de configuración requieren reiniciar KWin.
5. Con tres aplicaciones abiertas, comprobá que se generen exactamente tres mosaicos de aplicaciones, sin contar las islas, y probá el monitor externo.

Es importante usar **Ignore Window Classes** y no *Untile Window Classes*: esta última mantiene ventanas fuera del mosaico pero puede seguir gestionándolas en el motor, según la versión de Polonium. La configuración moderna de Polonium ofrece ambas opciones.

Si KWin no permite seleccionar las islas y no las presenta como ventanas normales, no agregues clases al filtro. La causa puede ser otra (mosaicos guardados, otro proceso de shell o un conflicto entre superficies de Layer Shell y el trabajo de KWin). Recopilá logs con:

```fish
journalctl --user --no-pager -g '[Pp]olonium' -n 80
```

### Sobre el espacio que ocupa cada isla

Quickshell ahora fija `implicitWidth` a la suma del ancho real de los botones más 24 px y `implicitHeight` a 42 px arriba / 58 px abajo. Ninguna cápsula ancla ambos extremos horizontales. Esto corrige la geometría de sus propias superficies, pero **no resuelve que las aplicaciones queden debajo de las islas**.

No vamos a intentar recuperar el área de trabajo activando `exclusiveZone` a ciegas: hay que coordinar el tiling de Polonium y las áreas reservadas por monitor, sin imponerle a KWin un área rectangular equivocada. Esa integración sigue pendiente.

Fuentes:
- https://quickshell.org/docs/v0.3.1/types/Quickshell.Wayland/WlrLayershell/
- https://zeroxoneafour.github.io/polonium/usage.html
- https://github.com/zeroxoneafour/polonium/blob/master/res/config.ui
- https://develop.kde.org/docs/plasma/kwin/api/
