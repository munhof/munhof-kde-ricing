# Roadmap — enfoque Plasma nativo

## Completado

- [x] v0.1: motor declarativo, CLI, doctor, plan, apply, rollback y pruebas.
- [x] v0.2: captura de configuración KWin/Polonium y manifests reversibles.
- [x] v0.3: inspección y gestión optativa de nuevos paneles Plasma.
- [x] v0.4: dos perfiles Plasma Wayland para el mismo usuario, respaldos y recuperación.
- [x] v0.8: retiro del prototipo Waybar/Quickshell de la configuración activa, limpieza de autostart, guía nativa para dos monitores.

## Siguiente trabajo

- [ ] Validar paneles superiores y docks nativos sobre KDE Plasma 6.8.2 en ambas pantallas.
- [ ] Hacer un preset nativo de Plasma que respete siempre Polonium, sin capas externas.
- [ ] Crear un tema Plasma propio inspirado en el rice de referencia: paneles translúcidos, acentos violetas y bordes.
- [ ] Implementar exportación y restauración per-monitor de paneles usando la API oficial, sin IDs de pantalla fijos.
- [ ] Probar perfiles de densidad laptop/escritorio/tableta sin modificar KScreen ni PowerDevil.
- [ ] Añadir regresiones visuales y pruebas de inicio de sesión en un KDE real.

## Requisitos de aceptación

1. Ningún panel externo (Waybar/Quickshell) debe iniciarse automáticamente.
2. Polonium debe distribuir exactamente las aplicaciones abiertas, sin superficies externas contadas.
3. Debe haber barra y dock nativos en cada monitor configurado.
4. Plasma Original debe mantener sus paneles y colores tras alternar sesiones.
5. Toda operación automatizada de escritura debe tener plan previo, alcance explícito y recuperación.
