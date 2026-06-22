# paso_36 — Autorización a nivel de objeto por institución

## Contexto y decisión (David)

Cierra el hallazgo E de la auditoría de enrutado. Las guardas (paso_35) comprueban **rol**, y el scope central (frente C) filtra **listados**. Pero los métodos de servicio que operan **por `id`** sobre una entidad concreta (actualizar/eliminar/desactivar/reset/get_by_id) **no verifican que el objeto pertenezca a la institución del usuario**. Con multi-tenant vivo, un director con el `id` de un objeto de **otra** institución podría leerlo/mutarlo. Hay que añadir **verificación de pertenencia** en esas operaciones.

**Regla:** si `institucion_actual()` es `None` (admin de plataforma / seed / arranque) → SIN check (cross-tenant por diseño). Si no es None → el objeto debe pertenecer a esa institución, o se rechaza.

**CRÍTICO:** verificar contra el `institucion_id` del objeto **leído del repo por su id**, NUNCA el `institucion_id` del objeto que pasa el caller (que podría venir forjado para coincidir con el del atacante).

Alcance: entidades con `institucion_id` **directo** (usuarios, estudiantes, grupos, asignaturas, salas, plantillas_franja, configuracion_anio). Las entidades de scope **transitivo** (asignaciones, notas, escenarios, control_diario…) quedan cubiertas por (a) el scope de sus listados (B3/B4) y (b) el acceso vía su padre ya verificado; se documentan como residual de menor prioridad, no se tocan aquí.

## Tareas

> Estado implementer: T1–T6 [x] — `python init.py` verde (1181 passed, 1 skipped).

### T1 — Helper de pertenencia [x]
- En `src/services/contexto_tenant.py`: añadir `OperacionFueraDeInstitucionError(PermissionError)` y `verificar_pertenencia(institucion_id_objeto: int | None) -> None` que:
  - si `institucion_actual()` es `None` → no hace nada (admin/seed, cross-tenant permitido);
  - si no → lanza `OperacionFueraDeInstitucionError` cuando `institucion_id_objeto != institucion_actual()`.
- Tests del helper (scope None → pasa siempre; scope X → pasa con X, lanza con Y).

### T2 [x] — usuario_service (por id)
- En `actualizar`, `desactivar`, `reactivar`, `cambiar_rol`, `resetear_password`, `get_by_id`: tras leer el usuario destino por id (ya lo hacen vía `_get_usuario_o_lanzar`), llamar `verificar_pertenencia(target.institucion_id)`. Así el RBAC (paso_23) + pertenencia se combinan: un director solo gestiona usuarios de SU institución; el admin (scope None) sigue cross-tenant.

### T3 [x] — estudiante_service (por id)
- En `actualizar`, `actualizar_piar`, `get_by_id` (y cualquier mutación por id): leer el estudiante por id y `verificar_pertenencia(est.institucion_id)`.

### T4 [x] — infraestructura_service (por id)
- En las mutaciones por id de entidades con institucion_id directo: `actualizar_grupo`/`eliminar_grupo`, `actualizar_asignatura`/`eliminar_asignatura`, `actualizar_sala`/`eliminar_sala`, `eliminar_plantilla` (y su actualizar si existe): **leer el objeto actual por id desde el repo** y `verificar_pertenencia(obj.institucion_id)` ANTES de mutar. Para los `actualizar_*` que reciben un objeto completo, NO confiar en el `institucion_id` del objeto recibido — usar el del registro persistido; además impedir que el update cambie la institución (preservar la existente).
- (areas_conocimiento sigue siendo catálogo global → sin check.)

### T5 [x] — configuracion_service (por id)
- `activar_anio` y cualquier `actualizar` por `anio_id`: leer el año por id y `verificar_pertenencia(anio.institucion_id)` (el director solo activa/edita años de su institución).

### T6 [x] — Tests + verificación
- Tests de aislamiento por objeto (con 2 instituciones): un director de la inst. A **NO** puede `actualizar`/`eliminar`/`desactivar`/`get_by_id` un grupo/estudiante/usuario/sala/año de la inst. B (lanza `OperacionFueraDeInstitucionError`); SÍ puede con los de la A; el admin (scope None) puede con ambos. Verificar que pasar un objeto con `institucion_id` forjado no burla el check (se usa el del repo).
- `python init.py` VERDE (baseline 1154 passed, 1 skipped; corregir fallout — fakes/tests que mutan por id sin sesión tienen scope None y no se ven afectados). check_imports + check_design en verde. Regla de capas intacta.
- `progress/impl_paso_36.md`.

## criterio_done
Existe `verificar_pertenencia` + `OperacionFueraDeInstitucionError`; las mutaciones y get_by_id por id de usuarios/estudiantes/grupos/asignaturas/salas/plantillas/configuracion_anio verifican que el objeto (leído del repo) pertenezca a `institucion_actual()`; admin (scope None) sigue cross-tenant; un objeto con institucion_id forjado no burla el check; tests de aislamiento por objeto; `python init.py` verde. Con esto cierra la dimensión multi-tenant de la seguridad del enrutado (E).
