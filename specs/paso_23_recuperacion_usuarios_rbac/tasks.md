# paso_23 — Recuperación de usuarios + RBAC de roles en el servicio

## Contexto y decisiones (aprobadas por David)

Cierra huecos del módulo de usuarios detectados en el análisis:
- **Reactivar** y **Restablecer contraseña** existen en la capa de servicio/auth pero NO están cableados en la UI → un usuario desactivado o que olvidó su clave es irrecuperable desde la app.
- El RBAC de roles vive **solo en la vista**; `crear_usuario`/`cambiar_rol` del servicio aceptan cualquier rol. Además hay una **inconsistencia**: "Nuevo usuario" restringe (admin solo crea director) pero "Cambiar rol" ofrece `_ROLES_OPCIONES` (incluye Administrador) sin validación → admin puede promover a admin por esa puerta.

**Decisión de política:** el admin **SÍ** puede crear y promover a otro admin (redundancia / recuperación de la cuenta admin). La regla se aplica **en el servicio/dominio** (defensa en profundidad), no solo en la vista.

Matriz de asignación de roles (quién puede asignar qué):
- `admin`    → puede asignar/crear: **admin, director**
- `director` → puede asignar/crear: **coordinador, profesor**
- otros      → no gestionan usuarios

Gestión por rol del actor sobre un usuario destino:
- `admin`    → puede gestionar (reactivar / desactivar / reset password / cambiar rol) a **cualquier** usuario.
- `director` → puede gestionar (reactivar / desactivar / reset password) solo a **coordinador / profesor**; NO a admin/director, NO cambiar roles a elevados.

**Fuera de alcance:** institución/multi-tenant (eso es paso_24). No añadir `institucion_id` aquí.

## Tareas

### [x] T1 — Política RBAC en dominio + enforcement en servicio
- Crear una política pura en dominio (p.ej. `src/domain/policies/rbac_usuarios.py` o función en el modelo `usuario`): `roles_asignables(actor_rol) -> set[str]` y `puede_gestionar(actor_rol, target_rol) -> bool` según la matriz de arriba. Sin dependencias de infra/interfaz.
- `usuario_service.crear_usuario(dto, creado_por_id, actor_rol=None)`: si `actor_rol` se provee, validar que `dto.rol in roles_asignables(actor_rol)`, si no `raise ValueError` accionable.
- `usuario_service.cambiar_rol(usuario_id, nuevo_rol, cambiado_por_id, actor_rol=None)`: validar `nuevo_rol in roles_asignables(actor_rol)` Y `puede_gestionar(actor_rol, usuario.rol_actual)`.
- Default `actor_rol=None` = sin enforcement (no rompe callers/tests existentes), pero **la vista siempre lo pasa** (`ctx.usuario_rol`).
- Tests: admin puede crear/promover admin y director; director NO puede crear/promover admin/director; director NO puede cambiar el rol de un admin.

### [x] T2 — Reactivar y Restablecer contraseña en el servicio
- `usuario_service.resetear_password(usuario_id, nueva_password, actor_rol=None, reset_por_id=None)` (decorar `@requiere_escritura`): valida `puede_gestionar(actor_rol, target.rol)`; si `nueva_password` vacía usa el username; llama `self._auth.resetear_password(...)`; **audita** con `TipoEventoSesion.RESETEAR_PASSWORD` vía `auditoria` (registrar_evento) con detalles actor→objetivo.
- `reactivar(...)` ya existe (`@requiere_escritura`): añadir validación `puede_gestionar(actor_rol, target.rol)` (param `actor_rol` opcional).
- `desactivar(...)`: añadir la misma validación `puede_gestionar` (param `actor_rol` opcional).
- Tests de los nuevos comportamientos (incluido que reset audita el evento).

### [x] T3 — UI de gestión y recuperación en /admin/usuarios
- La columna de Acciones debe mostrarse para **admin y director** (hoy solo admin), con cada acción **gated por fila** según `puede_gestionar(ctx.usuario_rol, u.rol)`:
  - **Reactivar** (icono `restart_alt`/`person`): visible cuando `not u.activo` y el actor puede gestionar al destino. Llama `usuario_service.reactivar(uid, actor_rol=ctx.usuario_rol)`.
  - **Restablecer contraseña** (icono `key`/`password`): diálogo con "Nueva contraseña" (vacío = usa el username); confirma y llama `resetear_password(...)`. Toast con el resultado.
  - **Desactivar**: igual que hoy pero gated por `puede_gestionar` (no solo `es_admin`).
  - **Cambiar rol**: el select solo ofrece `roles_asignables(ctx.usuario_rol)` (admin: admin/director; director: coordinador/profesor) — corrige la inconsistencia actual de `_ROLES_OPCIONES`.
- Flujo "Nuevo usuario": para admin, las opciones de rol pasan a `{"admin": "Administrador", "director": "Director"}` (admin ya puede crear admin). Pasar `actor_rol=ctx.usuario_rol` a `crear_usuario`.
- Respetar todas las prohibiciones del design system (ThemeManager.icono, clases CSS, sin colores quemados, etc.).

### [x] T4 — Verificación y cierre
- `python init.py` VERDE (baseline 1023 passed, 1 skipped; corregir fallout). check_design sobre usuarios.py exit 0; check_imports --layer domain/services/interface exit 0.
- `progress/impl_paso_23.md`.

## criterio_done
Admin puede crear/promover admin (regla en servicio); director limitado a coordinador/profesor; "Cambiar rol" ya no ofrece roles fuera del alcance del actor; "Reactivar" y "Restablecer contraseña" cableados y auditados; director puede gestionar (reactivar/desactivar/reset) coordinador/profesor; `python init.py` verde.
