# paso_25 — UI de instituciones en /admin/usuarios + limpieza del topbar

## Contexto y decisión (David)

Cerrar el frente multi-tenant por el lado de la UI y limpiar la página de usuarios:
1. **Crear/listar instituciones dentro de `/admin/usuarios`** (no una página aparte). Acción exclusiva de **admin** (rol de plataforma). El modelo/servicio `Institucion` ya existen (paso_24); falta la UI.
2. **Quitar el chip de contexto** (selector año/periodo/grupo/asignatura del topbar) en esta página — es irrelevante para gestión de usuarios.
3. **Sacar el botón "Nuevo usuario" del topbar** y moverlo al cuerpo de la página.

Alcance acotado: solo `layout.py` (flag para ocultar el chip), `institucion_service.py` (re-export de DTOs) y `usuarios.py` (UI). No tocar lógica de negocio ni schema.

## Tareas

### T1 — Flag para ocultar el chip de contexto en el layout
- En `src/interface/design/layout.py`: añadir parámetro `mostrar_contexto: bool = True` a `app_layout(...)` y propagarlo a `_topbar(...)`.
- En `_topbar`, el `context_chip(...)` solo se renderiza si `ctx is not None` **and** `mostrar_contexto`. Default `True` → **ninguna otra página cambia**.

### T2 — Re-export de DTOs de institución en la capa de servicio
- En `src/services/institucion_service.py`: añadir `NuevaInstitucionDTO` e `InstitucionResumenDTO` a los imports ya presentes y a `__all__`, para que la página los importe SOLO desde `src.services.institucion_service` (nunca desde `src.domain.models`). Patrón igual a `usuario_service` (`NuevoUsuarioDTO`/`FiltroUsuariosDTO`).

### T3 — UI en /admin/usuarios
- **Quitar el "Nuevo usuario" del topbar:** ya no pasar `page_acciones` a `app_layout`; pasar `mostrar_contexto=False`.
- **Mover "Nuevo usuario" al cuerpo:** botón (componente del design system, p.ej. `btn_primary` con `person_add`) en la barra de herramientas del panel de usuarios (junto a los filtros), que abre el mismo `_abrir_crear_usuario` actual. Visible según `puede_crear` (igual que hoy).
- **Panel "Instituciones" (solo admin):** nueva sección en el cuerpo, ANTES o DESPUÉS del panel de usuarios:
  - Lista las instituciones con `Container.institucion_service().listar()` (nombre, estado activa). `empty_state` si no hay.
  - Botón **"Nueva institución"** → `form_dialog` con los campos de `NuevaInstitucionDTO` (al menos nombre; nit/código si el DTO los tiene — verificar firma) → `Container.institucion_service().crear(dto)` → toast + refrescar la lista.
  - Toda la sección gated por `es_admin` (el director no ve ni crea instituciones).
- Respetar prohibiciones del design system (ThemeManager.icono, clases CSS, sin colores quemados, sin `.style` estático sin `# DYNAMIC`, no importar `src.domain.models`, `Container.*_service()` no `*_repo()`).

### T4 — Verificación y cierre
- `python init.py` VERDE (baseline 1074 passed, 1 skipped; corregir fallout — atención a tests que invoquen `app_layout` por la nueva firma, aunque el default la mantiene compatible). `python scripts/check_design.py --file src/interface/pages/admin/usuarios.py` y `--file src/interface/design/layout.py` exit 0; `check_imports --layer interface` y `--layer services` exit 0.
- `progress/impl_paso_25.md`.

## criterio_done
En `/admin/usuarios`: el chip de contexto no aparece, no hay "Nuevo usuario" en el topbar (está en el cuerpo), y existe un panel (solo admin) para listar y crear instituciones usando `InstitucionService`. El flag `mostrar_contexto` no altera ninguna otra página. `python init.py` verde; check_design/check_imports verdes.
