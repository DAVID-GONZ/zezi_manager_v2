# chip_01 — Componente inline_selectors

> Referencia completa: `specs/chip_inline_00_roadmap/chip_01_inline_selectors.md`

## Archivos a crear

| Archivo | Acción |
|---------|--------|
| `src/interface/design/components/inline_selectors.py` | CREAR |
| `src/interface/design/styles/components/inline_selectors.css` | CREAR |
| `src/interface/design/styles/main.css` | MODIFICAR — agregar @import |
| `tests/unit/interface/test_inline_selectors.py` | CREAR |

## Tasks

- [ ] T1 — Crear `inline_selectors.css` con las clases `.inline-sel-row` y `.inline-sel-pill` (con variantes `:hover`, `.sel-active`, `:disabled`). Importarlo en `main.css`. Verificar con `check_design.py` sobre cualquier archivo que lo use.

- [ ] T2 — Implementar lógica pura (sin render NiceGUI) en `inline_selectors.py`:
  - Función `_estado_inicial(s)` que garantiza las claves `sel_periodo_id/nombre`, `sel_grupo_id/nombre`, `sel_asignacion_id/nombre` en `s` si no existen.
  - Función `_preseleccionar_periodo(s, institucion_id)` que carga periodos del año en curso, filtra el primero con `estado == 'abierto'` y lo escribe en `s`. Si no hay abierto, no escribe nada.
  - Función `_on_periodo_cambio(s, periodo_id, periodo_nombre)` que setea `sel_periodo_id/nombre` y limpia `sel_grupo_id/nombre/sel_asignacion_id/nombre`.
  - Función `_on_grupo_cambio(s, grupo_id, grupo_nombre)` que setea `sel_grupo_id/nombre` y limpia `sel_asignacion_id/nombre`.
  - Función `_on_asignacion_cambio(s, asig_id, asig_nombre)` que setea `sel_asignacion_id/nombre`.
  - Función `_seleccion_completa_3d(s)` → True si los 3 valores no son None.
  - Función `_seleccion_completa_2d(s)` → True si periodo_id y grupo_id no son None.

- [ ] T3 — Implementar render NiceGUI en `inline_selectors.py`:
  - `inline_periodo_grupo_asignatura(s, on_change, usuario_id, institucion_id, usuario_rol, preselect_periodo=True)`:
    - Llama `_estado_inicial(s)`.
    - Si `preselect_periodo=True`, llama `_preseleccionar_periodo(s, institucion_id)`.
    - Renderiza `div.inline-sel-row` con 3 pills: periodo, grupo, asignatura.
    - Cada pill es `ui.button(text, on_click=...)` con clase `inline-sel-pill` (+ `sel-active` si tiene valor).
    - Cada pill abre un `ui.menu` con `ui.menu_item` por opción.
    - Pill grupo: deshabilitado si `sel_periodo_id` es None. Carga grupos desde `Container.infraestructura_service().listar_grupos_por_periodo(periodo_id)`. Si `usuario_rol == "profesor"`, filtra grupos donde el usuario tiene asignaciones activas.
    - Pill asignatura: deshabilitado si `sel_grupo_id` es None. Carga desde `Container.catalogo_academico_service().listar_asignaciones_por_grupo_periodo(grupo_id, periodo_id)`. Si `usuario_rol == "profesor"`, filtra por `usuario_id`.
    - `on_change` se llama solo cuando `_seleccion_completa_3d(s)` es True.
  - `inline_periodo_grupo(s, on_change, institucion_id, preselect_periodo=True)`:
    - Igual pero solo 2 pills (sin asignatura).
    - `on_change` se llama cuando `_seleccion_completa_2d(s)` es True.
  - Exportar ambas funciones en `__init__.py` del package de components.

- [ ] T4 — Escribir tests unitarios en `tests/unit/interface/test_inline_selectors.py`. Los tests verifican lógica pura (NO render NiceGUI). Usar mocks para los servicios del Container.
  - `test_preselect_false_no_modifica_s` — Con `preselect_periodo=False`, `s` permanece vacío
  - `test_preselect_true_selecciona_primer_abierto` — Primer periodo abierto se asigna a `s["sel_periodo_id"]`
  - `test_preselect_true_sin_abiertos_deja_none` — Sin periodos abiertos, `s["sel_periodo_id"]` queda None
  - `test_cambio_periodo_limpia_grupo_y_asignacion` — `_on_periodo_cambio` pone grupo y asignacion a None
  - `test_cambio_grupo_limpia_asignacion` — `_on_grupo_cambio` pone asignacion a None
  - `test_on_change_solo_cuando_completa_3d` — `_seleccion_completa_3d` retorna False con solo periodo
  - `test_on_change_solo_cuando_completa_2d` — `_seleccion_completa_2d` retorna True con periodo+grupo

- [ ] T5 — Verificación final:
  - `python -X utf8 init.py` completamente verde
  - `python scripts/check_imports.py --layer interface` sin errores
  - `python -m pytest tests/unit/interface/test_inline_selectors.py -v` — 7 tests verdes
  - Ninguna página existente modificada

## Restricciones críticas

- ❌ No usar `ui.select` nativo — pills deben ser `ui.button` + `ui.menu`
- ❌ No escribir a `SessionContext`
- ❌ No importar desde `src.domain` directamente — solo vía `Container`
- ❌ No apilar 3+ clases atómicas Tailwind — usar las clases semánticas de `.inline-sel-pill`
- ✅ CSS en `inline_selectors.css`, no inline
- ✅ Los pills usan `ThemeManager.icono("expand_more")` para el chevron

## Notas de implementación

### Cómo obtener el año activo para la pre-selección de periodo

```python
import datetime
anio_actual = datetime.date.today().year
# Luego buscar el año en la BD:
# Container.infraestructura_service().listar_anios_lectivos()
# o usar Container.periodo_service().listar_por_anio(anio_id) si hay método que resuelva por año calendario
```

Si no hay un método que resuelva año calendario → anio_id directamente, usar
`Container.periodo_service().listar_activos()` o el método equivalente que devuelva
periodos del año en curso. Verificar la firma real antes de llamar.

### Pill con valor vs. sin valor

```
Sin valor:   [  Seleccionar periodo  ▾ ]   → clase inline-sel-pill (sin sel-active)
Con valor:   [  2025-1  ▾ ]                → clase inline-sel-pill sel-active
Deshabilitado: pill siguiente sin periodo  → atributo disabled en el button
```

### Orden de @ui.refreshable

Definir los `@ui.refreshable` ANTES de los handlers que los llaman.
