# convivencia_25_hub_seguimiento — Spec

## Contexto

`seguimiento.py` hoy es la página de Alertas + Vista 360° (solo dir/coord). Se
reescribe como el **hub de Seguimiento maestro-detalle**, abierto a todos los
profesores (`_AULA`) para sus grupos/asignaturas asignadas. Absorbe la
visualización que se retira de Observaciones (contadores + lista gestionable) y de
Comportamiento (registros), añade la evolución de la nota de comportamiento, e
integra las Alertas + Vista 360° como sección solo para dir/coord.

Depende de: **convivencia_21** (métodos de servicio) y **convivencia_22**
(`counter_card`, `mini_chart`).

Scope: `src/interface/pages/convivencia/seguimiento.py` (SUSTITUIR).
Referencias de patrón: `src/interface/pages/inicio.py`,
`src/interface/pages/academico/registro_asistencia.py`, clases `page-body`,
`page-col-main`, `page-col-side` (ya en el layout).

## Requisitos (EARS)

- **R1** — Todo profesor DEBE poder visualizar el seguimiento de sus grupos y
  asignaturas asignadas (route `_AULA`; el selector ya scoping por rol/usuario).
- **R2** — El maestro DEBE mostrar, por estudiante del grupo/periodo:
  #observaciones, #registros negativos, nota, y un badge de alerta cuando
  `supera_umbral`. Datos vía `resumen_convivencia_grupo` (una sola llamada — sin N+1).
- **R3** — Al seleccionar un estudiante, el detalle DEBE mostrar: contadores
  (`counter_card`), la evolución de la nota (`mini_chart` con
  `serie_notas_comportamiento`), la lista de observaciones (con acciones de gestión
  gated), y la lista de registros de comportamiento.
- **R4** — La sección **Alertas + Vista 360°** DEBE renderizarse solo para
  director/coordinador (crear alerta, cargar 360°), migrada de la implementación actual.

## Diseño

### Estado `_s`
`sel_periodo_id`, `sel_grupo_id`, `estudiantes`, `resumen` (list[ResumenConvivenciaDTO]),
`sel_estudiante_id`, `serie` (list[PuntoSerieDTO]), `observaciones_est`,
`registros_est`, `resultado_360`, `docentes`, `alertas`.

### Estructura (refreshables hermanos, selector fuera)
- `inline_periodo_grupo(...)` arriba (fuera del refreshable), `preselect_periodo=True`.
- `on_sel_change`: carga estudiantes + `resumen_convivencia_grupo(grupo, periodo)`.
- **Maestro** (`page-col-main`): grid/lista de `resumen`. Cada fila: nombre,
  contadores (obs / registros neg / nota) y badge alerta (`supera_umbral`). Click →
  `on_estudiante_change(est_id)`.
- **Detalle** (`page-col-side`, al haber `sel_estudiante_id`):
  - Fila de `counter_card`: nota actual, #obs, #registros neg, estado alerta.
  - `mini_chart(labels, valores)` con `serie_notas_comportamiento(est, anio_id)`
    (`anio_id` del `configuracion_service.get_activa()`).
  - Lista de observaciones del estudiante (`listar_observaciones(est, periodo)`), con
    acciones de gestión **migradas de `observaciones.panel_obs_lista`**: toggle
    visibilidad; y para dir/coord: promover a plantilla, promover a comportamiento,
    eliminar. (Reusar `_toggle_visibilidad`, `_promover_a_plantilla`,
    `_promover_a_comportamiento`, `_eliminar_observacion`.)
  - Lista de registros del estudiante (`listar_registros(FiltroConvivenciaDTO(
    estudiante_id, periodo_id))`), presentados con badges por tipo (reusar
    `_TIPOS_DISPLAY`/`_CLASE_BADGE` de `comportamiento.py`).
  - **Sección Alertas + 360° (dir/coord):** botón "Nueva alerta"
    (`_abrir_crear_alerta`/`_enviar_alerta`) y "Cargar 360°" (`_ver_360`) con las
    `stat_card`/listas actuales. Migrar del `seguimiento.py` vigente.

### Servicios usados
`Container.convivencia_service()`: `resumen_convivencia_grupo`,
`serie_notas_comportamiento`, `listar_observaciones`, `listar_registros`,
`vista_360`, `crear_alerta_seguimiento_manual`, y las promociones/eliminación.
`Container.estudiante_service()`, `Container.configuracion_service()`,
`Container.usuario_service().listar_docentes()`, `Container.alerta_service()`.

### Alternativa descartada
Tabs en lugar de maestro-detalle. Descartada por decisión de David (maestro-detalle):
el drill-down por estudiante es la unidad natural de trabajo del docente.

## Tareas

- **T1** — Estado + selector + `on_sel_change` con `resumen_convivencia_grupo`.
- **T2** — Maestro: grid/lista de resumen con contadores + badge alerta + selección.
- **T3** — Detalle: `counter_card` + `mini_chart` (evolución).
- **T4** — Detalle: lista de observaciones con acciones de gestión gated (migradas).
- **T5** — Detalle: lista de registros de comportamiento con badges por tipo.
- **T6** — Sección Alertas + Vista 360° (dir/coord), migrada.

## Verificación
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/sync_tokens.py --check
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```
Maestro sin N+1 (una llamada a `resumen_convivencia_grupo` por grupo); detalle con
gráfica y contadores; sección alertas/360 solo dir/coord; check_design --all verde; init.py verde.
