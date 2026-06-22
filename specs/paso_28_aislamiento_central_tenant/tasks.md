# paso_28 — Aislamiento central por institución (frente C multi-tenant)

## Contexto y decisión (David)

Mecanismo CENTRAL de scope por institución, espejando el patrón de `src/services/solo_lectura.py`: un `contextvars.ContextVar` con la institución de la sesión actual, poblado en el choke point `SessionContext`, y consultado por los **servicios** para resolver el `institucion_id` que pasan a los repos (parametrizados). Esto evita cablear el filtro página-por-página y deja el carril listo para el frente B (tablas académicas).

**Regla de capas (igual que solo_lectura):** el módulo del contextvar vive en `src/services/`, NO importa interfaz ni infraestructura. Los **repos siguen recibiendo `institucion_id` por parámetro** (los repos NO importan de services). El scope se resuelve en el servicio.

**Regla de scope (clave de corrección):**
`institucion_actual()` = **None** si el rol efectivo de la sesión es `admin` (plataforma, opera cross-tenant y filtra explícito); en otro caso = `institucion_id` de la sesión. Durante "Ver como" el rol efectivo es el del usuario objetivo (no admin), así que queda scopeado a la institución del objetivo. `None` ⇒ los servicios NO auto-filtran (admin ve todo / filtra explícito).

**Fuera de alcance:** `institucion_id` en tablas académicas (grupos/estudiantes/asignaciones/notas…) = frente B. Aquí solo el mecanismo + wiring + refactor de los servicios que YA son tenant-aware (configuración, usuarios) como patrón de referencia.

## Tareas

### [x] T1 — Módulo del contextvar de institución
- Crear `src/services/contexto_tenant.py` (puro, sin imports de interfaz/infra), espejando `solo_lectura.py`:
  - `_institucion_actual: contextvars.ContextVar[int | None]` default `None`.
  - `activar_institucion(institucion_id: int | None) -> None`.
  - `institucion_actual() -> int | None`.
  - `usar_institucion(institucion_id)` — **context manager** (`@contextlib.contextmanager`) que setea el contextvar y lo restaura al salir (para seed/scripts/tests que no tienen sesión).
  - `__all__`.
- Tests del módulo: default None, set/get, restauración del context manager.

### [x] T2 — Wiring desde la sesión (choke point)
- En `SessionContext` (`src/interface/context/session_context.py`), añadir `_sincronizar_institucion()` (espejo de `_sincronizar_solo_lectura`) que calcula el scope con la **regla de scope** de arriba y llama `activar_institucion(scope)`:
  - `scope = None if self.usuario_rol == "admin" else self.institucion_id`.
- Invocarlo donde ya se sincroniza solo_lectura: en `desde_storage()` (incluido el caso sin sesión → `activar_institucion(None)`) y en `guardar()`.
- Verificar que `iniciar_ver_como`/`salir_ver_como` dejan el contextvar correcto (al persistir con `guardar()` debería resolverse solo; si no llaman a guardar, sincronizar explícitamente). Durante ver-como (rol del objetivo) el scope = institución del objetivo; al salir, vuelve al scope del admin (None).

### [x] T3 — Refactor de los servicios tenant-aware para resolver desde el contextvar
- `configuracion_service._resolver_institucion(institucion_id)`: orden de resolución → `institucion_id` explícito → `institucion_actual()` → `Container.institucion_service().id_por_defecto()` (fallback de arranque/seed sin sesión). Así los callers ya no NECESITAN pasar `ctx.institucion_id` (queda automático); pueden seguir pasándolo sin daño.
- `usuario_service`: en `listar_resumenes`/`listar_filtrado`/`listar_para_ver_como`, si el `institucion_id` recibido es `None`, tomar `institucion_actual()` (que es None para admin → ve todas; la institución para director → filtrado). NO romper el filtro explícito del admin (selector "Todas"/institución concreta) ni el `solo_activos`.
- Simplificar `src/interface/pages/admin/usuarios.py`: el `institucion_forzada` del director puede apoyarse en el contextvar (mantener el comportamiento idéntico: director ve solo su institución, admin filtra). No cambiar la UX.
- (Opcional) Simplificar los callers de `get_activa()` cableados en paso_27 para confiar en el contextvar; si genera churn, dejarlos.

### [x] T4 — Tests de comportamiento
- `institucion_actual()` None por defecto y tras sesión admin; = institución para director; = institución del objetivo durante "Ver como".
- `configuracion_service.get_activa()` sin argumento resuelve la institución del contextvar (director) y cae a #1 sin sesión.
- `usuario_service.listar_resumenes` auto-scopea para director y NO filtra para admin (contextvar None).
- Sin regresiones en los tests de paso_24/27.

### [x] T5 — Verificación y cierre
- `python init.py` VERDE (baseline 1078 passed, 1 skipped; corregir fallout). check_imports domain/infrastructure/services/interface + check_design en verde. Confirmar que `contexto_tenant.py` NO importa interfaz/infra y que ningún repo importa de services.
- `progress/impl_paso_28.md` (mecanismo, regla de scope admin=None, cómo quedó el wiring, output de init.py).

## criterio_done
Existe `contexto_tenant.py` (contextvar + activar/leer + context manager) en la capa de servicios; la sesión lo puebla con la regla admin→None / resto→su institución (objetivo durante "Ver como"); `configuracion_service` y `usuario_service` resuelven el scope desde el contextvar (repos siguen parametrizados); el admin sigue viendo cross-tenant y el director solo lo suyo, sin cablear el filtro en cada página; `python init.py` verde y regla de capas intacta.
