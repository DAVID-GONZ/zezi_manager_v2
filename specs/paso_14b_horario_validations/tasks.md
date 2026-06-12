# paso_14b_horario_validations — tasks

Scope: `src/services/horario_service.py` (nuevo),
`src/domain/models/infraestructura.py` (CupoDTO),
`src/domain/ports/infraestructura_repo.py`,
`src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`,
`container.py`, `tests/unit/services/`, `tests/integration/`.

---

### T1 — `CupoDTO`
Añadir a `infraestructura.py`: `usadas`, `maximas: int|None`, `disponibles`,
`excedido`. Export en `__all__`.
**Verif:** `python -c "from src.domain.models.infraestructura import CupoDTO; CupoDTO(usadas=2, maximas=4)"`

### T2 — Puerto: `existe_cruce`, conteos; retirar `existe_conflicto_horario`
Declarar `existe_cruce(...)`, `contar_bloques_asignacion`,
`contar_bloques_docente`. Eliminar `existe_conflicto_horario` del puerto.
**Verif:** `python scripts/check_imports.py --layer domain`

### T3 — Repo SQLite: implementación de cruce y conteos
Implementar los tres métodos; eliminar `existe_conflicto_horario` y actualizar
llamadores.
**Verif:** `python -m pytest tests/integration/ -q -k cruce`

### T4 — `HorarioService`
Crear el servicio con `crear_bloque`, `mover_bloque`, `actualizar_bloque`,
`eliminar_bloque`, `disponibilidad_asignacion`, `disponibilidad_docente`. Reglas
R2–R10. Sin SQL ni NiceGUI.
**Verif:** `python scripts/check_imports.py --layer services`

### T5 — Wiring en `container.py`
Registrar `horario_service()` perezoso con infra/asignacion/usuario repos.
**Verif:** `python -c "from container import Container; Container.horario_service()"`

### T6 — Tests unitarios de validación (FakeRepo)
Casos: asignación inexistente/inactiva (R2); cruce docente (R4); cruce grupo
(R5); cruce sala distinta de "Aula" (R6); exclusión del propio bloque al editar
(R7); tope materia superado (R8); tope docente superado (R9); docente sin tope
no aplica R9 (R10); creación válida (nominal).
**Verif:** `python -m pytest tests/unit/services/ -q -k horario_service`

### T7 — Verificación integral
**Verif:** `python init.py` exit 0; `python -m pytest tests/ -q` sin regresiones.

Al terminar: `step_list.json` → `spec_ready`.
