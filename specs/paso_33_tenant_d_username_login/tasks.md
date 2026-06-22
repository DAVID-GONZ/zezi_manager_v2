# paso_33 — Frente D: username por institución + login que desambigüe

## Contexto y decisión (David)

Último frente de multi-tenant. Hoy `usuarios.usuario` es `UNIQUE` global → dos instituciones no pueden tener ambas un "director"/"c.lopez". Objetivo: unicidad **por institución** + login que resuelva la institución sin degradar el caso de una sola institución.

**Patrón de referencia OBLIGADO (rebuild):** `_migrar_*_por_institucion` de paso_27/29/30/32. `usuarios(id)` lo referencian ~20 tablas hijas (asignaciones, notas, cierres, registros de auditoría por usuario, etc.) → **preservar `id`** sí o sí; `foreign_keys OFF` durante + `foreign_key_check` al final.

**Nota sobre admin:** todos los usuarios tienen `institucion_id` (backfill #1 de paso_24); los admin se crean siempre en la institución por defecto (#1) porque `institucion_actual()` es None para admin y `crear_usuario` cae a `id_por_defecto()`. Así `UNIQUE(institucion_id, usuario)` también cubre a los admin (únicos dentro de #1). No introducir reglas especiales de admin en este paso.

## Tareas

### T1 — usuarios: unicidad de username por institución + migración
- DDL BD nueva: en `usuarios`, cambiar `usuario TEXT NOT NULL UNIQUE` → `usuario TEXT NOT NULL` + `UNIQUE(institucion_id, usuario)`. Mantener el resto (incl. `institucion_id` ya existente de paso_24). Índice si aplica.
- Migración rebuild idempotente (solo si la unicidad sigue siendo la global; detectar y reconstruir), **copiando `id`**, manejo de `PRAGMA foreign_keys` + `foreign_key_check`. (institucion_id ya está poblado; no re-backfill.)

### T2 — Unicidad de creación por institución
- `usuario_service.crear_usuario`: el chequeo de unicidad de username pasa a ser **por institución** — `existe_usuario(usuario, institucion_id)` donde `institucion_id` = el que se asigna al nuevo usuario (resuelto desde `institucion_actual()` o `id_por_defecto()`). Un director creando "prof1" solo colisiona con "prof1" de SU institución.
- `usuario_repo`/port: `get_by_username` y `existe_usuario` aceptan `institucion_id: int | None` (None = comportamiento global actual, para compatibilidad). Añadir `listar_por_username(usuario) -> list[Usuario]` (todas las instituciones) para el login.

### T3 — Login que desambigüe (sin degradar single-tenant)
- En el punto de autenticación que invoca `login.py` (el método de `Container.auth_service()` que valida credenciales — verificar cuál es): `autenticar(usuario, password, institucion_id: int | None = None)`:
  - `candidatos = listar_por_username(usuario)` (filtrar a `institucion_id` si se pasó).
  - 0 → credenciales inválidas (mismo mensaje genérico que hoy, sin filtrar info).
  - 1 → verificar password y entrar (caso single-tenant: **UX idéntica**, sin campo institución).
  - >1 → NO probar password contra varios; lanzar/retornar una señal de **ambigüedad** con la lista de instituciones candidatas.
- `login.py`: si la autenticación retorna ambigüedad, **revelar un `ui.select` de institución** (poblado con las instituciones candidatas) y reintentar `autenticar(usuario, password, institucion_id)` con la elegida. Mientras no haya ambigüedad, el formulario no muestra institución. Mantener el manejo de errores/estilos actual.
- Al autenticar con éxito, poblar `SessionContext.institucion_id` con la del usuario (ya se hace desde paso_24; confirmar que sigue correcto con el nuevo flujo).

### T4 — Seed + tests + verificación
- Seed: sin cambios de identidad (los usuarios siguen en #1); confirmar que el seed no rompe con la unicidad compuesta.
- Tests: mismo `usuario` (p.ej. "director") en DOS instituciones NO colisiona; `crear_usuario` rechaza duplicado **dentro** de la misma institución pero permite el mismo nombre en otra; login con username único entra sin institución; login con username ambiguo exige institución y entra con la correcta; password incorrecto falla igual; migración preserva ids/FKs (`foreign_key_check` limpio), idempotente.
- `python init.py` VERDE (baseline 1135 passed, 1 skipped; corregir fallout — fakes/repos que usan `get_by_username`/`existe_usuario` deben contemplar el nuevo parámetro opcional). check_imports + check_design en verde.
- **Probar la migración a mano** sobre BD preexistente con usuarios + hijos (asignaciones/notas): ids preservados, FKs intactos. Documentar.
- `progress/impl_paso_33.md`.

## criterio_done
`usuarios` tiene `UNIQUE(institucion_id, usuario)` con migración idempotente que preserva ids/FKs; la creación valida unicidad por institución; el login entra directo cuando el username es único (UX single-tenant intacta) y pide institución solo cuando es ambiguo; `python init.py` verde y BD preexistente migra sin pérdida ni FKs rotos. Con esto el multi-tenant queda funcionalmente completo (instituciones + usuarios + config + todo el modelo académico aislados, y login por institución).
