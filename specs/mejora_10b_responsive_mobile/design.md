# Design: mejora_10b — Responsive y mobile-first

> **Origen:** evaluación de modernidad del design system (2026-08-09).
> **Tipo:** mejora de layout/UX. Sin cambio de identidad visual.
> **Prerrequisitos:** ninguno. Recomendado tras 10a (fuentes).

---

## Problema

El sistema está diseñado para escritorio (sidebar 220px, ventana nativa). Evidencia:
solo ~6 breakpoints de layout reales (`max-width: 1100/820/640/560`, `min-width: 1024`),
**0 usos de `clamp()`** y **0 container queries**. Para que la app sea usable como
**web** (y luego Capacitor/Android) faltan: escala fluida, comportamiento de navegación
en pantallas chicas, y garantía de no-overflow horizontal.

## Objetivo

Mobile-first pragmático **sin rediseñar**: (1) tokens de breakpoint, (2) tipografía y
espaciado fluidos con `clamp()`, (3) navegación adaptativa (sidebar → rail/drawer bajo
un breakpoint), (4) cero scroll horizontal y targets táctiles ≥ 44px en 360/768/1280.

---

## 1. Tokens de breakpoint

En `tokens.css`, formalizar la escala (hoy los px están sueltos en cada `@media`):

```css
--bp-sm: 560px;   --bp-md: 768px;   --bp-lg: 1024px;   --bp-xl: 1280px;
```

> CSS no interpola variables dentro de `@media (...)`; los tokens son la **referencia
> canónica** y cada `@media` usa el mismo valor literal. Documentar la equivalencia.
> Consolidar los breakpoints actuales (1100/820/640/560) a esta escala donde no cambie el layout.

## 2. Tipografía y espaciado fluidos

Reemplazar los `--font-size-*` de la escala grande por `clamp()` (mínimo móvil → máximo
escritorio), preservando el valor actual como **máximo** (cero cambio en desktop):

```css
--font-size-h1: clamp(1.25rem, 1rem + 1.2vw, 1.5rem);   /* hoy 1.5rem = máx */
--font-size-h2: clamp(1.1rem, 0.95rem + 0.8vw, 1.25rem);
/* body/small/label se dejan fijos (legibilidad) */
```

Y `--content-padding` fluido: `clamp(16px, 4vw, 24px)`.

## 3. Navegación adaptativa

`layout.py` ya renderiza un **rail** (60px, `--rail-width`) además del sidebar (220px).
Estrategia por breakpoint (CSS + un toggle en `layout.py`):
- **≥ `--bp-lg` (1024):** comportamiento actual (sidebar/rail según estado).
- **`--bp-md`–`--bp-lg`:** forzar **rail** (iconos) para ganar ancho de contenido.
- **< `--bp-md` (768):** sidebar **off-canvas** (drawer) que abre con el botón de menú del
  topbar; overlay que cierra al tocar fuera. El contenido ocupa el 100% del ancho.

> La parte de abrir/cerrar el drawer requiere estado en `layout.py` (una clase toggled
> en el contenedor raíz); el resto es CSS sobre `sidebar.css`/`content.css`/`topbar.css`.

## 4. No-overflow y táctil

- Auditar tablas/grillas anchas (ag-Grid, `.stats-grid`, parrilla de horarios): envolver
  en contenedor `overflow-x: auto` propio; el `body` nunca hace scroll horizontal
  (`overflow-x: hidden` ya está en `reset.css`).
- Targets interactivos (botones icon-only del topbar/rail, chips) con `min-height/min-width: 44px`
  bajo `--bp-md`.

---

## Verificación

- En 360 / 768 / 1280 px: sin scroll horizontal del `body`, sin solapes, nav utilizable.
- Drawer abre/cierra bajo 768; contenido a ancho completo.
- Desktop (≥1280) **idéntico** al actual (los `clamp()` topan en el valor previo).
- `python scripts/check_design.py --all` y `python init.py` en verde.
