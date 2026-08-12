# convivencia_23_observaciones_creacion — Spec

## Contexto

`observaciones.py` hoy hace tres cosas: crear observaciones, mostrar un grid de
estudiantes con contadores (`panel_grid`) y listar/gestionar observaciones
(`panel_obs_lista`). Debe quedar como **superficie de creación pura**. La
visualización (contadores + lista gestionable) se reubica al hub de Seguimiento
(convivencia_25). Además, por decisión de David, la **creación de registros de
comportamiento** (fortaleza/dificultad/…) se mueve aquí desde `comportamiento.py`,
gated a director de grupo/coordinación/dirección.

Scope: `src/interface/pages/convivencia/observaciones.py` (MODIFICAR).

## Requisitos (EARS)

- **R1** — La página DEBE permitir crear observaciones para uno o más estudiantes
  seleccionados (todos los profes, sobre sus asignaciones — RBAC ya en el servicio).
- **R2** — La página DEBE ofrecer "Nuevo registro de comportamiento" SOLO cuando el
  usuario está autorizado sobre el grupo (director de grupo/coord/dir).
- **R3** — La página NO DEBE listar ni gestionar observaciones existentes (eso vive
  en Seguimiento). Se elimina `panel_obs_lista` y las acciones de gestión.
- **R4** — Se conserva un **selector mínimo de estudiantes** para la creación (no se
  elimina la capacidad de elegir a quién aplicar).

## Diseño

**Conservar:**
- Selector `inline_periodo_grupo_asignatura` (contexto periodo/grupo/asignatura).
- Grid de selección de estudiantes reducido a picker: columnas `checkbox` +
  `nombre_completo`. Quitar columnas `num_obs` y `ultima_fecha` (visualización → Seguimiento).
- `_crear_observacion`, `_abrir_crear_observacion`, flujo de plantillas
  (`_abrir_selector_plantilla`, `_cargar_plantillas`), `_cargar_categorias`.

**Eliminar:**
- `panel_obs_lista` y todo su render.
- `_cargar_observaciones`, `_construir_filas_obs`, `_construir_filas_grid` (contadores),
  `_toggle_visibilidad`, `_promover_a_plantilla`, `_promover_a_comportamiento`,
  `_eliminar_observacion`, `on_categoria_change`, `_texto_truncado`, `_nombre_estudiante`
  (si dejan de usarse), y las claves de estado `observaciones`/`sel_categoria_id`.
- `_actualizar_datos_en_sitio` se simplifica a refrescar solo el picker tras crear.

**Añadir (migrado de `comportamiento.py`):**
- `_TIPOS_DISPLAY`, `_autorizado_para_grupo(ctx, grupo_id)`.
- `_abrir_crear_registro` / `_crear_registro` (form `NuevoRegistroComportamientoDTO`
  vía `Container.convivencia_service().registrar_comportamiento(...)`), usando el
  estudiante seleccionado y el grupo/periodo del contexto.
- Botón "Nuevo registro de comportamiento" en la toolbar, visible solo si
  `_autorizado_para_grupo(...)`.
- Import `NuevoRegistroComportamientoDTO` (y `TipoRegistro` si hace falta) vía el módulo de servicios.

## Tareas

- **T1** — Reducir el grid a picker (quitar columnas de visualización).
- **T2** — Eliminar `panel_obs_lista` y todos los helpers/handlers de listado/gestión.
- **T3** — Migrar el form de registro de comportamiento + gating + botón en toolbar.
- **T4** — Simplificar estado y `contenido()` (dos refreshables → uno si aplica).

## Verificación
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/convivencia/observaciones.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```
Crear observación (multi-estudiante) funciona; "Nuevo registro" solo aparece gated;
sin listado de observaciones; check_design del archivo verde; init.py verde.
