# paso_42 — Gestión de estudiantes por rol (director/coordinador gestionan; profesor solo lee)

## Contexto y decisión (David)

En `/estudiantes` (ruta abierta a director/coordinador/profesor) las acciones de gestión (crear, importar CSV, editar, PIAR) **no están gateadas por rol** hoy — cualquiera de los 3 puede usarlas. Decisión:
- **`director` y `coordinador`:** gestionan — cargan (CSV), crean estudiantes, editan, y (en paso_43) trasladan.
- **`profesor`:** **solo lectura** — lista los estudiantes de SUS grupos (ya restringido por asignaciones en cambio previo) y puede ver el detalle, pero SIN botones de crear/importar/editar/PIAR.

(El traslado se implementa en paso_43; aquí solo el gating de las acciones existentes.)

## Tareas

### T1 — Gating en la página `estudiantes.py` ✅
- Calcular `puede_gestionar = ctx.usuario_rol in ("director", "coordinador")` (usar el enum/propiedad coherente con el resto; `ctx.es_directivo` incluye admin, que no accede a esta ruta, así que aquí basta director/coordinador).
- Ocultar (no solo deshabilitar) para profesor: botón **"Nuevo estudiante"** (`_abrir_dialog_matricula`), **"Importar CSV"** (`_abrir_dialog_csv`) y las acciones por fila de **editar** (`_abrir_dialog_edicion`) y **PIAR** (`_abrir_dialog_piar`). El profesor ve la tabla en modo lectura (sus grupos).
- No romper la restricción por asignaciones del docente (cambio previo) ni el "listado inactivo hasta filtrar".

### T2 — Defensa en profundidad en el servicio (RBAC ligero) ✅
- En `estudiante_service`, los métodos de mutación que usa esta página (`matricular`, `matricular_masivo_csv`, `actualizar`, `actualizar_piar`) deben rechazar al profesor: añadir un parámetro `actor_rol: str | None = None` (default None = sin enforcement, para no romper callers/tests) y, si se provee y no es director/coordinador (ni admin/None), lanzar `ValueError`/`PermissionError` accionable. La página pasa `actor_rol=ctx.usuario_rol`.
- (Patrón análogo al RBAC de usuarios de paso_23: regla en el servicio, no solo en la vista.)

### T3 — Verificación ✅
- `python init.py` VERDE (baseline 1195 passed, 1 skipped; corregir fallout). check_design `--file` estudiantes.py exit 0; check_imports interface/services en verde.
- Tests: el servicio rechaza mutaciones con `actor_rol="profesor"`; las acepta con director/coordinador (y con None, comportamiento actual). (El gating de UI no requiere test de NiceGUI, pero documentar.)
- `progress/impl_paso_42.md`.

## criterio_done
En `/estudiantes`, profesor solo lee (sin botones de crear/importar/editar/PIAR); director/coordinador gestionan; las mutaciones del servicio rechazan al profesor vía `actor_rol`; `python init.py` verde.
