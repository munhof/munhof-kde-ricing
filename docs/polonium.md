# Polonium sobre KDE Plasma 6.8

Este proyecto administra **solo ajustes globales explícitos** en `kwinrc`, preservando KScreen, PowerDevil, SDDM, pantalla táctil y rotación.

## Captura y reproducción

1. Activá Polonium en **Configuración del sistema → Gestión de ventanas → Guiones de KWin**.
2. Configurá la disposición a tu gusto en el engranaje del script.
3. Ejecutá `uv run plasma-rice capture --dry-run` para revisar las claves detectadas.
4. Ejecutá `uv run plasma-rice capture` para generar `components/tiling-captured/manifest.yaml`.
5. Verificá `uv run plasma-rice plan -c tiling-captured` antes de añadir el manifiesto a Git.
6. Para restaurarlo en otro equipo con Polonium instalado, ejecutá `plan -c tiling-captured`, luego `apply -c tiling-captured` (con snapshot previo).
7. Revertí con `rollback`, si no modificaste las claves desde la aplicación.

El comando evita sobrescribir archivos existentes. Los filtros de nombres de procesos y títulos se **excluyen por defecto**. Optar por incluirlos mediante `--include-filters` puede capturar datos privados.

**Alcance:** la captura no incluye atajos de teclado, disposiciones específicas de cada monitor, actividades ni los ajustes almacenados por Polonium Setting Saver. El proyecto necesita un adaptador separado para esos recursos.

## Primer preset estético

`minimal-tiling` aplica `Borders=1` en `[Script-polonium]`: según la interfaz de Polonium actual, oculta los bordes de las ventanas tiled, manteniendo bordes en las flotantes. Puede requerir cerrar y reiniciar sesión.

```bash
uv run plasma-rice plan -c minimal-tiling
uv run plasma-rice apply --dry-run -c minimal-tiling
# Aplicación explícita, luego de revisar:
uv run plasma-rice apply -c minimal-tiling
# Reversión si corresponde:
uv run plasma-rice rollback
```

**Precaución:** la opción `Borders` pertenece a Polonium y puede cambiar entre versiones; verificá el engranaje de Polonium antes de aplicarla. No se habilita ningún preset visual por defecto.

Referencias:
- https://github.com/zeroxoneafour/polonium
- https://zeroxoneafour.github.io/polonium/usage.html
- https://github.com/zeroxoneafour/polonium/blob/master/res/config.ui
