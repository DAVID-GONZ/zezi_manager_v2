# paso_13a — Design Evolution: Spec

**Fecha:** 2026-06-08
**Estado:** in_progress

## Propuestas analizadas

| ID | Propuesta | Decisión | Razón |
|----|-----------|----------|-------|
| §1  | Topbar claro | ✅ Implementar | CSS puro + 2 líneas Python. Elimina la disonancia cognitiva del topbar azul sobre fondo blanco |
| §2A | Mobile responsive | ⏸️ Diferir | Requiere condicional Python en layout.py para elegir entre rail y bottom-bar según viewport. No es CSS-only. Paso futuro. |
| §2B | Z-index tokens | ✅ Implementar | Mecánico, sin riesgo. Centraliza los 5 valores hardcodeados |
| §2C | Spacing consistente | ✅ Implementar | Reemplaza `gap: 20px` (fuera de escala) y `padding: 0 16px` hardcodeados |
| §3A | Tipografía rem | ✅ Implementar | Solo tokens.css + 3 archivos con valores hardcodeados |
| §3B | Keyboard tooltips | ✅ Implementar | `:focus-visible` en sidebar.css + `tabindex="0"` en rail items |
| §3C | Dark mode | ✅ Implementar | Estructura semántica + paleta oscura ink-aware |

## T1: Topbar claro

**Problema:** Topbar índigo (#2E3192) sobre contenido blanco crea dos zonas de alto contraste
visual que compiten. Además, los colores de texto hardcodeados en `layout.py` (white 0.85/0.9)
fijan el topbar como oscuro perpetuamente.

**Solución:**
- `.andes-topbar`: `background: var(--color-surface)`, `border-bottom: 1px solid var(--color-border)`
- Tokens topbar: `--nav-topbar-bg → var(--color-surface)`, `--nav-topbar-border → var(--color-border)`
- Todos los colores blancos del topbar → variantes oscuras del design system
- `layout.py`: remover `color="rgba(255,255,255,...)"` de `ThemeManager.icono()` calls
- Context chip: `background: var(--ink-050)`, `border: 1px solid var(--ink-100)`, `color: var(--ink-700)`

**Beneficio:** El topbar claro unifica visualmente con el sidebar paper, crea una franja de
navegación coherente, y el contenido index académico (#2E3192) aparece como acento en lugar de
fondo dominante.

## T2: Z-index tokens

Tokens nuevos en `:root`:
```
--z-index-rail:    900
--z-index-flyout:  940
--z-index-topbar:  1000
--z-index-modal:   1100
--z-index-toast:   1200
```

Referenciados en sidebar.css y topbar.css.

## T3: Consistent spacing

- `.page-stack { gap: 20px }` → `gap: var(--space-lg)` (28px — más rítmico)
- `.andes-topbar { padding: 0 16px }` → `padding: 0 var(--space-md)` (semántico)

## T4: Tipografía rem

Conversión en tokens.css:
```
h1: 24px → 1.5rem
h2: 20px → 1.25rem
h3: 17px → 1.0625rem
h4: 15px → 0.9375rem
body: 14px → 0.875rem
small: 12px → 0.75rem
label: 11px → 0.6875rem
table: 13px → 0.8125rem
```

Hardcoded px en layout/topbar.css y layout/sidebar.css → `var(--font-size-*)` o rem.
`cards.css` `.page-header-title: 22px` → `1.375rem`.

## T5: Keyboard a11y

- `sidebar.css`: `.rail-item:focus-visible` outline + tooltip visible on focus
- `layout.py`: `item_el.props(...)` añade `tabindex="0"` a cada rail item

## T6: Dark mode

`@media (prefers-color-scheme: dark)` en tokens.css. Solo sobrescribe la API pública
semántica (`--color-*`, `--nav-*`, `--shadow-*`). Los primitivos ink/paper/graphite
y los colores de dominio (asistencia, desempeño) permanecen inalterados.

El topbar claro (T1) hereda automáticamente el dark mode vía `var(--color-surface)`.

## Fix de consistencia

`@media (prefers-contrast: more)` tenía `--color-primary: #0F1E3D` (paleta anterior).
Corregido a `var(--ink-900)` (#1A1B6E).
