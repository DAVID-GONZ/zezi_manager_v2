# paso_14e_gestor_escenarios — design

## Archivo

`src/interface/pages/academico/horarios.py` — rama admin/director/coordinador.
Sustituye la "gestión provisional" dejada por 14d.

## Servicios usados (solo `Container.*`)

- `infraestructura_service`: `listar_escenarios`, `get_escenario_activo`,
  `crear_escenario`, `activar_escenario`, `renombrar_escenario`,
  `eliminar_escenario`, `duplicar_escenario`,
  `listar_horario_grupo_escenario`, `listar_horario_escenario`.
- `horario_service`: `crear_bloque`, `actualizar_bloque`, `eliminar_bloque`,
  `disponibilidad_asignacion`, `disponibilidad_docente`.
- `asignacion_service.listar_con_info(FiltroAsignacionesDTO(periodo_id=...))`.

## Estructura `_s`

```python
_s = {
    "escenarios":     [],        # EscenarioHorario del año
    "escenario_sel":  None,      # escenario en edición
    "grupo_id":       None,      # filtro de grilla
    "grupos":         [],
    "bloques":        [],        # del escenario_sel
    "asignaciones":   [],
    "periodo_id":     None,
    "anio_id":        None,
}
```

## Layout

1. **Panel de escenarios** (arriba): lista/`ui.select` de escenarios con
   `status_badge("Activo")` en el vigente; botones: Crear, Activar, Renombrar,
   Duplicar, Eliminar. Crear/Renombrar → `form_dialog`; Eliminar → `confirm_dialog`
   (danger, advierte arrastre de bloques); Activar/Duplicar → acción directa con
   `toast_*`.
2. **Panel de edición** (abajo): selector de grupo + grilla
   (`grilla_refreshable`) de `listar_horario_grupo_escenario(grupo, escenario_sel)`.
   Cada celda con bloque ofrece editar/eliminar; celdas vacías ofrecen crear.
3. **Indicador de cupo**: al abrir el `form_dialog` de bloque y elegir asignación,
   mostrar `disponibilidad_asignacion` y `disponibilidad_docente` (texto
   "Materia: 2/3 · Docente: 18/22").

## Refreshables

- `escenarios_refreshable()` — render del panel de escenarios.
- `grilla_refreshable()` — grilla del escenario/grupo; `empty_state` con CTA si
  vacío (R13).

## Handlers

- `_crear_escenario(datos)` → `crear_escenario`; refresca.
- `_activar_escenario(id)` → `activar_escenario`; `toast_success`; refresca.
- `_duplicar_escenario(id)` → `form_dialog` pide nombre → `duplicar_escenario`.
- `_eliminar_escenario(id)` → `confirm_dialog` → `eliminar_escenario`.
- `_crear_bloque(datos)` → `horario_service.crear_bloque(...)`; captura
  `ValueError` → `toast_warning(str(exc))` (R9).
- `_editar_bloque` / `_eliminar_bloque` análogos.

El `form_dialog` de bloque toma `asignacion_id` (opciones de `_s["asignaciones"]`,
solo activas — R11), `dia`, `hora_inicio`, `hora_fin`, `sala`. El servicio deriva
grupo/asignatura/docente de la asignación; la UI no los envía.

## Componentes design system

`form_dialog`, `confirm_dialog`, `empty_state`, `status_badge`, `btn_primary/
secondary/danger/icon`, `toast_*`. Sin `style=` estático ni `ui.button().props()`
(R14).

### Alternativa descartada

**Grilla editable con drag & drop nativo de bloques.** Atractiva pero costosa y
frágil en NiceGUI/Quasar; se difiere. La edición por celda (crear/editar/eliminar
con diálogo) cubre el requisito de "edición manual" con menos riesgo. El
movimiento se modela como editar día/hora del bloque.

## Verificación

- `python scripts/check_design.py --file src/interface/pages/academico/horarios.py`
- `python init.py` exit 0; smoke: crear escenario, agregar bloques (incluyendo un
  intento que viole un cruce y otro que exceda el tope), activar escenario.
