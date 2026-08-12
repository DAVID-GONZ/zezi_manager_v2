# convivencia_24_notas_limpieza — Spec

## Contexto

`notas_convivencia.py` gestiona correctamente las notas de comportamiento del
boletín (grid editable gated a director de curso; profesor no-director en solo
lectura). Pero además permite **crear observaciones**, duplicando el módulo
Observaciones, y muestra un `panel_obs_lista` de observaciones públicas cuya
visualización pertenece al hub de Seguimiento. Este paso deja Notas enfocada solo
en las notas de boletín.

Scope: `src/interface/pages/convivencia/notas_convivencia.py` (MODIFICAR).

## Requisitos (EARS)

- **R1** — La página DEBE gestionar únicamente notas de comportamiento (valor 0–100)
  y la observación de boletín por estudiante/periodo.
- **R2** — El director de curso (autorizado) edita; el profesor no-director ve el
  grid en solo lectura. (Comportamiento actual de `_autorizado_para_grupo` — se conserva.)
- **R3** — La página NO DEBE crear observaciones ni listar observaciones públicas.

## Diseño

**Conservar:** selector, `panel_grid` (grid editable de notas), `_autorizado_para_grupo`,
`_guardar_nota_estudiante`, `_guardar_seleccionado`, `_guardar_todo`,
`on_cell_value_changed`, banner de periodo cerrado y de no-autorizado.

**Eliminar:**
- Botón "Nueva observación" y handlers `_crear_observacion`, `_abrir_crear_observacion`.
- `panel_obs_lista` completo y su render.
- `_cargar_observaciones_publicas`, `_construir_filas_obs`, `on_categoria_change`,
  `_texto_truncado` (si deja de usarse), y las claves de estado `observaciones`/`sel_categoria_id`.
- La columna `# Obs.` del grid (dependía de `_cargar_observaciones_publicas`).
- Import de `NuevaObservacionDTO` (ya no se usa).
- `_actualizar_datos_en_sitio` se reduce a recargar notas y refrescar el grid.

**contenido():** deja de renderizar `panel_obs_lista`; `on_sel_change` deja de
cargar observaciones públicas.

## Tareas

- **T1** — Quitar el botón "Nueva observación" y sus handlers/imports.
- **T2** — Eliminar `panel_obs_lista` y los helpers de observaciones.
- **T3** — Quitar la columna `# Obs.` y la carga de observaciones públicas del estado.

## Verificación
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/convivencia/notas_convivencia.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```
Grid editable gated intacto; sin creación ni listado de observaciones;
check_design del archivo verde; init.py verde.
