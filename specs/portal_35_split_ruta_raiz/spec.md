# portal_35_split_ruta_raiz — Spec

## Contexto

Hoy la raiz `/` solo redirige a `/inicio` (`main.py:111`, handler `raiz()` con
`ui.navigate.to("/inicio")`), y `/inicio` es una pagina **PUBLICO** (`main.py:149`) que
hace render dual dentro de `inicio_page()` (`src/interface/pages/inicio.py:105`): sin
sesion muestra tarjetas que llevan a `/login` (rama `else`, L142-158), con sesion muestra
tarjetas filtradas por rol (L130-141).

Se quiere separar limpiamente los dos modos en **dos rutas**: `/` = landing publica de
marketing (contenido en `portal_36`), `/inicio` = portal autenticado protegido (shell en
`portal_37`). Este paso establece el esqueleto de enrutamiento y proteccion; deja `/` con
una landing minima y `/inicio` solo con su camino autenticado. Reutiliza el wrapper
`registrar_pagina(ruta, fn, roles=...)` (`route_guard.py:215`) y los sentinels `PUBLICO` /
`AUTENTICADO` (`route_guard.py:57-58`); el guard `_pagina_protegida` (`:240`) ya redirige a
`/login` sin sesion, asi que proteger `/inicio` es cambiar su `roles`.

Scope: `main.py`, `src/interface/pages/inicio.py`,
`src/interface/pages/landing.py` (nuevo, shell minimo),
`tests/unit/interface/test_rutas_raiz.py` (nuevo),
`tests/unit/interface/design/test_navitems.py` (extender).

## Requisitos (EARS)

- **R1** — `/` DEBE registrarse con `registrar_pagina("/", landing_page, roles=PUBLICO)` y
  renderizar `landing_page()`. NO DEBE seguir redirigiendo a `/inicio`.
- **R2** — `/inicio` DEBE registrarse con `roles=AUTENTICADO` (no `PUBLICO`). Un visitante
  sin sesion que abra `/inicio` DEBE ser redirigido a `/login` por el guard existente.
- **R3** — La rama publica de `inicio_page` (tarjetas → `/login` y footer "Iniciar sesion",
  hoy L142-158) DEBE eliminarse. `inicio_page` queda solo con el camino autenticado; ya no
  necesita comprobar `autenticado` internamente.
- **R4** — El login DEBE seguir navegando a `/inicio` tras autenticar (`login.py`, sin
  cambios). El shell de la landing DEBE ofrecer un CTA "Iniciar sesion" → `/login`.
- **R5** — DEBE existir test que verifique `roles_de_ruta("/")` publico y
  `roles_de_ruta("/inicio")` no publico (requiere sesion).

## Diseño

### T1 — Landing shell (`src/interface/pages/landing.py`, nuevo)

`landing_page()` minimo: branding + un CTA `ui.link("Iniciar sesion", "/login")`.
`portal_36` sustituye este cuerpo por el marketing real (top-bar, hero, cards, footer). No
usa `app_layout`.

### T2 — Registro de rutas (`main.py:111-124, 149`)

- Reemplazar el handler `raiz()` (redirect) por
  `registrar_pagina("/", landing_page, roles=PUBLICO)`.
- Cambiar el registro de `/inicio` de `PUBLICO` a `AUTENTICADO`.
- Importar `landing_page` desde `src.interface.pages.landing`.

### T3 — Podar la rama publica de `inicio.py`

Eliminar de `inicio_page()` (L106-158) la deteccion de sesion y la rama `else` publica +
footer de login. Conservar solo el render autenticado (admin y roles). El branding/greeting
propio se reemplaza por el shell del portal en `portal_37`; aqui basta con dejar la pagina
funcional para usuarios autenticados.

### T4 — Tests (`test_rutas_raiz.py` nuevo; `test_navitems.py` extender)

- `roles_de_ruta("/")` es el conjunto publico.
- `roles_de_ruta("/inicio")` requiere sesion (no publico).
- `decidir_acceso("/inicio", sesion=None)` → redirect a `/login`.

## Tareas

- [ ] **T1** — Crear `landing.py` con `landing_page()` shell minimo + CTA login.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer interface`
- [ ] **T2** — En `main.py`: `/` publico → `landing_page`; `/inicio` → `AUTENTICADO`.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "from src.interface.auth.route_guard import roles_de_ruta; assert roles_de_ruta('/inicio') != 'PUBLICO'"`
- [ ] **T3** — Podar la rama publica de `inicio_page`.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/inicio.py`
- [ ] **T4** — Tests de rutas raiz y guard.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/interface/test_rutas_raiz.py tests/unit/interface/design/test_navitems.py -q`

## Verificacion final

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer interface
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/inicio.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/interface -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Criterios observables (`python main.py`): abrir `/` sin sesion muestra la landing (shell),
no redirige; abrir `/inicio` sin sesion redirige a `/login`; tras login se llega a `/inicio`;
`init.py` verde.

## Dependencias

Ninguna. Es la base de `portal_36` y `portal_37`.
