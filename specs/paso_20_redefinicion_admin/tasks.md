# paso_20_redefinicion_admin — Redefinir `admin` como rol de plataforma + Vista de Auditoría

## Contexto y decisión de diseño (aprobada por David)

`admin` deja de ser un rol institucional/académico y pasa a ser un **rol de plataforma/sistema**:

- **Auditor (lectura global):** ve el log de auditoría completo. Nueva vista `/admin/auditoria`.
- **Aprovisionador acotado:** SOLO puede crear/gestionar usuarios con rol `director`. Es el dueño-bootstrap. El `director` crea coordinadores y profesores.
- **NO participa en docencia ni configuración institucional:** no califica, no registra asistencia, no cierra periodos, no configura SIE ni información institucional por sí mismo.

`director` hereda todo lo institucional que antes compartía con `admin`.

**Fuera de alcance de este paso (será paso_21):** impersonación "ver como" de solo lectura. NO implementar aquí.

Modelo de despliegue: single-tenant hoy (una institución por instalación). No introducir lógica multi-tenant todavía.

---

## Matriz de roles objetivo

| Función | Roles que acceden (NUEVO) |
|---|---|
| Inicio | todos (`*`) |
| Aula (planilla, asistencia, observaciones, comportamiento, seguimiento) | director, coordinador, profesor |
| Académico (estudiantes, grupos, asignaturas, plan estudios, asignaciones, horarios, disponibilidad, salas) | director, coordinador, profesor (según ya estaba, **menos admin**) |
| Evaluación (config SIE, habilitaciones, planes, cierres) | director, coordinador, profesor (según ya estaba, **menos admin**) |
| Informes | director, coordinador, profesor (según ya estaba, **menos admin**) |
| Usuarios | **admin** (crea solo director) + **director** (crea coordinador/profesor) |
| Información Institucional | **director** (quitar admin) |
| Auditoría (NUEVA) | **admin** |

Regla mecánica: en cada guarda de página y cada item de NAV que hoy lista `"admin"` junto a roles académicos/institucionales, **quitar `"admin"`**. Excepciones donde `admin` PERMANECE: página/NAV de Usuarios, divider de la sección admin, y la nueva vista de Auditoría (admin exclusivo).

---

## Tareas

### T1 — NAV_ITEMS + test_navitems
Archivo: `src/interface/design/layout.py` (`NAV_ITEMS`).
- Quitar `"admin"` de los grupos **Aula**, **Académico**, **Evaluación**, **Informes** (en el `rol` del grupo y en el `rol` de cada child).
- Mantener divider con `["admin", "director"]`.
- Grupo **Administración** (`rol: ["admin","director"]`):
  - `Usuarios` → `["admin", "director"]` (sin cambio).
  - `Información Institucional` → `["director"]` (quitar admin).
  - **NUEVO child** `Auditoría` → `rol: ["admin"]`, `ruta: "/admin/auditoria"`, `icon: "history"`.
- **No** crear un grupo raíz nuevo (debe seguir habiendo 6 grupos no-divider para no romper `test_navitems_grupos_raiz_seis`).
- Actualizar `tests/unit/interface/design/test_navitems.py`: añadir `/admin/auditoria` a `RUTAS_REQUERIDAS`. Si algún test asume que admin ve Aula/Académico, ajustarlo a la nueva matriz.

### T2 — Migrar guardas de página (quitar admin de lo académico/institucional)
En cada archivo, quitar `"admin"` de la guarda de acceso (`if ctx.usuario_rol not in (...)`) y de las constantes de rol del módulo (`_ROLES_VALIDOS`, `_ROL_ADMIN`, `_ROLES_PERMITIDOS`, `_ROLES_ESCRITURA`, `_ROLES_SELECTOR_VISTA`):

- `src/interface/pages/academico/estudiantes.py`
- `src/interface/pages/academico/registro_asistencia.py`
- `src/interface/pages/academico/tablero_estadisticos.py` (guarda + `es_directivo` local → `("director","coordinador")`)
- `src/interface/pages/academico/horarios_hub.py` (`_ROLES_ESCRITURA`, `_ROLES_SELECTOR_VISTA`)
- `src/interface/pages/admin/grupos.py` → `("director",)`
- `src/interface/pages/admin/asignaturas.py` → `("director",)`
- `src/interface/pages/admin/salas.py` → `("director",)`
- `src/interface/pages/admin/plan_estudios.py` → `("director","coordinador")`
- `src/interface/pages/admin/asignaciones.py` (guarda + `es_directivo` local)
- `src/interface/pages/admin/disponibilidad_docente.py` → `("director","coordinador")`
- `src/interface/pages/admin/configuracion_sie.py` (`_ROL_ADMIN` → `("director",)`)
- `src/interface/pages/admin/configuracion_institucion.py` → `("director",)`
- `src/interface/pages/evaluacion/cierre_periodo.py` (`_ROLES_PERMITIDOS` sin admin)
- `src/interface/pages/evaluacion/cierre_anio.py` (`_ROLES_PERMITIDOS` sin admin)
- `src/interface/pages/evaluacion/habilitaciones.py`
- `src/interface/pages/evaluacion/configuracion_evaluacion.py` (sigue solo profesor; sin cambio de guarda)
- `src/interface/pages/informes/boletin_periodo.py`
- `src/interface/pages/informes/boletin_anual.py`
- `src/interface/pages/informes/consolidado_notas.py`
- `src/interface/pages/informes/consolidado_asistencia.py`
- `src/interface/pages/informes/estadisticos.py`
- `src/interface/pages/convivencia/observaciones.py`
- `src/interface/pages/convivencia/comportamiento.py`
- `src/interface/pages/convivencia/notas_convivencia.py`

NO tocar `src/interface/pages/admin/usuarios.py` aquí (va en T4).

### T3 — Semántica "ver todo vs sólo lo mío" (es_admin → es_directivo)
En `src/interface/pages/evaluacion/planilla_notas.py` y `src/interface/pages/evaluacion/planes_mejoramiento.py`:
- El flag local `es_admin = ctx.usuario_rol in _ROL_ADMIN` se usa para decidir "ver todos los registros vs sólo los del usuario". Como admin ya no accede a estas páginas, renombrar la intención a `es_directivo = ctx.usuario_rol in ("director","coordinador")`. Mantener el comportamiento: directivos ven todo, profesor ve sólo lo suyo (`usuario_id = ctx.usuario_id`).

### T4 — usuarios.py: aprovisionamiento acotado
Archivo: `src/interface/pages/admin/usuarios.py`.
- Guarda de acceso: mantener `("admin", "director")`.
- `admin` SOLO puede crear rol `director`: `_roles_crear_admin = {"director": "Director"}`.
- `director` crea `{"coordinador": "Coordinador", "profesor": "Profesor"}` (sin cambio).
- Ajustar la validación de creación/cambio de rol (líneas ~98, ~156, ~168) para reflejar: admin no crea coordinador/profesor/admin; director no crea admin/director. Mensajes de error accionables.

### T5 — Vista de Auditoría (NUEVA) + ruta + re-export DTO
- **Re-export en service layer:** en `src/services/auditoria_service.py`, exponer para la UI (import + `__all__`): `FiltroAuditoriaDTO`, `RegistroCambio`, `EventoSesion`, `AccionCambio`, `TipoEventoSesion`. (Patrón igual a `usuario_service` que re-exporta `NuevoUsuarioDTO`/`FiltroUsuariosDTO`.) La página importa SOLO desde `src.services.auditoria_service`, nunca desde `src.domain.models`.
- **Nueva página:** `src/interface/pages/admin/auditoria.py`, ruta `@ui.page("/admin/auditoria")`, función `auditoria_page()`.
  - Guarda: `if not ctx: -> /login`; `if ctx.usuario_rol != "admin": toast_error("Acceso no autorizado"); -> /inicio`.
  - Solo lectura. Dos secciones (segmentos o tabs): **"Cambios"** (datos de `Container.auditoria_service().listar_cambios(FiltroAuditoriaDTO(...))`) y **"Sesiones"** (`listar_eventos_sesion(...)`).
  - Filtros: rango de fechas (`desde`/`hasta`), `usuario_id` opcional, `tabla`/`accion` (cambios), `tipo_evento` (sesiones); paginación con `pagina`/`por_pagina`.
  - Tabla con columnas legibles usando `timestamp_display`/`fecha_display`, `accion`, `tabla`, `tipo_evento`, etc. `empty_state` cuando no hay registros.
  - Patrón de UI: seguir `src/interface/pages/admin/usuarios.py` e `inicio.py`. Usar `app_layout(ctx, contenido, page_titulo="Auditoría", page_icono="history", ...)`. Respetar TODAS las prohibiciones del implementer (sin `.dict()`, `ThemeManager.icono()`, clases CSS del design system, sin estilos estáticos sin `# DYNAMIC`, etc.).
- **Ruta en `main.py`:** registrar `/admin/auditoria` con el guard de autenticación estándar (igual que las demás páginas admin), importando `auditoria_page`.

### T6 — Verificación y cierre
- `python init.py` debe terminar **verde** (baseline previa: 920 passed, 1 skipped). Corregir TODO el fallout de tests que asumían acceso de admin a páginas académicas (actualizarlos a la nueva matriz de roles; NO debilitar las guardas para que pasen tests viejos).
- `python scripts/check_design.py --file src/interface/pages/admin/auditoria.py` exit 0.
- `python scripts/check_imports.py --layer interface` exit 0.
- Escribir `progress/impl_paso_20.md` con archivos tocados, tabla de verificación por tarea, decisiones de diseño de la vista de auditoría, y el output de `python init.py`.
- Devolver solo la referencia al archivo de progreso (no el contenido completo).

## criterio_done
`python init.py` verde; admin no aparece en NAV de Aula/Académico/Evaluación/Informes; las guardas académicas/institucionales rechazan admin; admin solo crea director; existe y funciona `/admin/auditoria` (solo lectura, admin exclusivo); check_design/check_imports verdes. SIN impersonación (paso_21).
