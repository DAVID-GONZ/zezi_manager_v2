# paso_26 — Arreglar el render de la lista de usuarios en /admin/usuarios

## Contexto

La "tabla" de usuarios está hecha a mano con flex (`tabla()` en `src/interface/pages/admin/usuarios.py`, ~líneas 344-397) y tiene errores de render:

1. **Columnas desalineadas:** el encabezado asigna anchos (`Nombre flex-1`, `Usuario w-32`, `Rol w-28`, `Estado w-20`, `Acciones w-48`), pero en las filas de datos las celdas de **Rol** (`status_badge`) y **Estado** (`badge_estado_general`) se pintan **sin contenedor con ese ancho**, así que no cuadran con su cabecera y todo se desplaza.
2. **Falta columna "Institución":** el admin filtra por institución y ve usuarios de varias instituciones, pero la tabla no muestra a cuál pertenece cada usuario.
3. **Acciones apretadas:** hasta 4 `btn_icon` (ver como / cambiar rol / reset / desactivar) en un contenedor `w-48` → desbordan o se envuelven feo.

Alcance: SOLO la presentación de la lista en `usuarios.py`. No tocar servicios, RBAC, ni lógica de carga.

## Tareas

### T1 — Alinear columnas (header ↔ filas)
- Cada celda de datos debe ir envuelta en un contenedor con la **misma clase de ancho** que su encabezado (Rol → `w-28`, Estado → `w-20`, etc.), de modo que header y filas queden alineados. Hoy `status_badge(...)` y `badge_estado_general(...)` se insertan sueltos en el flex.
- Recomendado: evaluar usar el componente de tabla del design system (`data_table`, el mismo patrón de `src/interface/pages/admin/auditoria.py`) si da una alineación más robusta que el flex manual. Si se mantiene el flex, dejar las celdas correctamente envueltas y con `items-center`.

### T2 — Columna "Institución" (solo admin)
- Añadir una columna **Institución** al encabezado y a cada fila, visible **solo para admin** (el director ve una sola institución, no la necesita).
- Mostrar el **nombre** de la institución, no el id. El nombre se resuelve con el catálogo que la página ya carga (`instituciones_opts` / `_s["instituciones"]`): mapear `u.institucion_id → nombre` (fallback "—" si no resuelve). NO añadir métodos de servicio.
- Ajustar los anchos del resto de columnas para que la fila no se desborde.

### T3 — Acciones que no desbordan
- Dar a la columna de acciones un ancho suficiente para los hasta 4 botones (p.ej. ampliar el contenedor o usar `flex-nowrap` + `gap` adecuado) para que no se envuelvan ni recorten. Mantener alineación a la derecha.

### T4 — Verificación
- `python init.py` VERDE (baseline 1074 passed, 1 skipped). `python scripts/check_design.py --file src/interface/pages/admin/usuarios.py` exit 0; `check_imports --layer interface` exit 0.
- Revisar el `tabla()` completo por si hay otros desajustes evidentes (celdas sin ancho, badges sin envolver) y dejarlo consistente.
- `progress/impl_paso_26.md`.

## criterio_done
La lista de usuarios alinea header y filas; el admin ve una columna "Institución" con el nombre; los botones de acción no desbordan; sin cambios de servicios/lógica; `python init.py` verde y check_design/check_imports verdes.
