# paso_14d_docente_view — design

## Archivo

`src/interface/pages/academico/horarios.py` — la página se bifurca por rol. Este
paso entrega la **rama docente**; la rama de gestión (admin/dir/coord) se aborda
en 14e. Para no romper esos roles entretanto, se conserva la grilla actual como
rama "gestión provisional" hasta 14e.

## Servicios usados (solo `Container.*`)

- `Container.infraestructura_service().get_escenario_activo(anio_id)` — escenario
  vigente.
- `...listar_horario_docente(usuario_id, periodo_id)` — bloques del docente
  (resuelve escenario activo internamente, paso_14a).
- `Container.asistencia_service().contar_clases_mes(usuario_id, anio, mes)` —
  conteo (paso_14c).
- `Container.configuracion_service().get_activa()` / `periodo_service` — año y
  periodo de referencia (ya presentes en la página).

## Estado `_s` (rama docente)

```python
_s = {
    "bloques":     [],          # HorarioInfo del docente
    "vista_grid":  "semana",    # "semana" | "dia"
    "dia_sel":     <hoy o lunes>,
    "mes_sel":     <mes actual>,
    "anio_cal":    <año calendario actual>,
    "clases_mes":  0,
    "usuario_id":  ctx.usuario_id,
    "periodo_id":  None,
    "anio_id":     None,
}
```

## Refreshables

- `grilla_refreshable()` — si `vista_grid == "semana"` reusa `_build_grilla`
  (día × hora). Si `"dia"`, filtra los bloques de `dia_sel` y los lista ordenados
  por `hora_inicio` como tarjetas. Si no hay bloques → `empty_state` (R7) sin CTA.
- `metricas_refreshable()` — `stat_card` con `clases_mes` (R4) y selector de mes
  (`ui.select` 1–12 + año) que actualiza `_s["mes_sel"]`/`_s["anio_cal"]`,
  recalcula `clases_mes` y refresca (R5).

## Handlers

- `_toggle_vista(valor)` → set `vista_grid`, refresh grilla.
- `_cambiar_dia(e)` → set `dia_sel`, refresh grilla.
- `_recalcular_mes()` → `clases_mes = asistencia_service.contar_clases_mes(...)`,
  refresh métricas.

## Componentes design system

`empty_state`, `stat_card`, `status_badge`, `btn_secondary`/`btn_icon` para la
alternancia. Sin `style=` estático ni `ui.button().props()` (R9). Toggle día/
semana con `ui.toggle` o dos `btn_secondary` con estado activo por clase CSS.

### Alternativa descartada

**Página nueva separada para el docente (`mi_horario.py`).** Descartada: duplica
ruta y navegación; el requisito es que `/horarios` se comporte distinto por rol.
La bifurcación por rol dentro de la misma página mantiene una sola entrada de
menú y un solo guard.

## Verificación

- `python scripts/check_design.py --file src/interface/pages/academico/horarios.py`
- `python init.py` exit 0; smoke como docente: grilla semana/día + tarjeta mes.
