# convivencia_33_config_unificada_y_renombre — Spec

## Contexto

Las paginas de Categorias y Plantillas son dos CRUD independientes con layout
identico. David quiere fusionarlas en una vista side-by-side (categorias a la
izquierda, plantillas a la derecha) accesible a todos los roles de aula, donde
los profesores pueden crear/editar plantillas pero no categorias (solo dir/coord).
Ademas, los labels del rail no coinciden con los `page_titulo` de varias paginas
de convivencia, y el checkbox `es_publica` necesita un label mas claro.

Scope: `src/services/convivencia_service.py`,
`src/interface/pages/convivencia/configuracion_convivencia.py` (nuevo),
`src/interface/pages/convivencia/categorias.py`,
`src/interface/pages/convivencia/plantillas.py`,
`src/interface/pages/convivencia/observaciones.py`,
`src/interface/pages/convivencia/seguimiento.py`,
`src/interface/pages/convivencia/reporte_periodo.py`,
`src/interface/pages/convivencia/_shared_observacion_form.py`,
`src/interface/design/layout.py`, `main.py`,
`src/interface/auth/route_guard.py`.

## Requisitos (EARS)

- **R1** — `crear_plantilla()` y `actualizar_plantilla()` DEBEN aceptar
  `usuario_rol="profesor"` sin lanzar `PermissionError`.
- **R2** — `desactivar_plantilla()` DEBE seguir rechazando `usuario_rol="profesor"`.
- **R3** — La pagina `/convivencia/configuracion` DEBE renderizar dos columnas
  side-by-side usando `page-body` + `page-col-side` (categorias, flex:2) +
  `page-col-main` (plantillas, flex:3).
- **R4** — Un profesor que accede a `/convivencia/configuracion` NO DEBE ver la
  columna de categorias; DEBE poder crear y editar plantillas; NO DEBE ver el
  boton "Desactivar" en plantillas.
- **R5** — Un director/coordinador DEBE ver ambas columnas y tener CRUD completo
  en categorias y plantillas (incluida desactivacion).
- **R6** — `/convivencia/categorias` y `/convivencia/plantillas` DEBEN redirigir a
  `/convivencia/configuracion` (compatibilidad).
- **R7** — El label de cada entrada en `NAV_ITEMS` DEBE coincidir exactamente con
  el `page_titulo` de la pagina destino:

  | Label del rail (= page_titulo) | Ruta |
  |---|---|
  | Observador del estudiante | `/convivencia/observaciones` |
  | Notas de convivencia | `/convivencia/notas` |
  | Seguimiento de convivencia | `/convivencia/seguimiento` |
  | Configuracion de convivencia | `/convivencia/configuracion` |
  | Reporte de convivencia | `/convivencia/reporte-periodo` |

- **R8** — Las entradas "Categorias" y "Plantillas" DEBEN eliminarse de `NAV_ITEMS`.
- **R9** — `/convivencia/configuracion` DEBE aparecer en `RUTAS_POR_MODULO["convivencia"]`.
- **R10** — El label del checkbox `es_publica` en `_shared_observacion_form.py` DEBE
  ser `"Incluir en el boletin"` (no `"Publica? (aparece en boletin)"`).

## Diseno

### T1 — Servicio: RBAC de plantillas (`convivencia_service.py`)

Metodos a cambiar:
- `crear_plantilla()` (~L1156): tupla de roles `("director", "coordinador")` →
  `("director", "coordinador", "profesor")`.
- `actualizar_plantilla()` (~L1172): mismo cambio.
- `desactivar_plantilla()`: sin cambio (solo dir/coord).

### T2 — Nueva pagina combinada (`configuracion_convivencia.py`)

Archivo nuevo en `src/interface/pages/convivencia/`.

**Imports**: `Container`, `SessionContext`, `form_dialog`, `confirm_dialog`,
`empty_state`, `status_badge`, `toast_*`, `btn_primary`, `btn_icon`, `btn_danger`,
`app_layout`, `Icons`. DTOs via servicio: `NuevaCategoriaDTO`, `NuevaPlantillaDTO`.

**Estado** (`_s`):
```python
{
    "categorias": [],
    "plantillas": [],
    "editando_cat": None,
    "editando_plt": None,
}
```

**Layout**: `page-stack` > `page-body` > `page-col-side` (categorias) + `page-col-main` (plantillas).

- Columna categorias: `if rol in ("director", "coordinador"):` renderizar panel-card
  con toolbar ("Nueva categoria") + config-list table (Nombre, Tipo badge, Estado badge,
  Acciones). Handlers: `_abrir_crear_cat`, `_abrir_editar_cat`, `_desactivar_cat`.
- Columna plantillas: siempre visible. Toolbar con "Nueva plantilla". Config-list table
  (Texto truncado 75 chars, Categoria badge, Usos, Estado badge, Acciones). El boton
  "Desactivar" solo se renderiza si `rol in ("director", "coordinador")`. Handlers:
  `_abrir_crear_plt`, `_abrir_editar_plt`, `_desactivar_plt`.

**Coordinacion de refresh**: un solo `@ui.refreshable _contenido()` que renderiza ambas
columnas. Al mutar una categoria, se refresca todo (las plantillas muestran nombre de
categoria).

**page_titulo**: `"Configuracion de convivencia"`.
**Export**: `__all__ = ["configuracion_convivencia_page"]`.

### T3 — Redirect de rutas antiguas

- `categorias.py`: reemplazar cuerpo por guard de sesion + `ui.navigate.to("/convivencia/configuracion")`.
- `plantillas.py`: idem.
  Patron identico a `comportamiento.py`.

### T4 — Rutas y navegacion

**main.py**:
- Importar `configuracion_convivencia_page`.
- `registrar_pagina("/convivencia/configuracion", configuracion_convivencia_page, roles=_AULA)`.

**route_guard.py** — `RUTAS_POR_MODULO`:
- Anadir `"/convivencia/configuracion"` a la lista `"convivencia"`.

**layout.py** — `NAV_ITEMS` (hijos de "Aula"):
- Eliminar entradas "Categorias" y "Plantillas".
- Anadir entrada `{"label": "Configuracion de convivencia", "icon": "settings", "ruta": "/convivencia/configuracion", "rol": ["director", "coordinador", "profesor"], "requiere_modulo": "convivencia"}`.
- Renombrar labels existentes:
  - `"Observaciones"` → `"Observador del estudiante"`
  - `"Seguimiento"` → `"Seguimiento de convivencia"`
  - `"Reporte de periodo"` → `"Reporte de convivencia"`

### T5 — Titulos de pagina (page_titulo)

- `observaciones.py`: `page_titulo="Observaciones"` → `page_titulo="Observador del estudiante"`.
- `seguimiento.py`: `page_titulo="Seguimiento"` → `page_titulo="Seguimiento de convivencia"`.
- `reporte_periodo.py`: `page_titulo="Reporte de convivencia por periodo"` → `page_titulo="Reporte de convivencia"`.
- `notas_convivencia.py`: sin cambio (ya coincide).

### T6 — Label es_publica

- `_shared_observacion_form.py`: `"label": "¿Publica? (aparece en boletin)"` →
  `"label": "Incluir en el boletin"`.

## Tareas

- [x] **T1** — `convivencia_service.py`: ampliar tupla de roles en `crear_plantilla` y `actualizar_plantilla` para incluir `"profesor"`.
  Verificacion: `python -c "from src.services.convivencia_service import ConvivenciaService; print('OK')"`

- [x] **T2** — Crear `configuracion_convivencia.py`: pagina side-by-side con categorias (dir/coord) y plantillas (todos). CRUD completo, guards por rol dentro de la pagina.
  Verificacion: `python scripts/check_imports.py --layer interface`, `python scripts/check_design.py --file src/interface/pages/convivencia/configuracion_convivencia.py` ✅

- [x] **T3** — Convertir `categorias.py` y `plantillas.py` a redirects a `/convivencia/configuracion`.
  Verificacion: `python scripts/check_imports.py --layer interface` ✅

- [x] **T4** — `main.py`: registrar ruta `/convivencia/configuracion`. `route_guard.py`: anadir a `RUTAS_POR_MODULO`. `layout.py`: eliminar Categorias/Plantillas, anadir Configuracion de convivencia, renombrar Observaciones/Seguimiento/Reporte.
  Verificacion: `python -m pytest tests/unit/interface/design/test_navitems.py -q` → 8 passed ✅

- [x] **T5** — Actualizar `page_titulo` en `observaciones.py`, `seguimiento.py`, `reporte_periodo.py`.
  Verificacion: visual (rail label = titulo en topbar)

- [x] **T6** — Cambiar label `es_publica` en `_shared_observacion_form.py`.
  Verificacion: visual (checkbox dice "Incluir en el boletin")

## Verificacion final

```
PYTHONIOENCODING=utf-8 python scripts/check_imports.py --layer interface
PYTHONIOENCODING=utf-8 python scripts/check_design.py --file src/interface/pages/convivencia/configuracion_convivencia.py
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/interface/design/test_navitems.py -q
PYTHONIOENCODING=utf-8 python init.py
```

Vista combinada funcional por roles; labels rail = page_titulo; redirects operando;
es_publica con label claro; init.py verde. Smoke por director, coordinador y profesor.
