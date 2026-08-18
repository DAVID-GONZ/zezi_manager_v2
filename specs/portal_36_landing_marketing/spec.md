# portal_36_landing_marketing — Spec

## Contexto

Tras `portal_35`, `/` es una pagina publica con un shell minimo (`landing_page()` en
`src/interface/pages/landing.py`). Este paso la convierte en la **cara comercial** del
producto para visitantes sin sesion (modo SaaS): top-bar de marketing, hero con propuesta
de valor, cuadricula de caracteristicas y footer legal.

Las 5 tarjetas de caracteristicas se derivan del registro unico de modulos
(`src/domain/modulos.py`, `modulos_con_pagina()` devuelve Asistencia, Evaluacion,
Academico, Convivencia, Informes con `label`/`descripcion`/`icono`) — no se hardcodean.
A diferencia del hub interno, estas tarjetas **no navegan** a la ruta del modulo: anclan a
secciones explicativas de la misma pagina (`#caracteristicas-<id>`).

La landing es una superficie de marketing standalone: **no usa `app_layout`** (rail+topbar
del portal). Introduce clases nuevas namespaced `mkt-*`, que deben declararse en el contrato
y usar solo tokens (`check_design.py` reglas G/N; frontera Core/Adapter intacta).

Scope: `src/interface/pages/landing.py`,
`src/interface/design/styles/components/marketing.css` (nuevo),
`src/interface/design/styles/CLASS_CONTRACT.md`,
`src/interface/design/styles/tokens.css` (solo si faltan tokens),
`src/interface/design/styles/main.css` (import del parcial nuevo),
`tests/unit/interface/design/test_class_contract.py` (si aplica).

## Requisitos (EARS)

- **R1** — La landing DEBE renderizar una **top-bar de marketing**: logo a la izquierda;
  al centro enlaces ancla (Caracteristicas, Precios, Demo, Contacto); a la derecha
  "Iniciar sesion" (→`/login`) y "Registrate" (placeholder → `/login` hasta que exista
  registro).
- **R2** — DEBE renderizar un **hero**: titulo de propuesta de valor, subtitulo,
  imagen/mockup de la interfaz y un CTA primario (→`/login`).
- **R3** — DEBE renderizar **5 tarjetas de caracteristicas** obtenidas de
  `modulos_con_pagina()` (`label`, `descripcion`, `icono`); cada tarjeta ancla a
  `#caracteristicas-<id>`, NO navega a la ruta del modulo.
- **R4** — DEBE renderizar un **footer**: contacto, terminos y politica de privacidad
  (enlaces placeholder si aun no hay paginas).
- **R5** — Toda clase nueva DEBE declararse en `CLASS_CONTRACT.md` y usar **solo tokens**
  (nada de hex/px hardcodeado). NO DEBE haber selectores de framework (`.q-*`, etc.) fuera
  de `styles/adapter/`.
- **R6** — La landing NO DEBE usar `app_layout`; es standalone de marketing.

## Diseño

### T1 — `landing_page()` (`src/interface/pages/landing.py`)

Estructura con `ui.element("div")` + clases del contrato:
`.mkt-topbar` (logo + `.mkt-nav` con `.mkt-nav-link` ancla + botones) ›
`.mkt-hero` (`.mkt-hero-title`, `.mkt-hero-sub`, `.mkt-hero-cta`, imagen) ›
`.mkt-feature-grid` de `.mkt-feature-card` (una por modulo, iterando
`modulos_con_pagina()`) › secciones explicativas ancladas (`id="caracteristicas-<id>"`) ›
`.mkt-footer`. Reusar `btn_primary`/`btn_secondary` de `components/buttons.py` para CTAs y
`ThemeManager.icono` para iconos. Anclas con `ui.link(texto, "#caracteristicas-<id>")`.

### T2 — CSS de marketing (`styles/components/marketing.css`, nuevo)

Clases `mkt-*` con solo tokens (`--color-*`, `--space-*`, `--radius-*`, `--font-*`).
Importar el parcial en `styles/main.css`. Si se necesitan tokens nuevos (p.ej. un ancho
maximo de contenido de marketing), anadirlos en `tokens.css` y regenerar con
`python scripts/sync_tokens.py`. Declarar todas las clases en `CLASS_CONTRACT.md`
(seccion nueva "Marketing / landing").

### T3 — Gate de deploy documentado

Anotar (en `landing.py` docstring y en `docs/seguridad.md`) que publicar esta pagina a
produccion exige `seguridad_web_01` + `seguridad_web_02` done. No bloquea el build en dev.

## Tareas

- [ ] **T1** — Implementar `landing_page()` con top-bar, hero, feature grid (desde el
  registro) y footer.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/landing.py`
- [ ] **T2** — Crear `marketing.css`, importarlo en `main.css`, declarar clases `mkt-*` en
  `CLASS_CONTRACT.md`, tokens via `sync_tokens.py` si aplica.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all` y `scripts/sync_tokens.py --check`
- [ ] **T3** — Documentar el gate de deploy (S01+S02) en la landing y en `docs/seguridad.md`.
  Verificacion: revision.

## Verificacion final

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/sync_tokens.py --check
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/audit_design.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/interface -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Criterios observables (`python main.py`, sesion cerrada): `/` muestra top-bar de marketing,
hero con CTA, 5 tarjetas cuyas etiquetas coinciden con `modulos_con_pagina()`, cada una
ancla a su seccion; footer con enlaces legales; "Iniciar sesion" abre `/login`. `init.py`
verde y `check_design.py --all` sin violaciones.

## Dependencias

- `portal_35_split_ruta_raiz` — provee `/` publico y `landing_page` shell.
- **Gate de deploy:** `seguridad_web_01_tls_proxy`, `seguridad_web_02_secretos_config`
  (para publicar a produccion, no para construir).
