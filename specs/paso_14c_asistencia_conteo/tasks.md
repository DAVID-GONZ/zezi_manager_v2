# paso_14c_asistencia_conteo — tasks

Scope: `src/domain/ports/asistencia_repo.py`,
`src/infrastructure/db/repositories/sqlite_asistencia_repo.py`,
`src/services/asistencia_service.py`, `tests/unit/services/`, `tests/integration/`.

---

### T1 — Puerto: métodos de conteo
Declarar `contar_clases_dictadas_docente` y `clases_dictadas_por_asignacion` en
`IAsistenciaRepository`.
**Verif:** `python scripts/check_imports.py --layer domain`

### T2 — Repo SQLite: queries de conteo
Implementar ambos con `JOIN asignaciones` + `GROUP BY asignacion_id, fecha` y
filtro `strftime` por año/mes.
**Verif:** `python -m pytest tests/integration/ -q -k clases_dictadas`

### T3 — Servicio: `contar_clases_mes` / `clases_mes_por_asignacion`
Delegar en el repo, validar `1 <= mes <= 12`.
**Verif:** `python scripts/check_imports.py --layer services`

### T4 — Tests
Casos: docente con registros en 2 asignaciones distintas el mismo día cuenta 2
(R1, R5); mes sin registros retorna 0 (R4); un día con muchos estudiantes en una
asignación cuenta 1 (R5); desglose por asignación correcto (R6).
**Verif:** `python -m pytest tests/ -q -k clases_dictadas`

### T5 — Verificación integral
**Verif:** `python init.py` exit 0; `python -m pytest tests/ -q` sin regresiones.

Al terminar: `step_list.json` → `spec_ready`.
