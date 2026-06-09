# Tasks — paso_12c_aula_serena

## Resumen

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T1 | Reescribir tokens.css con paleta Aula Serena | `styles/tokens.css` | grep ink-700 |
| T2 | Regenerar tokens.py | `tokens.py` (autogen) | sync_tokens --check |
| T3 | typography.css con dual font | `styles/typography.css` | grep Source Serif |
| T4 | sidebar.css → tema claro | `styles/layout/sidebar.css` | smoke visual |
| T5 | topbar.css → azul sólido sin blur | `styles/layout/topbar.css` | grep backdrop |
| T6 | Iconos del sidebar adaptados | `layout.py` o CSS | smoke visual |
| T7 | Barrer hex viejos hardcodeados | grep + edit | grep |
| T8 | Smoke visual + reporte | progress/impl_12c.md | manual |
| T9 | Verificación final | — | init.py + tests |

---

## T1 — tokens.css

Reemplazar el contenido completo de `src/interface/design/styles/tokens.css` por
el bloque definido en design.md §2.

Mantener:
- Variables de espaciado (`--space-*`).
- Variables de radio (`--radius-*`).
- Variables de layout (`--sidebar-width`, etc.) — ya resueltas en 12a.
- Variables de transiciones (`--transition-*`).
- Variables de componentes (`--btn-height`, `--input-height`, etc.).

Reemplazar todo lo demás (colores, navegación, dominio, tipografía, sombras).

**Verificación:**
```
grep -c "ink-700\|accent-600\|paper-050\|graphite-900" src/interface/design/styles/tokens.css
# >= 4
grep -c "#B3325D\|#8A2748" src/interface/design/styles/tokens.css
# 0
```

---

## T2 — Regenerar tokens.py

```
python scripts/sync_tokens.py
python scripts/sync_tokens.py --check
echo $?   # 0
```

Verificar que `Colors.PRIMARY` ahora vale `"#1E3A6F"`:

```
python -c "from src.interface.design.tokens import Colors; print(Colors.PRIMARY)"
# #1E3A6F
```

---

## T3 — typography.css

Reescribir `src/interface/design/styles/typography.css` para:

1. Añadir `@import` de Source Serif 4 al inicio (si los imports viven en
   `tokens.css`, mover Source Serif allí; mantener un solo punto de carga de
   fuentes externas).
2. Aplicar `font-family: var(--font-display)` a `h1, .display-title, .topbar-page-title`.
3. El resto de elementos sigue `var(--font-family)` (Inter).

**Verificación:**
```
grep "Source Serif" src/interface/design/styles/typography.css src/interface/design/styles/tokens.css
# Debe aparecer en uno de los dos
```

Visual: abrir la app, ir a inicio. El título grande debe verse en serif. Los
labels de tabla, formularios, botones, en Inter.

---

## T4 — sidebar.css claro

En `src/interface/design/styles/layout/sidebar.css`:

1. Quitar `box-shadow: 4px 0 24px rgba(0,0,0,0.4)` del `.andes-sidebar`.
2. Cambiar `border-right` por `1px solid var(--nav-sidebar-border)`.
3. En `.andes-sidebar-item:hover`, quitar `transform: translateX(4px)`.
4. En `.andes-sidebar-item.active`, quitar `box-shadow` coloreado.
5. Añadir bloque de iconos:
   ```css
   .andes-sidebar .material-symbols-rounded {
     color: var(--graphite-700);
   }
   .andes-sidebar-item.active .material-symbols-rounded {
     color: var(--nav-sidebar-active-text);
   }
   ```
6. `.sidebar-logo-text { color: var(--graphite-900); }`.
7. `.sidebar-sub-text { color: var(--graphite-500); }`.

**Verificación visual:** sidebar claro con texto oscuro. Item activo: fondo azul
tinta + texto blanco. Hover: fondo `ink-100` con texto oscuro.

---

## T5 — topbar.css azul sólido

En `src/interface/design/styles/layout/topbar.css`:

1. Reemplazar el `background` (gradient triple) por `var(--nav-topbar-bg)` sólido.
2. Eliminar `backdrop-filter` y `-webkit-backdrop-filter`.
3. Reemplazar `box-shadow` coloreado por `0 1px 3px rgba(0, 0, 0, 0.08)`.
4. `border-bottom: 1px solid var(--nav-topbar-border)`.

**Verificación:**
```
grep "backdrop-filter\|linear-gradient" src/interface/design/styles/layout/topbar.css
# Solo gradients permitidos en submenús internos (si existen); el .andes-topbar
# principal NO debe tener.
```

---

## T6 — Iconos del sidebar

Buscar en `layout.py`:
```
grep -n "color=\"white\"\|color=\"rgba(255" src/interface/design/layout.py
```

Cada llamada `ThemeManager.icono(..., color="white")` o
`color="rgba(255,255,255,0.85)"` dentro del bloque `_sidebar()` (no del topbar)
se cambia a `color=None` (= deja al CSS controlar).

Los del topbar SÍ quedan blancos (porque el topbar sigue oscuro tinta).

**Verificación visual:** iconos del sidebar oscuros sobre claro; iconos del
topbar blancos sobre tinta.

---

## T7 — Barrido de hex viejos

```
grep -rn "#B3325D\|#8A2748\|#611B32\|#DB3D72\|#FCE8ED\|#DDA8B8" src/
```

Cualquier ocurrencia fuera de `tokens.css` y `tokens.py` (autogenerado) se
reemplaza por `var(--color-primary)` o el equivalente correcto. Tokens.css
no debería tener ninguno tampoco.

```
grep -rn "#47FF59\|#47FF97" src/
```

Idem para los verdes neón.

```
grep -rn "rgba(179, 50, 93\|rgba(97, 27, 50\|rgba(219, 61, 114" src/
```

Cualquier rgba de la paleta borgoña pasa a sombra neutra `rgba(0, 0, 0, X)`.

Documentar en `progress/impl_12c.md` cada cambio fuera del scope habitual.

---

## T8 — Smoke visual

Arrancar `python main.py` y navegar manualmente a:

1. `/login`
2. `/inicio`
3. `/estudiantes`
4. `/asistencia`
5. `/evaluacion/planilla`
6. `/evaluacion/configuracion`
7. `/evaluacion/habilitaciones`
8. `/informes/boletin-periodo`
9. `/informes/estadisticos`
10. `/admin/grupos`
11. `/admin/configuracion`

Para cada una, escribir en `progress/impl_12c.md` 1-2 frases descriptivas y
flagear cualquier anomalía (texto ilegible, color inconsistente, componente
que se rompió).

Cualquier anomalía visible la corrige el implementer o se abre ticket
`paso_12c_followup_<área>`.

---

## T9 — Verificación final

```
python scripts/sync_tokens.py --check
python init.py
pytest tests/ --tb=short
```

Todo verde. Sin regresión de tests. Sin nuevas violaciones de design system.

Reviewer:
- Verifica que no quedan hex de la paleta borgoña.
- Verifica que `backdrop-filter` no aparece en el sidebar ni topbar principales.
- Verifica que `font-display` se aplica solo donde corresponde (no rompe legibilidad
  de planilla).
- Verifica que el sidebar es claro y consistente con la propuesta.
