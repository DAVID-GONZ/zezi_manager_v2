# Spec — revision2_planilla_notas

## Módulo: Planilla de Notas — Revisión 2
**Versión:** 1.0 — 2026-05-21  
**Tipo:** Corrección de bugs bloqueantes (la planilla sigue sin renderizar)  
**Notación:** EARS

---

## Diagnóstico

### Bug #1 (CRÍTICO) — Coordinadores y directores nunca ven la planilla

```
layout.py:268
  context_chip(ctx=ctx, mostrar_asignatura=(usuario_rol == "profesor"))
    → Solo profesores reciben el selector de asignación en el topbar

planilla_notas.py:490-496
  if not ctx.asignacion_id or not ctx.periodo_id:
      return   ← early return — el panel de planilla NUNCA se renderiza
```

**Causa raíz:** `context_chip` expone el selector de asignatura únicamente al rol `"profesor"`.
Para coordinadores y directores, `ctx.asignacion_id` siempre es `None` al cargar la página,
por lo que el `contenido()` hace `return` antes de renderizar el ag-Grid.

**Fix:** Reemplazar el early-return por selectores en la propia página, pre-poblados desde ctx.
Los selectores deben existir siempre (no solo cuando ctx incompleto) para que cualquier rol
pueda cambiar de asignación/periodo sin tener que usar el topbar.

---

### Bug #2 (CRÍTICO) — `listar_resultados_grupo` recibe los argumentos equivocados

```python
# evaluacion_service.py:334 — llamada actual (INCORRECTA)
resultados = self._repo.listar_resultados_grupo(asignacion_id, periodo_id)
#                                                ^^^^^^^^^^^^^  ^^^^^^^^^^
#                                                arg1=grupo_id  arg2=asignacion_id → arg3 FALTANTE

# evaluacion_repo.py:291-295 — firma del puerto
def listar_resultados_grupo(self, grupo_id: int, asignacion_id: int, periodo_id: int)

# sqlite_evaluacion_repo.py:455 — la SQL usa grupo_id para filtrar estudiantes
WHERE grupo_id = ? AND estado_matricula = 'activo'
```

**Consecuencia:**
- `grupo_id` recibe el valor de `asignacion_id` → SQL filtra con ID incorrecto → 0 estudiantes.
- `periodo_id` nunca se pasa → Python lanza `TypeError` swallowed en el `except Exception`.

**Fix:** Corregir la llamada en `EvaluacionService.obtener_planilla`:
```python
resultados = self._repo.listar_resultados_grupo(
    grupo_id, asignacion_id, periodo_id
)
```
El `grupo_id` debe provenir del contexto. `obtener_planilla` debe recibirlo como argumento.

---

### Bug #3 (MENOR) — `_periodo_abierto()` devuelve `False` cuando el periodo no está en la lista

```python
# planilla_notas.py:230
return False  # ← si periodo_id no está en _s["periodos"], edición bloqueada
```

Si `_cargar_estado()` no encontró una config activa, `_s["periodos"] = []`. Entonces
`_periodo_abierto()` siempre retorna `False` → banner "CERRADO" aunque el periodo esté abierto.

**Fix:** Cambiar el default de `False` a `True` en la última línea: si no se puede determinar
el estado, asumir abierto (el servicio ya valida al intentar guardar).

---

### Bug #4 (MENOR) — `obtener_planilla` llamada con `ctx=None`

```python
# planilla_notas.py:105-107
_s["planilla"] = Container.evaluacion_service().obtener_planilla(
    asig_id, per_id, ctx=None
)
```

`ctx` no se usa en el cuerpo del método actualmente, pero es inconsistente.
Con el fix del Bug #2, `grupo_id` debe pasarse explícitamente, así que `ctx=None` queda obsoleto.

---

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/services/evaluacion_service.py` | Corregir firma y llamada de `obtener_planilla`: agregar `grupo_id`, pasar los 3 args a `listar_resultados_grupo` |
| `src/interface/pages/evaluacion/planilla_notas.py` | Reemplazar early-return por selectores en página; pasar `grupo_id` a `_cargar_datos_asignacion`; corregir `_periodo_abierto` default |

---

## Requisitos funcionales

### R1 — Corregir `EvaluacionService.obtener_planilla`

**R1.1** La firma debe incluir `grupo_id`:

```python
def obtener_planilla(
    self,
    grupo_id: int,
    asignacion_id: int,
    periodo_id: int,
) -> list[ResultadoEstudianteDTO]:
```

**R1.2** La llamada al repositorio debe pasar los 3 argumentos en el orden correcto:

```python
resultados = self._repo.listar_resultados_grupo(grupo_id, asignacion_id, periodo_id)
```

**R1.3** Eliminar el parámetro `ctx` de la firma (no se usa en el cuerpo y genera confusión).
Si `ctx` existe en otros call-sites, actualizar todos ellos.

---

### R2 — Selectores en página (reemplazar early-return)

**R2.1** Eliminar el bloque early-return de `contenido()` (líneas 490-496 actuales):

```python
# ELIMINAR esto:
if not ctx.asignacion_id or not ctx.periodo_id:
    with ui.element("div").classes("tablero-empty mt-4"):
        ...
    return
```

**R2.2** Agregar al estado `_s` los campos para las opciones de los selectores:

```python
_s: dict = {
    "asignacion_id":    ctx.asignacion_id,
    "periodo_id":       ctx.periodo_id,
    "grupo_id":         ctx.grupo_id,
    "asignaciones":     [],   # NUEVO: list[Asignacion] para el selector
    "periodos":         [],
    ...
}
```

**R2.3** Agregar `_cargar_asignaciones()` que cargue las asignaciones del grupo:

```python
def _cargar_asignaciones() -> None:
    grupo_id = _s["grupo_id"]
    if not grupo_id:
        _s["asignaciones"] = []
        return
    try:
        _s["asignaciones"] = Container.asignacion_service().listar_por_grupo(grupo_id)
    except Exception as exc:
        logger.error("Error cargando asignaciones: %s", exc)
        _s["asignaciones"] = []
```

> Verificar que `AsignacionService` tiene `listar_por_grupo(grupo_id)` o método equivalente.
> Si el método no existe con ese nombre exacto, usar el método disponible con filtro de grupo.

**R2.4** Agregar un `@ui.refreshable` `filtros_refreshable()` al inicio de `contenido()` que
muestre los dos selectores en fila:

```python
@ui.refreshable
def filtros_refreshable() -> None:
    with ui.element("div").classes("panel-card mb-4"):
        ui.label("Contexto de evaluación").classes("text-sm font-semibold mb-3")
        with ui.row().classes("gap-3 items-end flex-wrap"):
            # Selector de periodo
            per_opts = {p.id: getattr(p, "nombre", str(p.id)) for p in _s["periodos"]}
            ui.select(
                label="Periodo",
                options=per_opts or {None: "Sin periodos"},
                value=_s["periodo_id"],
                on_change=lambda e: on_periodo_change(e.value),
            ).classes("w-44")

            # Selector de asignación
            asig_opts = {
                a.id: getattr(a, "nombre_asignatura", str(a.id))
                for a in _s["asignaciones"]
            }
            ui.select(
                label="Asignación",
                options=asig_opts or {None: "Sin asignaciones"},
                value=_s["asignacion_id"],
                on_change=lambda e: on_asignacion_change(e.value),
            ).classes("w-56")
```

> `nombre_asignatura` es el atributo de Asignacion que muestra el nombre. Verificar el modelo
> en `src/domain/models/asignacion.py` y usar el atributo correcto.

**R2.5** Los handlers de cambio recargan datos y refrescan la sección de planilla:

```python
def on_periodo_change(per_id) -> None:
    _s["periodo_id"] = per_id
    _cargar_datos_asignacion()
    filtros_refreshable.refresh()
    vista_planilla.refresh()
    contenido_actividades.refresh()

def on_asignacion_change(asig_id) -> None:
    _s["asignacion_id"] = asig_id
    _cargar_datos_asignacion()
    filtros_refreshable.refresh()
    vista_planilla.refresh()
    contenido_actividades.refresh()
```

**R2.6** Mantener el chip informativo de contexto solo cuando AMBOS están seleccionados.
Si alguno falta, mostrar un mensaje inline dentro del panel de planilla (NO early-return):

```python
# En vista_planilla():
if not _s["asignacion_id"] or not _s["periodo_id"]:
    with ui.element("div").classes("tablero-empty"):
        ui.icon("tune").classes("text-grey-5 text-3xl mb-2")
        ui.label("Selecciona un periodo y asignación arriba para ver la planilla.").classes(
            "tablero-empty-hint"
        )
    return
```

---

### R3 — Pasar `grupo_id` en `_cargar_datos_asignacion`

**R3.1** La llamada a `obtener_planilla` debe incluir `grupo_id`:

```python
_s["planilla"] = Container.evaluacion_service().obtener_planilla(
    _s["grupo_id"], asig_id, per_id
)
```

---

### R4 — Corregir `_periodo_abierto()` default

**R4.1** La última línea de `_periodo_abierto()` debe retornar `True` en lugar de `False`:

```python
def _periodo_abierto() -> bool:
    per_id = _s["periodo_id"]
    if not per_id:
        return False
    for p in _s["periodos"]:
        if p.id == per_id:
            estado = getattr(p, "estado", None)
            if estado is None:
                return True
            estado_val = estado.value if hasattr(estado, "value") else str(estado)
            return estado_val not in ("cerrado", "closed")
    return True  # ← si el periodo no está en la lista, asumir abierto
```

---

### R5 — Inicialización de datos

**R5.1** Al inicio de la función de página, llamar `_cargar_asignaciones()` además de los
cargadores existentes:

```python
_cargar_estado()
_cargar_asignaciones()
_cargar_datos_asignacion()
```

---

## Verificación

1. **Coordinador sin topbar asignatura**: Acceder a `/evaluacion/planilla` con rol coordinador.
   Deben aparecer los selectores de periodo y asignación en la parte superior.
   Al seleccionar ambos, la planilla debe cargar con datos.

2. **Profesor con contexto del topbar**: Acceder con rol profesor y asignatura ya seleccionada
   en el topbar. Los selectores deben mostrar los valores del ctx pre-seleccionados.
   La planilla debe cargar automáticamente (sin acción adicional).

3. **Verificar que las notas se guardan**: Editar una celda del ag-Grid. El notify
   "Nota X guardada" debe aparecer. Recargar la página — la nota debe persistir.

4. **Periodo cerrado**: Con un periodo cerrado, el banner amarillo debe aparecer y las
   celdas deben ser no editables.

5. `pytest -x -q` sin regresiones.

---

## Tests de aceptación

**T1** `pytest -x -q` pasa sin errores (≥607 tests).

**T2** `EvaluacionService.obtener_planilla(grupo_id=1, asignacion_id=1, periodo_id=1)`
llama a `listar_resultados_grupo(1, 1, 1)` — verificable en test unitario con FakeRepo.

**T3** Con `_s["periodos"] = []` y `_s["periodo_id"] = 5`, `_periodo_abierto()` retorna `True`.

**T4** La página `/evaluacion/planilla` carga sin errores con `ctx.asignacion_id = None`
(i.e., coordinador sin asignatura en topbar) — sin early-return, muestra selectores.

---

*Spec listo. Paso: `revision2_planilla_notas`.*
