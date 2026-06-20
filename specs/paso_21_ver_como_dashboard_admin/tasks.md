# paso_21 — "Ver como" (impersonación read-only) + Dashboard de plataforma (admin)

## Contexto y decisiones (aprobadas por David)

Continuación de `paso_20` (admin = rol de plataforma). Dos entregables:

1. **Ver como:** admin asume la vista de un usuario concreto en **SOLO LECTURA**, para verificar lo que ese usuario ve sin perder su independencia de auditor. El bloqueo de escritura se aplica **de forma CENTRAL en la capa de servicios** (decisión explícita de David — no página por página). Banner persistente + "Salir". Auditado.
2. **Dashboard de plataforma (admin):** reescribir la rama admin de `inicio.py` para mostrar **datos de uso / tráfico / nº de usuarios por institución**, con la presentación **estructurada para multi-tenant** (hoy single-tenant: una institución = la config activa). Arreglar los accesos rápidos rotos que dejó paso_20.

**Fuera de alcance (NO hacer aquí):**
- Diferenciación profunda del dashboard de profesor vs directivo → `paso_22`. NO tocar las ramas `profesor`/`director`/`coordinador` de inicio.py.
- Multi-tenancy real (tablas/aislamiento por tenant). Solo dejar la presentación preparada.

---

## Tareas

> Estado de implementación (impl_paso_21):
> - [x] T1 — Mecanismo central de solo-lectura + test del guard
> - [x] T2 — SessionContext: impersonación + activación del flag + auditoría
> - [x] T3 — Banner persistente + Salir (layout)
> - [x] T4 — Entradas a "Ver como" (usuarios.py por fila + dashboard admin)
> - [x] T5 — Dashboard de plataforma (admin) en inicio.py
> - [x] T6 — Verificación (init.py verde: 1015 passed, 1 skipped)
> - [x] T7 — Componente de fecha compartido (date-picker + presets) y migración
> - [x] T8 — Selector "Ver como" de doble filtrado (institución → usuario), multi-tenant-ready

### T1 — Mecanismo central de solo-lectura (capa de servicios)
- Crear módulo neutral SIN dependencias de interfaz: `src/services/solo_lectura.py`.
  - `contextvars.ContextVar[bool]` privado, default `False`.
  - `activar_solo_lectura(valor: bool) -> None`, `es_solo_lectura() -> bool`.
  - Excepción `OperacionSoloLecturaError(PermissionError)` con mensaje accionable ("Sesión en modo solo lectura (Ver como): no se permiten cambios.").
  - Helper `verificar_escritura() -> None` que lanza `OperacionSoloLecturaError` si `es_solo_lectura()`.
  - Opcional: decorador `requiere_escritura` equivalente.
- Aplicar `verificar_escritura()` (o el decorador) al INICIO de los métodos de **MUTACIÓN** de los servicios de aplicación usados desde páginas (crear/actualizar/editar/eliminar/desactivar/reactivar/registrar/cerrar/guardar/asignar...). Cubrir como mínimo: `usuario_service`, `estudiante_service`, `asignacion_service`, `evaluacion_service`, `asistencia_service`, los servicios de convivencia, `configuracion_service`, `plan_estudios_service`, `infraestructura_service`, `cierre_service`, `habilitacion_service`, `plan_mejoramiento_service`, `periodo_service`. **Los métodos de LECTURA no se tocan.**
- Respeta la regla de capas: `solo_lectura.py` NO importa interfaz; los servicios importan el helper desde la capa de servicios. El default `False` garantiza que el comportamiento normal NO cambia (los tests existentes siguen verdes).
- Test nuevo: con `activar_solo_lectura(True)`, un método de escritura representativo (p.ej. `usuario_service.crear_usuario`) lanza `OperacionSoloLecturaError`; con `False`, funciona normal.

### T2 — SessionContext: estado de impersonación + activación del flag
- En `src/interface/context/session_context.py` y el storage:
  - Campos nuevos: `impersonando: bool = False`, `admin_real_id/admin_real_nombre/admin_real_rol` (identidad real del admin para poder volver), `solo_lectura: bool = False`. Incluirlos en `desde_storage()` y `guardar()`.
  - `desde_storage()` debe llamar `activar_solo_lectura(self.solo_lectura)` como **choke point único** (corre al inicio de cada página y de los handlers que releen el contexto).
  - Método `iniciar_ver_como(target_usuario_id, target_rol, target_nombre, contexto_academico_target)`: guarda la identidad real del admin, sustituye `usuario_id/usuario_rol/usuario_nombre` por los del target, carga el contexto académico del target si existe (si no, queda incompleto y las pantallas muestran sus empty states), pone `impersonando=True`, `solo_lectura=True`, persiste y registra evento de auditoría.
  - Método `salir_ver_como()`: restaura la identidad real del admin, limpia impersonando/solo_lectura, persiste, registra evento de fin.
- Auditoría: añadir a `TipoEventoSesion` (en `src/domain/models/auditoria.py`) `VER_COMO_INICIO` y `VER_COMO_FIN`; registrar ambos vía `auditoria_service.registrar_evento(...)` con `detalles` indicando admin real → usuario objetivo. (Append-only; mantiene la independencia del log.)

### T3 — Banner persistente + salir (layout)
- En `app_layout`/topbar (`src/interface/design/layout.py`): si `ctx.impersonando`, renderizar un banner fijo (clase CSS del design system, sin `.style` estático) con texto "Estás viendo como <nombre> · solo lectura" y botón "Salir" que llama `salir_ver_como()` y navega a `/inicio`.

### T4 — Entradas a "Ver como"
- En `/admin/usuarios` (`usuarios.py`): acción por fila **"Ver como"** visible SOLO para admin, que arranca `iniciar_ver_como(...)` con los datos de esa fila. No permitir ver-como a sí mismo. (Ver como otro admin: permitido por ahora.)
- En el dashboard de admin (T5): acción **"Ver como…"** que abre un selector de usuario (reutilizar el listado de `usuario_service`) y arranca la impersonación.

### T5 — Dashboard de plataforma (admin) en inicio.py
- Reescribir **SOLO la rama admin** de `inicio.py` (no tocar profesor/director/coordinador).
- **Saludo:** mensaje de plataforma (auditoría + gestión de cuentas), sin framing académico ("Administra la configuración…").
- **Stats con DATOS REALES** de uso/tráfico/usuarios por institución. Añadir métodos de agregación de **solo lectura** en la capa de servicios (no computar en la página):
  - `usuario_service.resumen_por_rol()` → conteo de usuarios por rol y total (y nº de directores).
  - `auditoria_service.resumen_uso(dias: int)` → logins (hoy / últimos 7 días), accesos denegados (7 días), nº de sesiones/usuarios activos recientes, a partir de `listar_eventos_sesion`.
  - Presentar "por institución" (hoy una fila = la config activa) de forma que añadir tenants después sea natural (no quemar "1 institución" como literal único).
- **Accesos rápidos VÁLIDOS** (eliminar los rotos `/admin/configuracion`, `/admin/grupos`, `/admin/asignaciones`): "Auditoría" → `/admin/auditoria`; "Usuarios" → `/admin/usuarios`; "Ver como…" (abre selector).
- **Actividad reciente:** mantener (feed de auditoría global ya existente).

### T6 — Verificación y cierre
- `python init.py` VERDE (baseline previa: 1004 passed, 1 skipped). Corregir fallout. Incluir el test del guard read-only (T1).
- `python scripts/check_design.py --file src/interface/pages/inicio.py` y `--file src/interface/design/layout.py` exit 0; `python scripts/check_imports.py --layer interface` y `--layer services` exit 0.
- Escribir `progress/impl_paso_21.md` (archivos, tabla de verificación por tarea, decisiones de diseño del mecanismo read-only y del dashboard, output completo de `python init.py`).

### T7 — Componente de fecha compartido (design system) + migración
Refinamiento de UX (aprobado por David: opción "componente compartido + presets, migrar todo").
- Crear componente(s) de fecha en `src/interface/design/components/` (exportar desde el `__init__` de components), siguiendo TODAS las reglas del design system (clases CSS de `styles/`, `ThemeManager.icono()`, sin `.style` estático sin `# DYNAMIC`, sin colores quemados):
  - `date_input(...)`: campo de **una** fecha con date-picker (calendario), label, dense/outlined; devuelve/usa "YYYY-MM-DD". Reemplaza el patrón suelto `.props("type=date")`.
  - `date_range_input(...)`: rango **Desde/Hasta** con **presets rápidos** (Hoy, Últimos 7 días, Últimos 30 días, Periodo activo) que setean ambas fechas; callback `on_change(desde, hasta)`. Validación: `desde <= hasta`.
- Usar `date_range_input` en `src/interface/pages/admin/auditoria.py`: **reemplazar los dos `ui.input` de texto "Desde/Hasta"** (líneas ~200-215) por el rango con presets. Mantener la semántica actual (`_s["desde"]/_s["hasta"]` como "YYYY-MM-DD" o None y `_on_filtros_cambio`).
- **Migrar** los usos sueltos de `.props("type=date")` al componente compartido:
  - `src/interface/pages/informes/consolidado_asistencia.py` (2 inputs)
  - `src/interface/pages/informes/consolidado_notas.py` (2 inputs)
  - `src/interface/pages/academico/registro_asistencia.py` (1 input, clase `asis-date-input` — preservar el comportamiento/estilo o equivalente vía el componente)
- `check_design` sobre el componente nuevo y las páginas migradas en exit 0; sin regresiones visuales de fondo.

### T8 — Selector "Ver como" de doble filtrado (multi-tenant-ready)
Decisión de David: en multi-tenant el selector debe filtrar primero por **institución** y luego por los **usuarios de esa institución**.
- En `_abrir_selector_ver_como(ctx)` de `inicio.py` (y donde aplique): convertir el `form_dialog` de un solo select a **dos niveles**:
  1. **Institución** (select): por ahora una sola opción = la institución activa (`configuracion_service.get_activa()`), preseleccionada. Estructurar para que añadir tenants después sea natural (no quemar la única institución como literal fijo).
  2. **Usuario** (select): lista de usuarios **filtrada por la institución elegida**. Hoy (single-tenant) son todos los usuarios activos salvo uno mismo; pero el filtrado debe pasar por un parámetro de scope de institución (p.ej. `institucion_id` opcional en el listado, no-op en single-tenant) para que el día de mañana filtre de verdad.
- NO crear tablas/columnas de tenant ni `institucion_id` en el modelo de usuario todavía: solo el scaffolding del selector y el hook de parámetro. Documentarlo como "preparado para multi-tenant" en el progress.
- La acción "Ver como" por fila en `/admin/usuarios` ya es específica de un usuario; no requiere el doble nivel (dejarla como está).

## criterio_done
"Ver como" funciona: admin impersona en solo lectura, la escritura queda bloqueada centralmente en servicios (`OperacionSoloLecturaError`), banner persistente + salir, eventos VER_COMO_INICIO/FIN en auditoría. Dashboard de admin con datos de uso reales y accesos rápidos válidos (sin enlaces rotos), estructura lista para multi-tenant. Inputs de fecha mejorados: componente de fecha compartido con date-picker + presets, usado en la auditoría y migradas las páginas que usaban `type=date` suelto. Selector "Ver como" de doble filtrado (institución → usuario) preparado para multi-tenant. `python init.py` verde. NO se tocaron los dashboards de profesor/directivo (eso es paso_22).
