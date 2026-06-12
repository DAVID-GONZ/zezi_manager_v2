# paso_14g_plantilla_descarga — tasks

Scope: `src/services/horario_service.py`,
`src/interface/pages/academico/horarios.py`,
`tests/unit/services/test_horario_lote.py` (ampliar),
`tests/unit/services/test_horario_export.py` (nuevo),
`tests/integration/test_asignacion_asignatura_horario.py` (nuevo).

---

### T1 — `HorarioService`: constante + helpers + `plantilla_filas` / `filas_exportables`
Añadir `COLUMNAS_HORARIO`, helpers `_dia_str`/`_hora_str` (extraídos del patrón de
`analizar_lote`) y los dos métodos. Sin imports de exportación ni NiceGUI.
Importar `FiltroAsignacionesDTO` desde `src.domain.models.asignacion`.
**Verif:** `python -X utf8 -c "from src.services.horario_service import HorarioService, COLUMNAS_HORARIO"`

### T2 — Interfaz: plantilla prellenada + botón Descargar horario
En `_seccion_carga_masiva`, reemplazar `_descargar_plantilla` por la versión que
usa `plantilla_filas` + `exporter_service().exportar_csv` + `ui.download`. Añadir
botón **Descargar horario** que use `filas_exportables(escenario_sel.id)`. Avisos
con `toast_warning` cuando no hay datos (R6). Solo `puede_escribir`.
**Verif:** `python -X utf8 scripts/check_design.py --file src/interface/pages/academico/horarios.py`

### T3 — Tests de descarga (`test_horario_export.py`)
`plantilla_filas`: 3 asignaciones activas → 3 filas con `COLUMNAS_HORARIO`, día/hora
vacíos, sala "Aula". `filas_exportables`: 2 bloques → 2 filas completas; filtro por
grupo; escenario vacío → `[]`.
**Verif:** `python -X utf8 -m pytest tests/unit/services/test_horario_export.py -q`

### T4 — Test de carga ida-y-vuelta (`test_horario_lote.py`, ampliar)
Exportar filas de un escenario (FakeRepo) y re-analizarlas sobre escenario vacío →
todas `ok`; columnas de referencia no rompen el parser.
**Verif:** `python -X utf8 -m pytest tests/unit/services/test_horario_lote.py -q`

### T5 — Test de integración (`test_asignacion_asignatura_horario.py`)
Con `db_conn`/`seed_result`: sin asignaciones huérfanas (asignatura/grupo
existen); crear un bloque sobre el escenario activo y verificar coherencia de
`grupo_id`/`asignatura_id`/`usuario_id` con su asignación; `listar_horario_escenario`
incluye el bloque con nombres resueltos no vacíos.
**Verif:** `python -X utf8 -m pytest tests/integration/test_asignacion_asignatura_horario.py -q`

### T6 — Verificación integral
**Verif:** `python -X utf8 init.py` exit 0; `python -X utf8 -m pytest tests/ -q` sin
regresiones.

Al terminar: `step_list.json` → `done` tras reviewer.
