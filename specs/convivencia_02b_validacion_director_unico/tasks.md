# convivencia_02b — Validación: un docente dirige un solo grupo

> Parche de la Fase 1 (`convivencia_00_roadmap`), sobre lo entregado en `convivencia_02`. Pedido por David tras verificación manual.

## Contexto y decisión (David)

Al asignar director de grupo debe respetarse una **unicidad**: un docente puede ser director de **un solo grupo**. Intentar asignarlo como director de un segundo grupo (mientras dirige otro) debe **bloquearse y levantar una alerta** (no persistir). Cambiar el director de un grupo dado sigue permitido (reemplaza al anterior). Un grupo, por diseño (columna única `director_grupo_id`), ya no puede tener dos directores.

Estado actual (`convivencia_02`):
- `catalogo_academico_service.asignar_director_grupo(grupo_id, usuario_id | None)` valida que el usuario tenga asignación activa en el grupo, pero **no** valida que no dirija ya otro grupo.
- La UI (`grupos.py`) llama al servicio y muestra toasts.

## Tareas

### T1 — Validación en el servicio
- En `catalogo_academico_service.asignar_director_grupo`, antes de persistir (y solo cuando `usuario_id` no es `None`): si ese `usuario_id` ya es `director_grupo_id` de **otro** grupo (id distinto al que se está editando), **lanzar `ValueError`** con un mensaje claro (p.ej. "El docente X ya es director del grupo Y; un docente solo puede dirigir un grupo."). No persistir.
- Reasignar el director del **mismo** grupo (mismo `grupo_id`) sigue permitido (reemplazo idempotente). Desasignar (`None`) siempre permitido.
- Determinar "dirige otro grupo" con datos ya disponibles vía servicio (p.ej. escanear `listar_grupos()` por `director_grupo_id`, o un método auxiliar). No duplicar SQL en la página.

### T2 — Alerta en la UI
- En `grupos.py`, capturar el `ValueError` del servicio y mostrarlo con `toast_error`/`toast_warning` (la "alerta"), sin romper la página; el selector debe revertir/refrescar al estado real (no dejar seleccionado un valor que no se guardó).

### T3 — Tests
- Test de servicio: asignar a un docente que ya dirige otro grupo → lanza `ValueError`, no persiste. Reasignar el mismo grupo a otro docente libre → OK. Desasignar (`None`) → OK. Asignar a docente sin asignación en el grupo → sigue fallando como antes.

### T4 — Verificación
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services` y `--layer interface` en verde.
- `check_design.py --file src/interface/pages/admin/grupos.py` verde.
- `pytest tests/unit/services/ -q` verde.
- `init.py` VERDE.
- `progress/impl_convivencia_02b.md`.

## criterio_done
Asignar como director de grupo a un docente que ya dirige otro grupo se bloquea con una alerta visible y no persiste; reemplazar el director del mismo grupo y desasignar siguen funcionando; tests de servicio verdes; `init.py` verde; check_design/check_imports verdes.
