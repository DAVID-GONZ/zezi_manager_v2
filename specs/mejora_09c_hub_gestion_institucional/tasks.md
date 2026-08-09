# Tasks: mejora_09c — Hub editable de gestión institucional

**Fase 3 de 3.** Prerrequisitos: mejora_09a ✓ y mejora_09b ✓.

**Declara scope completo desde el inicio** (lección de 09b/check_scope):
- `src/interface/pages/institucion/hub_institucion.py` (nuevo)
- `src/interface/pages/institucion/__init__.py` (nuevo, si el directorio no existe)
- `src/interface/pages/admin/configuracion_institucion.py` (eliminado)
- `src/interface/design/layout.py`
- `main.py`
- `src/services/institucion_service.py` (posible ampliación de `__all__`)
- `tests/unit/interface/test_hub_institucion_smoke.py` (nuevo)

Puede que se necesite un CSS auxiliar (`src/interface/design/styles/pages/hub_institucion.css`)
si `check_design.py` lo exige — decisión del implementer, añadir al scope si aplica.

---

## T1 — Página hub: esqueleto con tabs y prefill

**Archivo nuevo:** `src/interface/pages/institucion/hub_institucion.py`
**Ruta lógica:** `/institucion/configuracion` (registrada en T6).

- `# page-delegate` en la línea previa a `def hub_institucion_page()`.
- Reconstruir `ctx = SessionContext.desde_storage()`; si `None` → `/login`.
- Layout: `app_layout(ctx, contenido, page_titulo="Configuración institucional",
  page_subtitulo="Identidad, preferencias, módulos y apariencia",
  page_icono="settings")`.
- **Estado** (dict `_s`): un sub-diccionario por sección (`identidad`,
  `preferencias`, `modulos`, `apariencia`), con las claves del formulario.
- **Prefill** en `_cargar_estado()`:
  - `inst = Container.institucion_service().get(ctx.institucion_id)`
  - `prefs = Container.preferencias_service().get_dto(ctx.institucion_id)`
  - Poblar los sub-dicts con los valores actuales.
- **Tabs**: `ui.tabs()` con las 4 tabs, `ui.tab_panels(...)` con cada panel
  refrescable por sección (usar `@ui.refreshable` por sección para poder
  recargar una sin resetear el resto).
- **Reglas de capas**: NO importar `src.domain.models.*`. DTOs y enums desde
  módulos de servicio (patrón `catalogo_instituciones.py`,
  `configuracion_inicial.py`).

---

## T2 — Sección Identidad

Dentro de la página T1, implementar el panel de la tab "Identidad":

- **Prefill**: valores actuales de la entidad `Institucion`.
- **Campos** (grid 2 columnas, patrón de la página vieja):
  - Obligatorios: `nombre`, `nombre_oficial`, `rector`, `municipio`.
  - Opcionales: `codigo_dane` (12 dígitos, valida el DTO/modelo), `nit`,
    `direccion`, `telefono`, `email_institucional`, `resolucion_aprobacion`,
    `lema`, `jornada_principal` (select AM/PM/UNICA), `tipo_institucion`
    (publica/privada), `calendario` (A/B).
  - **Sin campo de logo** (memoria [[logo-gestion-imagenes-diferida]]).
- **Selects de enum**: si el import de `JornadaPrincipal`/`TipoInstitucion`/
  `Calendario` desde `institucion_service` no está expuesto en `__all__`, o
  bien:
  (a) ampliar `institucion_service.__all__` con esos enums (preferido —
      mínima fricción), o
  (b) resolver los selects con strings crudos y dejar que el DTO valide.
  Documentar la decisión en `progress/impl_mejora_09c.md`.
- **Botón "Guardar cambios"** → construye `ActualizarInstitucionDTO(...)` con
  los campos del panel, invoca `Container.institucion_service().actualizar(
  ctx.institucion_id, dto)`, `toast_success` en éxito, `toast_warning(str(exc))`
  en `ValueError`, `toast_error` en excepción genérica (log + no bloquear UI).
- **Botón "Recargar"** ghost: re-lee y refresca solo esta sección.

---

## T3 — Sección Preferencias académicas

Dentro de la página T1, panel de la tab "Preferencias":

- **Prefill**: `PreferenciasDTO` (defaults del design system heredados si no hay
  valor en BD; mejora_08 los garantiza).
- **Campos** (4):
  - `nota_minima_aprobacion_default` (float, `ui.number` step=0.1)
  - `nota_minima_escala_default` (float)
  - `nota_maxima_escala_default` (float)
  - `numero_periodos_default` (int, `ui.number` step=1)
- **Validación UI mínima antes de persistir**: `min_escala < max_escala` y
  `min_escala ≤ aprobacion ≤ max_escala`. Si falla → `toast_warning` explicativo
  sin persistir.
- **Persistencia**: `Container.preferencias_service().set(ctx.institucion_id,
  ActualizarPreferenciaDTO(clave=..., valor=str(...)))` por clave. Envolver los
  4 sets en un `try/except ValueError` (idempotente y trivial).

---

## T4 — Sección Módulos

Panel de la tab "Módulos":

- **Prefill**: `PreferenciasDTO.modulo_convivencia_activo` y `.modulo_alertas_activo`.
- **Campos**: 2 `ui.switch` con labels claros.
- **Texto explicativo**: "Al desactivar convivencia, sus páginas y su ítem de
  NAV se ocultan hasta reactivarlo."
- **Persistencia**: dos `preferencias_service.set(...)` con `valor="true"/"false"`.
- **Nota UX**: los cambios de visibilidad del NAV/rutas los aplica el guard en
  el próximo request; no requiere reload manual (el usuario los verá al navegar).

---

## T5 — Sección Apariencia

Panel de la tab "Apariencia":

- **Prefill**: `PreferenciasDTO.color_primario` (`"#2E3192"`) y
  `.color_secundario` (`"#8B90F0"`). El DTO **garantiza** valor no-None para
  claves conocidas (fix del bug UX anotado en el review de 09b).
- **Campos**: `ui.color_input(value=prefs.color_primario)` y
  `ui.color_input(value=prefs.color_secundario)`.
- **Texto de ayuda**: "Los cambios de color se aplican al recargar la
  aplicación."
- **Persistencia**: dos `preferencias_service.set(...)` con el hex string.
- **Sin hex literales sueltos en el JSX/HTML**: los defaults van vía el DTO
  (permitidos como valor de configuración, no como clase CSS inline). Pasar
  `check_design.py`.

---

## T6 — Navegación, ruta y eliminación de la página vieja

**`main.py`:**
- Importar `hub_institucion_page` desde el nuevo módulo.
- `registrar_pagina("/institucion/configuracion", hub_institucion_page,
  roles={Rol.DIRECTOR})`.
- **Eliminar** el bloque de import y `registrar_pagina` de la ruta antigua
  `/admin/configuracion-institucion`.

**`src/interface/design/layout.py`:**
- Reemplazar el ítem NAV en `layout.py:188-190`:
  ```python
  {"label": "Configuración institucional", "icon": "settings",
   "ruta": "/institucion/configuracion", "rol": ["director"]}
  ```
  (Icono `settings` o `business` — el implementer elige el que encaje
  visualmente con el resto del NAV del director; documentar.)

**Archivo eliminado:**
- `src/interface/pages/admin/configuracion_institucion.py` — `git rm`.
- Verificar que ningún otro módulo lo importa (grep previo).

**No se toca** `configuracion_service.actualizar_info_institucional` (queda
para casos legacy; ver design.md §1).

---

## T7 — Tests + verificación

**Archivo nuevo:** `tests/unit/interface/test_hub_institucion_smoke.py`
- Test 1: `from src.interface.pages.institucion.hub_institucion import
  hub_institucion_page` (import sin error).
- Test 2: `assert callable(hub_institucion_page)`.
- Test 3 (opcional): regex/AST sobre el archivo del hub confirmando que NO
  contiene `from src.domain.models` (refuerzo del linter general).

**Regresión:**
- Correr `pytest tests/unit/interface/auth/test_route_guard.py` — la matriz de
  rutas se regenera con el conftest; verificar 0 fallos por la ruta eliminada.
- Correr los tests de `institucion_service` y `preferencias_service` — no
  deberían cambiar (llamadas ya cubiertas).

**Linters obligatorios:**
- `python scripts/check_scope.py` → 0 (declarar TODO el scope en
  `step_list.json.destino_v2` **antes** de tocar código).
- `python scripts/check_imports.py --layer interface` → 0.
- `python scripts/check_design.py --file
  src/interface/pages/institucion/hub_institucion.py` → 0.
- `python scripts/check_tasks.py` → 0.

**Verificación final:**
```
$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/ -q --tb=short
$env:PYTHONIOENCODING="utf-8"; python init.py
```
0 failed, `init.py` completamente verde (09b dejó incluso el falso positivo
`login.py:16` corregido — mantener así).

Escribir `progress/impl_mejora_09c.md` (archivos creados/eliminados/modificados,
decisión sobre enums en `__all__` de `institucion_service`, decisión sobre CSS
auxiliar, decisión sobre icono NAV).

---

## Riesgos / notas para el implementer

- **Scope declarado ANTES de codificar**: la lección de 09b es que
  `check_scope.py` compara `git diff HEAD` contra `destino_v2`; si aparecen
  archivos no declarados el reviewer rechaza. Coordinar con el leader para
  añadir cualquier archivo extra al scope **antes** de que aparezca en el diff.
- **Ruta eliminada**: `/admin/configuracion-institucion` sale del registro y del
  NAV. Buscar referencias externas (docs, tests, otros pages) antes de borrar
  el archivo. Si hay algún link duro, actualizarlo.
- **Ítem NAV con la misma posición**: el reemplazo mantiene la misma posición
  visual (línea `layout.py:188-190`); no reordenar el resto.
- **Fix del color_input**: `ui.color_input(value=prefs.color_primario)` debe
  abrir el picker con el color prefijado (a diferencia del wizard de 09b, que
  lo dejaba vacío). Verificar visualmente si `run.py` está disponible; si no,
  documentar como "requiere verificación manual".
- **Regla dura**: NO importar `src.domain.models.*` en la página. Los enums
  del select (`JornadaPrincipal`/`TipoInstitucion`/`Calendario`) deben venir
  del módulo de servicio, o usar strings crudos. Elegir y documentar.
- **Snapshot de años cerrados**: no se toca `configuracion_service
  .actualizar_info_institucional`; los snapshots por año siguen leyéndose desde
  ahí para boletines. El hub solo escribe en la entidad `Institucion` (fuente
  única desde mejora_06).
