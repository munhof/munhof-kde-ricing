# v0.5 — Apariencia Waybar + Wofi en ambos monitores

La v0.4 instaló dos perfiles Wayland para un mismo usuario. La v0.5 añade un primer **rice visual real**, aislado mediante una comprobación del perfil seleccionado.

## Qué reproduce del mock

- Barra oscura superior, sutilmente translúcida, con menús, escritorios, audio, red, batería y reloj **en todas las pantallas**.
- Dock inferior centrado **en todas las pantallas** con lanzadores de aplicaciones.
- Lanzador de aplicaciones oscuro, centrado, mediante Wofi.
- JetBrainsMono Nerd Font, acentos violetas y gris azul oscuro.
- Polonium sigue administrando las ventanas y la separación desde KWin.

**Limitaciones:** el dock v0.5 son lanzadores, no un task manager con indicadores de ventanas abiertas. Wofi usa una lista de aplicaciones, **no el grid con categorías mostrado en el mock**. El fondo de pantalla tampoco se cambia automáticamente. El aspecto exacto de la referencia exige un launcher personalizado (p. ej. QML/Quickshell), integración de tareas KWin y configuración de temas/ventanas adicional.

## Instalar dependencias en Garuda

En tu sesión KDE normal podés instalar las aplicaciones sin modificar aún el escritorio:

```fish
sudo pacman -S --needed waybar wofi ttf-jetbrains-mono-nerd pavucontrol
```

Polonium ya existe en tu usuario. La configuración de Polonium y los componentes KWin permanecen independientes por perfil.

## Primer ensayo seguro

1. Entrá en SDDM con el mismo usuario pero seleccionando **Plasma Rice (Wayland)**.
2. Desde el repositorio actualizado ejecutá:

```fish
cd ~/Escritorio/proyectos/munhof-kde-ricing
python3 scripts/appearance/appearancectl.py doctor
python3 scripts/appearance/appearancectl.py install
~/.local/bin/munhof-rice-appearance start
~/.local/bin/munhof-rice-appearance launcher
```

Las dos barras Waybar se muestran, por diseño, en **ambos monitores**: no se fija una salida concreta en el JSON. En esta fase puede haber superposición con barras de Plasma: todavía **no se ha borrado ninguna**.

3. Verificá barras, reloj, red, dock, acceso al lanzador y comportamiento multimonitor.
4. Si algo falla, ejecutá `~/.local/bin/munhof-rice-appearance stop` (solo detiene el Waybar del proyecto). Mirá los logs en `~/.local/state/munhof-kde-ricing/appearance/waybar.log`.

## Activación en cada inicio del perfil Rice

Una vez comprobado visualmente que Waybar funciona:

```fish
~/.local/bin/munhof-rice-appearance enable-autostart
```

La entrada XDG de autostart se instala en la cuenta actual pero su wrapper **solo inicia Waybar si el perfil gestionado activo es Rice**. En Original sale sin modificar nada.

## Reemplazar realmente las barras Plasma, SOLO en Rice

**No hagas esto hasta comprobar Waybar en ambos monitores y su arranque tras cerrar e iniciar sesión.**

```fish
~/.local/bin/munhof-rice-appearance replace-panels --confirm
```

Este comando guarda `~/.config/plasma-org.kde.plasma.desktop-appletsrc` bajo `~/.local/state/munhof-kde-ricing/appearance/plasma-panels-before-waybar.ini` **antes de eliminar** los paneles nativos de Plasma de la sesión Rice mediante su API oficial. No modifica directamente los paneles que están guardados en el snapshot del perfil Original. El escritorio sigue siendo Plasma/KWin; solo se retiran sus paneles.

Si Waybar deja de funcionar, entrá a Original desde SDDM (cuyos paneles y dock anteriores se restauran). Para restaurar también los paneles nativos del perfil Rice, tras **cerrar** Rice y mientras Rice siga siendo el perfil activo, podés restaurar el archivo de respaldo desde una TTY; no copies el archivo mientras `plasmashell` está funcionando.

**No ejecutes dos sesiones Plasma del mismo usuario en paralelo** ni uses la entrada estándar de Plasma de SDDM durante el test. La conmutación de archivos de los perfiles solo se hace desde las entradas gestionadas.

## Personalización

Archivos versionados en el repositorio:

```text
appearance/
├── waybar/
│   ├── config.jsonc      # barras superior e inferior, sin salida fija
│   └── style.css         # semitransparencias y acentos violetas
└── wofi/
    ├── config            # drun, posición y tamaño del launcher
    └── style.css
scripts/appearance/
└── appearancectl.py      # instalación, ejecución, log y rollback manual
```

Los archivos instalados se guardan bajo `~/.local/share/munhof-kde-ricing/appearance`, sin sobrescribir los `~/.config/waybar` o `~/.config/wofi` personales. Tras editar archivos del repositorio, ejecutá `python3 scripts/appearance/appearancectl.py install --update`, que respalda las versiones instaladas.

Para desactivar el inicio automático:

```fish
~/.local/bin/munhof-rice-appearance disable-autostart
~/.local/bin/munhof-rice-appearance stop
```

La siguiente versión debe incorporar un administrador real de ventanas abiertas al dock, un launcher de categorías en cuadrícula, un selector de wallpaper y bordes/decoraciones con compatibilidad comprobada en Plasma 6.8.

Fuentes:
- https://github.com/Alexays/Waybar
- https://github.com/Alexays/Waybar/blob/master/man/waybar.5.scd.in
- https://develop.kde.org/docs/plasma/scripting/
- https://github.com/zeroxoneafour/polonium

## v0.6 — Ajuste fino de la interfaz

Ahora hay tres escalas que modifican **de manera coordinada** el alto de la barra superior, la altura del dock, las dimensiones de los íconos y el tamaño del launcher.

| Perfil | Barra superior | Dock | Texto | Íconos | Separación |
| --- | ---: | ---: | ---: | ---: | ---: |
| compact | 34 px | 48 px | 12 px | 21 px | 7 px |
| balanced | 42 px | 60 px | 14 px | 27 px | 10 px |
| touch | 54 px | 76 px | 17 px | 36 px | 14 px |

En tu monitor de 16" 1920×1200 y el externo 1920×1080, empezá por **balanced**.

```fish
cd ~/Escritorio/proyectos/munhof-kde-ricing
git pull --ff-only origin main
python3 scripts/appearance/appearancectl.py install --update
~/.local/bin/munhof-rice-appearance tune --preset balanced  # simulación
~/.local/bin/munhof-rice-appearance tune --preset balanced --apply
~/.local/bin/munhof-rice-appearance restart
```

Si necesitás un ajuste más preciso:

```fish
~/.local/bin/munhof-rice-appearance tune --preset balanced --bar-height 44 --dock-height 64 --font-size 15 --icon-size 29 --edge-gap 12 --apply
~/.local/bin/munhof-rice-appearance restart
```

El comando genera `waybar/tuned-config.json`, `waybar/tuned-style.css`, `wofi/tuned-config` y `wofi/tuned-style.css` en los datos del proyecto. Los templates versionados permanecen intactos. `restart` reinicia únicamente la instancia de Waybar iniciada por el proyecto.

Se hace explícito `exclusive=true` para solicitar a KWin que reserve espacio para las barras en cada pantalla. **Polonium y KWin deben verificar esa reserva**; si quedan ventanas solapadas, capturá el estado y no elimines paneles Plasma todavía. No se modifican KScreen, zoom del sistema, PowerDevil ni el perfil Original. La futura compatibilidad con escala diferente por monitor todavía no está implementada.
