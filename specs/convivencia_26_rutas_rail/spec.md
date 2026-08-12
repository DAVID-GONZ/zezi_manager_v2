# convivencia_26_rutas_rail — Spec

## Contexto

El rail de menú está desalineado semánticamente: la etiqueta "Seguimiento" apunta a
`/convivencia/notas`, y la página real de seguimiento aparece como "Alertas
Seguimiento" (`/convivencia/seguimiento`). Además, tras la reorganización,
`comportamiento` deja de ser una página propia (su lectura vive en el hub de
Seguimiento; su creación, en Observaciones). Este paso corrige rutas y rail y retira
`comportamiento`.

Scope: `main.py`, `src/interface/design/layout.py` (`NAV_ITEMS`),
`src/interface/pages/convivencia/comportamiento.py` (redirect),
`tests/unit/interface/design/test_navitems.py`.

## Requisitos (EARS)

- **R1** — `/convivencia/seguimiento` DEBE ser accesible por todos los roles de aula
  (`_AULA`), no solo dir/coord.
- **R2** — El rail DEBE mapear cada etiqueta a su ruta correcta:
  Notas de convivencia → `/convivencia/notas`; Observaciones → `/convivencia/observaciones`;
  Seguimiento → `/convivencia/seguimiento`; Categorías → `/convivencia/categorias`;
  Plantillas → `/convivencia/plantillas`; Reporte de periodo → `/convivencia/reporte-periodo`.
- **R3** — `/convivencia/comportamiento` DEBE redirigir a `/convivencia/seguimiento`
  (compatibilidad de enlaces existentes).
- **R4** — Los permisos por rol se conservan o se documentan; el test de rutas del
  rail DEBE seguir pasando.

## Diseño

### `main.py` (~L271-277)
- `registrar_pagina("/convivencia/seguimiento", seguimiento_page, roles=_AULA)`
  (cambia de `_DIR_COORD` a `_AULA`).
- Retirar `/convivencia/comportamiento`, o registrarlo con un delegate mínimo
  `comportamiento_page` que haga `ui.navigate.to("/convivencia/seguimiento")`.

### `src/interface/design/layout.py` — `NAV_ITEMS` (hijos de "Aula")
- `Observaciones` → `/convivencia/observaciones` (icon `edit_note`).
- `Notas de convivencia` → `/convivencia/notas` (icon `grade`).
- `Seguimiento` → `/convivencia/seguimiento` (icon `insights`), rol
  `["director","coordinador","profesor"]`.
- `Categorías` / `Plantillas` (dir/coord) — sin cambios de ruta.
- `Reporte de periodo` → `/convivencia/reporte-periodo` (nuevo ítem, `_AULA`).
- Eliminar los ítems "Comportamiento" y "Alertas Seguimiento".

### `comportamiento.py`
- Reducir a delegate de redirect: `comportamiento_page()` → guard de sesión →
  `ui.navigate.to("/convivencia/seguimiento")`. (No eliminar el símbolo para no
  romper el import de `main.py`; o eliminar el import y la ruta a la vez.)

### `test_navitems.py`
- Actualizar el conjunto esperado de rutas/labels de convivencia.

## Tareas

- **T1** — `main.py`: `_AULA` en seguimiento; retiro/redirect de comportamiento.
- **T2** — `NAV_ITEMS`: etiquetas→rutas correctas, añadir Reporte, quitar
  Comportamiento y Alertas Seguimiento.
- **T3** — `comportamiento.py` → delegate de redirect.
- **T4** — Actualizar `test_navitems.py`.

## Verificación
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/interface/design/test_navitems.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```
Rail semántico; `/convivencia/seguimiento` es `_AULA`; `/convivencia/comportamiento`
redirige; test de rutas del rail pasa; init.py verde. Smoke por los 4 roles.
