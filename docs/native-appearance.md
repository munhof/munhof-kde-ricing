# Rice nativo con el editor de KDE Plasma 6.8

## Objetivo

Recrear un escritorio oscuro, ordenado y minimalista inspirado en r/unixporn **sin Waybar, Wofi ni Quickshell**. Se mantienen **KWin Wayland**, **Polonium** y los componentes de Plasma, para evitar conflictos entre superficies externas y el algoritmo de mosaicos.

Esta guía está orientada al portátil 1920×1200 y monitor externo 1920×1080, ambos con KDE Plasma Wayland. Las dimensiones son propuestas visuales y pueden requerir pequeños ajustes en cada pantalla.

## 0. Retirar los prototipos externos

En Plasma Rice, desde el repositorio:

```fish
python3 scripts/native/retire_external.py
python3 scripts/native/retire_external.py --apply
pgrep -af quickshell
```

Cerrá Quickshell desde su terminal con Ctrl+C si sigue ejecutándose. Wofi no debería estar abierto; cerralo con Esc si quedó en pantalla.

No desinstales paquetes hasta comprobar que ningún otro proyecto los utiliza. Si querés desinstalarlos de Garuda más adelante, revisá primero la lista de paquetes que `pacman` propone quitar; esa decisión es externa al proyecto.

## 1. Comprobar en qué sesión estás

```fish
cat ~/.local/state/munhof-kde-ricing/profiles/state.json
uv run plasma-rice shell inspect
```

La primera salida debería indicar `"active": "rice"`. La segunda lista los paneles reales, sus pantallas y los widgets.

**No edites paneles desde Plasma Original.** El administrador de perfiles guarda los paneles de Rice al cerrar su sesión y entrar a Original; la configuración original debe permanecer independiente.

## 2. Panel superior: uno por monitor

En el escritorio correspondiente a cada pantalla:

1. Clic derecho en un área vacía → **Entrar en modo edición**.
2. Si no existe panel superior, elegí **Añadir panel → Panel vacío**.
3. Seleccioná el panel y configurá **Posición superior**, **Flotante**, **altura 38 px**, **longitud: llenar ancho disponible**, **alineación central**, **visibilidad: siempre visible** y **opacidad: adaptativa** (los nombres pueden variar con el idioma o el tema).
4. Añadí y ordená los widgets: **Lanzador de aplicaciones (Kickoff)**, **Paginador de escritorios virtuales**, **Espaciador**, **Bandeja del sistema**, **Reloj digital**.
5. Usá el propio panel para regular los espaciadores y el espacio entre bloques. Evitá incluir tareas abiertas en la barra si ya utilizás un dock inferior.

La barra nativa conoce su pantalla y la posición disponible, en lugar de crear una capa externa de ancho completo. El modo «Flotante» es un efecto nativo de Plasma, no una ventana que Polonium debería contar como aplicación.

## 3. Dock inferior: uno por monitor

1. En modo edición, **Añadir panel → Panel vacío** (si no existe un dock).
2. Ubicalo abajo, con **altura 54 px**, **longitud: ajustar al contenido**, **alineación central** y **Flotante**.
3. Elegí **Ocultar automáticamente** si querés maximizar el área útil. La alternativa **Esquivar ventanas** es útil cuando está disponible y funciona bien con tu modo de mosaicos.
4. Añadí **Administrador de tareas solo con iconos** y opcionalmente **Mostrar escritorio**.
5. Abrí las aplicaciones habituales y anclalas desde el menú contextual del administrador de tareas. Los iconos abiertos se añaden y retiran automáticamente: ese es el comportamiento que no teníamos con el dock estático de Waybar.

**Importante:** un dock de Plasma puede ajustar su longitud al contenido; no hace falta mantener un rectángulo transparente sobre toda la pantalla.

## 4. Colores, transparencias y ventanas

Desde **Configuración del sistema → Colores y temas**:

- **Estilo de Plasma:** Breeze Dark o un estilo oscuro compatible con Plasma 6.
- **Colores:** esquema oscuro con acento violeta. Elegí un violeta moderado para selección, indicadores y botones; evitá introducir contraste demasiado bajo.
- **Decoraciones de ventanas:** Breeze o una decoración compatible con KWin y bordes redondeados.
- **Iconos:** podés conservar Tela o los iconos de Garuda, si te gustan.
- **Fuentes:** Inter para interfaz, JetBrains Mono Nerd Font para código o terminal. No es obligatorio instalar nada nuevo si ya están disponibles.

Desde **Configuración del sistema → Comportamiento del espacio de trabajo → Efectos del escritorio**, comprobá el efecto **Desenfoque**. La transparencia depende también del estilo de Plasma; activar blur no vuelve transparentes las ventanas por sí solo.

Aplicá cada parte desde el editor nativo; **no apliques un tema global con la opción «reemplazar distribución del escritorio»** salvo que hayas respaldado la configuración.

## 5. Polonium y ventanas

Con los paneles de Plasma, probá el mosaico de dos y tres ventanas en el monitor principal y el externo.

- Mantené Polonium habilitado en **Guiones de KWin**.
- Empezá por 10 px de padding y aumentá/reducí la separación desde las opciones de Polonium o el editor de mosaicos de KDE.
- No agregues reglas de exclusión para Waybar/Quickshell si ya no están activos.
- Si al maximizar una ventana el panel deja de flotar temporalmente, es comportamiento previsto del modo flotante en Plasma, no necesariamente un error.

Si la geometría parece incorrecta, verificá primero que no haya **paneles duplicados** en el mismo borde con `uv run plasma-rice shell inspect` y que no queden procesos externos activos. No cambies toda la configuración de KWin a ciegas.

## 6. Segundo monitor y modo tableta

Configurá la barra superior y el dock **desde el monitor correspondiente**. La API de scripting de Plasma permite gestionar paneles, pero asignar un panel concreto a una pantalla no está totalmente validado en la automatización actual; la interfaz de edición nativa es el método recomendado.

No toques `~/.local/share/kscreen`, `powerdevilrc`, rotación automática ni escala global. Estas preferencias son compartidas entre los dos perfiles y podrían alterar Plasma Original.

Para modo tableta, probá manualmente una altura de 46–50 px arriba y 64–70 px abajo; luego restaurá valores de escritorio si no te sirven. Más adelante podremos generar perfiles de densidad nativos, pero no los aplicamos automáticamente todavía.

## 7. Verificación y recuperación

```fish
uv run plasma-rice shell inspect
uv run plasma-rice doctor
```

Una vez conforme, cerrá sesión, seleccioná **Plasma Original (Wayland)** y verificá que conserve su distribución anterior. Al volver a **Plasma Rice (Wayland)**, deberán reaparecer las modificaciones nativas de Rice.

Si antes ejecutaste `replace-panels --confirm` y faltan paneles, **crealos nuevamente desde el editor de Plasma**. El prototipo antiguo guardaba un respaldo en `~/.local/state/munhof-kde-ricing/appearance/plasma-panels-before-waybar.ini`, pero **no recomendamos copiar ese archivo sobre el archivo activo de Plasma mientras `plasmashell` está en ejecución**.

## Límite visual

Plasma permite barras flotantes, tamaño ajustado al contenido, iconos de tareas y opacidad adaptable. La publicación de referencia utiliza módulos altamente estilizados que no se pueden recrear exactamente desde el editor estándar sin diseñar un **tema Plasma propio** o plasmoides adicionales. Ese tema será la siguiente etapa del repositorio, no otra capa Wayland.

Fuentes de referencia:
- https://develop.kde.org/docs/plasma/scripting/api/
- https://docs.kde.org/stable_kf6/en/plasma-workspace/kcontrol/lookandfeel/
- https://develop.kde.org/docs/plasma/theme/theme-porting-to-plasma6/
