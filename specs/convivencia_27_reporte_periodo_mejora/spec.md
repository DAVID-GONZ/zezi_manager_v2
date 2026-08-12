# convivencia_27_reporte_periodo_mejora — Spec

## Contexto

`/convivencia/reporte-periodo` "no lista nada". Causa raíz: la página usa el
selector 3D `inline_periodo_grupo_asignatura`, que solo dispara `on_change(s)`
cuando se selecciona **asignatura**. Pero el reporte es por **grupo + periodo**
(`ConvivenciaService.reporte_periodo_grupo(grupo, periodo)` no usa asignatura). Si
el usuario no elige asignatura —o es coordinador/director que no dicta en ese grupo
y por tanto no tiene asignaturas ahí, dejando el pill vacío— `on_change` nunca
dispara y el reporte no carga. Además, aunque cargue, es solo una grilla sin resumen.

Scope: `src/interface/pages/convivencia/reporte_periodo.py` (MODIFICAR).

## Requisitos (EARS)

- **R1** — El reporte DEBE cargarse al seleccionar periodo + grupo, SIN requerir asignatura.
- **R2** — El reporte DEBE mostrar un resumen (KPIs) del grupo/periodo: nº de
  estudiantes, nº con nota, promedio de nota de comportamiento, nº con alerta, y
  total de observaciones.
- **R3** — DEBE conservar la grilla por estudiante (nota, nivel, concepto, # obs,
  observaciones) y la exportación PDF/Excel existentes.
- **R4** — Se conserva la autorización por objeto (director de grupo/coord/dir);
  para profesor, el selector solo ofrece sus grupos.

## Diseño

### Selector 2D (fix R1)
- Reemplazar `inline_periodo_grupo_asignatura(...)` por
  `inline_periodo_grupo(_s, on_sel_change, institucion_id=ctx.institucion_id,
  usuario_id=ctx.usuario_id, usuario_rol=ctx.usuario_rol, preselect_periodo=True)`.
- `on_sel_change` deja de leer/usar asignatura; sigue fijando `grupo_id`, `periodo_id`,
  `sel_grupo_nombre`, `sel_periodo_nombre` y llamando `_cargar_reporte` + refresh.

### Resumen KPIs (R2) — reutiliza servicio + componente ya existentes
- Nuevo helper `_cargar_kpis(_s)` que llama
  `Container.convivencia_service().resumen_convivencia_grupo(grupo_id, periodo_id)`
  (lista de `ResumenConvivenciaDTO`) y agrega:
  - `estudiantes = len(resumen)`
  - `con_nota = sum(1 for r in resumen if r.nota is not None)`
  - `promedio = round(mean(notas), 1)` sobre notas no None (o "—" si ninguna)
  - `con_alerta = sum(1 for r in resumen if r.supera_umbral)`
  - `total_obs = sum(r.num_observaciones for r in resumen)`
- Render de una fila `form-row-inline` con `counter_card(...)` por KPI
  (importar `counter_card` desde `src.interface.design.components`). El de "Con alerta"
  usa `variante="danger", alerta=True` si `con_alerta > 0`.
- Se muestra solo cuando hay grupo+periodo y el usuario está autorizado, encima de la grilla.

### Conservar
- `reporte_periodo_grupo` (grilla), `exportar_reporte_periodo_grupo` (PDF/Excel),
  `_autorizado_para_grupo`, `_filas_grilla`, `_COL_DEFS`, `_slug_descarga`.

## Tareas
- **T1** — Cambiar a `inline_periodo_grupo` (2D) y ajustar `on_sel_change`.
- **T2** — `_cargar_kpis` + render de `counter_card` sobre `resumen_convivencia_grupo`.
- **T3** — Verificación.

## Verificación
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/convivencia/reporte_periodo.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer interface
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py   (lo corre el leader)
```
El reporte carga al elegir periodo+grupo; muestra KPIs + grilla + export; init.py verde.
