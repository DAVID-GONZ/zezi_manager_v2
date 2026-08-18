# portal_37_portal_shell — Spec

## Contexto

Tras `portal_35`, `/inicio` es el portal autenticado protegido. Hoy `inicio_page()`
(`src/interface/pages/inicio.py`) renderiza su propio `.hub-landing` standalone y **no usa
`app_layout`** (el layout portal rail+topbar de `src/interface/design/layout.py:489`), por
lo que no comparte navegacion con el resto de modulos. Ademas, el commit `inicio_34` dejo
construidos pero **sin consumir** los componentes de dashboard
(`src/interface/design/components/greeting_hero.py:27` y otros).

Este paso convierte `/inicio` en el **shell del portal inteligente**: usa `app_layout` para
heredar rail+topbar; anade al topbar un **buscador global** y una **campana de
notificaciones** (reutilizables por todas las paginas); oculta cualquier material de
marketing; y renderiza un banner de **saludo** (`greeting_hero`) seguido de un **resumen
global** en prosa ("Tienes 3 alertas de convivencia y 1 informe pendiente"). El resumen se
calcula en un servicio nuevo obtenido via `Container` (nunca instanciando repos en la
pagina), respetando rol y scope de `SessionContext.desde_storage()`
(`src/interface/context/session_context.py:58`), con degradacion fail-open.

Las sub-tarjetas de datos por modulo (Recientes/Alertas/Hitos) son el paso siguiente
(`portal_38`); aqui solo se monta el marco.

Scope: `src/interface/pages/inicio.py`,
`src/interface/design/layout.py` (buscador + campana en `_topbar`),
`src/interface/design/styles/layout/topbar.css`,
`src/interface/design/styles/CLASS_CONTRACT.md`,
`src/services/portal_resumen_service.py` (nuevo), `container.py`,
`tests/unit/services/test_portal_resumen_service.py` (nuevo).

## Requisitos (EARS)

- **R1** — `/inicio` DEBE renderizarse dentro de `app_layout(ctx, contenido, ...)` para
  heredar rail + topbar, en lugar de su `.hub-landing` standalone.
- **R2** — El topbar (`_topbar`, `layout.py:340`) DEBE ganar un **buscador global** y una
  **campana de notificaciones** con contador, reutilizables por todas las paginas. El
  logo/monograma DEBE enlazar a `/inicio`. El bloque de usuario con logout ya existe
  (`_user_block_topbar`, `layout.py:288`) y se conserva.
- **R3** — El material de marketing NO DEBE aparecer en el portal. En su lugar DEBE
  renderizarse `greeting_hero(...)` (componente existente) con saludo temporal + nombre +
  rol, seguido de un **resumen global** en prosa.
- **R4** — El resumen DEBE calcularse en `PortalResumenService` obtenido via
  `Container.portal_resumen_service()` (NUNCA repos fuera de `container.py`), respetando el
  rol y el scope de institucion de `SessionContext.desde_storage()`. Ante error DEBE
  degradar a un saludo sin cifras (fail-open), no romper la pagina.
- **R5** — El buscador y la campana PUEDEN entregar un **esqueleto funcional** (input que
  enruta a una busqueda futura; campana que abre un panel con las notificaciones ya
  derivables del resumen). NO DEBE bloquearse la entrega por busqueda avanzada.
- **R6** — DTOs y serializacion con `model_dump()` (NUNCA `.dict()`). El servicio NO DEBE
  importar `src.db` (solo via repos del `Container`).

## Diseño

### T1 — `/inicio` bajo `app_layout` (`inicio.py`)

`inicio_page()` construye un `contenido()` y lo pasa a `app_layout(ctx, contenido, ...)`.
`ctx` viene de `SessionContext.desde_storage()`. Se elimina el `.hub-landing` propio.

### T2 — Buscador + campana en el topbar (`layout.py`, `topbar.css`)

En `_topbar` anadir, junto a las acciones de pagina, un input `.topbar-search` y un boton
`.topbar-notif` con badge de contador (reusar `status_badge`/`counter` si encaja). Clases
nuevas en `CLASS_CONTRACT.md`, solo tokens. El logo DEBE ser `ui.link` a `/inicio`.

### T3 — `PortalResumenService` (`src/services/portal_resumen_service.py`, nuevo)

Metodo `resumen_global(ctx) -> ResumenGlobalDTO` que agrega conteos desde servicios ya
existentes (convivencia, informes, evaluacion) sin queries pesadas nuevas; devuelve lineas
de resumen (`texto`, `ruta_destino`, `severidad`) + total de notificaciones. Registrar en
`container.py` como `Container.portal_resumen_service()`. Envuelve toda llamada a repos en
try/except → fail-open a resumen vacio.

### T4 — Saludo + resumen (`inicio.py`)

En `contenido()`, antes de las tarjetas de modulo, renderizar `greeting_hero(...)` con
nombre/rol de `ctx`, seguido del resumen (lineas navegables a `ruta_destino`).

### T5 — Tests (`test_portal_resumen_service.py`, nuevo)

- `resumen_global` agrega conteos correctos con datos de prueba.
- fail-open: si un repo lanza, devuelve resumen vacio sin propagar.
- respeta el scope de institucion del `ctx`.

## Tareas

- [ ] **T1** — `/inicio` renderiza dentro de `app_layout`; se elimina `.hub-landing`.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/inicio.py`
- [ ] **T2** — Buscador global + campana en `_topbar`; logo enlaza a `/inicio`; clases en
  el contrato.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all`
- [ ] **T3** — `PortalResumenService` + registro en `container.py` (fail-open, `model_dump`).
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services`
- [ ] **T4** — `greeting_hero` + resumen global en `contenido()`.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/inicio.py`
- [ ] **T5** — Tests del servicio (agregacion, fail-open, scope).
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/services/test_portal_resumen_service.py -q`

## Verificacion final

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer interface
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Criterios observables (`python main.py`, con sesion): `/inicio` muestra rail+topbar con
buscador y campana; saludo con nombre/rol; una linea de resumen global navegable; ningun
material de marketing; si un servicio de conteo falla, el saludo aparece sin cifras (no hay
error). `init.py` verde.

## Dependencias

- `portal_35_split_ruta_raiz` — `/inicio` ya protegido y sin rama publica.
