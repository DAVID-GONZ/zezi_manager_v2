# paso_14f_carga_masiva — tasks

Scope: `src/services/horario_service.py`,
`src/domain/models/infraestructura.py` (DTOs de lote),
`src/domain/ports/infraestructura_repo.py`,
`src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`,
`src/interface/pages/academico/horarios.py`,
`tests/unit/services/`, `tests/integration/`.

---

### T1 — DTOs de lote
`FilaReporteDTO`, `ReporteLoteDTO`, `ResultadoLoteDTO` en `infraestructura.py`,
con props derivadas. Export en `__all__`.
**Verif:** `python -c "from src.domain.models.infraestructura import ReporteLoteDTO, ResultadoLoteDTO, FilaReporteDTO"`

### T2 — Repo: `crear_bloques_masivo`
Declarar e implementar inserción transaccional de varios `Horario`.
**Verif:** `python -m pytest tests/integration/ -q -k masivo`

### T3 — `HorarioService.analizar_lote`
Resolución de asignación por fila, escenario virtual acumulado, validación de
cruces (incl. internos del lote) y topes acumulados; produce `ReporteLoteDTO`.
**Verif:** `python -m pytest tests/unit/services/ -q -k analizar_lote`

### T4 — `HorarioService.aplicar_lote`
Modo "todo o nada" (defecto) y "solo válidas"; persistencia atómica; retorna
`ResultadoLoteDTO`.
**Verif:** `python -m pytest tests/unit/services/ -q -k aplicar_lote`

### T5 — Interfaz: plantilla + upload + reporte + aplicar
Botón descargar plantilla CSV; `ui.upload` → parseo a `list[dict]` →
`analizar_lote` con `skeleton_*`; tabla de reporte con `status_badge`; botones
Aplicar todo / Aplicar solo válidas; `toast_*` de resultado; refresco de grilla.
Solo roles con permiso de edición.
**Verif:** `python scripts/check_design.py --file src/interface/pages/academico/horarios.py`

### T6 — Tests de lote
Casos: fila sin asignación válida → error (R3); dos filas del lote que se solapan
→ una marcada por cruce interno (R5); lote que excede tope de docente sumando
existentes + lote (R6); "todo o nada" no persiste con errores; "solo válidas"
persiste el subconjunto (R8); conteos de resultado correctos (R9).
**Verif:** `python -m pytest tests/ -q -k lote`

### T7 — Verificación integral
**Verif:** `python init.py` exit 0; `python -m pytest tests/ -q` sin regresiones.

Al terminar: `step_list.json` → `spec_ready`.
