# paso_13f — Theme Toggle + Dark Mode Refinement: spec

**Fecha:** 2026-06-08
**Status sugerido:** spec_ready
**Prerequisito:** paso_13a (estructura dark mode existe en tokens.css)

## Problema

paso_13a introdujo el bloque `@media (prefers-color-scheme: dark)` en `tokens.css`,
pero con dos limitaciones críticas:

1. **Sin control de usuario.** El modo lo decide el SO. El usuario no puede forzar
   claro u oscuro desde la aplicación.
2. **Dark mode con contraste insuficiente.** La paleta actual es funcional pero
   "no usable ni agradable" (feedback de David):
   - `--color-text-primary: #E8E9F8` (ink-100) sobre `#1C1D2A` → ratio ~12:1, OK
     en texto grande pero los grises secundarios (`#9297D9` ink-300) sobre fondo
     `#1C1D2A` dan ~5.2:1 — borderline para texto pequeño.
   - `--color-primary: var(--ink-500)` (#4B50C0) en dark sobre superficie clara
     mantiene legibilidad, pero los hovers y bordes (`--ink-100` = #E8E9F8) en
     light-mode no tienen análogo coherente en dark.
   - Sombras `rgba(0,0,0,0.30+)` se ven como bloques negros, no transmiten
     elevación.
   - Falta tratamiento específico para tablas (`ag-grid`), gráficos ECharts,
     y bordes de cards.

## Objetivos

### Objetivo 1 — Toggle persistente del tema

Botón en el topbar (junto al user block) que cicla entre 3 estados:

| Estado | Comportamiento |
|---|---|
| `auto` (default) | Sigue `prefers-color-scheme` del SO |
| `light` | Forzar tema claro independientemente del SO |
| `dark` | Forzar tema oscuro independientemente del SO |

Persistencia: `localStorage` con clave `andes-theme`.

### Objetivo 2 — Dark mode usable

Rediseñar la paleta dark para ratios AAA en texto principal y AA en secundario,
con elevación visual real (no negro plano).

## Diseño

### A. Mecanismo del toggle

**A.1 CSS**: cambiar de `@media (prefers-color-scheme: dark)` a selector explícito
`:root[data-theme="dark"]`. Reglas finales en `tokens.css`:

```css
/* Tema claro = :root default (sin selector explícito) */
:root { ... tokens claros ... }

/* Tema oscuro forzado */
:root[data-theme="dark"] {
  --color-bg: ...;
  ...
}

/* Modo auto: respeta el SO si no hay override */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-bg: ...;
    ...
  }
}
```

Esto permite las 3 modalidades sin duplicación de bloques.

**A.2 JS**: en `app_layout()` inyectar (junto al script de flyout):

```js
(function() {
  if (window.__andesThemeInit) return;
  window.__andesThemeInit = true;
  var saved = localStorage.getItem('andes-theme') || 'auto';
  if (saved !== 'auto') {
    document.documentElement.setAttribute('data-theme', saved);
  }
  window.__andesSetTheme = function(mode) {
    localStorage.setItem('andes-theme', mode);
    if (mode === 'auto') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', mode);
    }
    // refrescar icono del botón
    var btn = document.querySelector('.theme-toggle-btn');
    if (btn) btn.setAttribute('data-mode', mode);
  };
})();
```

**A.3 Python (layout.py)**: nuevo helper `_theme_toggle_btn()`:

```python
def _theme_toggle_btn() -> None:
    """Botón cíclico del tema: auto → light → dark → auto."""
    btn = ui.element("button").classes("theme-toggle-btn").props(
        'data-mode="auto" title="Cambiar tema (claro/oscuro/auto)" tabindex="0"'
    )
    with btn:
        # Tres iconos superpuestos; CSS muestra el activo según data-mode
        ThemeManager.icono("brightness_auto", size=20, clases="theme-icon icon-auto")
        ThemeManager.icono("light_mode",     size=20, clases="theme-icon icon-light")
        ThemeManager.icono("dark_mode",      size=20, clases="theme-icon icon-dark")
    btn.on("click", lambda _: ui.run_javascript(
        "var m=document.documentElement.getAttribute('data-theme')||'auto';"
        "var next=m==='auto'?'light':(m==='light'?'dark':'auto');"
        "window.__andesSetTheme(next);"
    ))
```

Insertar en `_topbar()` antes del `_user_block_topbar()`.

**A.4 CSS del botón** (nuevo archivo `styles/components/theme-toggle.css`):

```css
.theme-toggle-btn {
  width: 34px; height: 34px;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: background 0.15s, color 0.15s;
  position: relative;
}
.theme-toggle-btn:hover { background: var(--color-surface-alt); color: var(--color-primary); }
.theme-toggle-btn:focus-visible { outline: 2px solid var(--ink-500); outline-offset: 2px; }
.theme-icon { position: absolute; opacity: 0; transition: opacity 0.15s; }
.theme-toggle-btn[data-mode="auto"]  .icon-auto  { opacity: 1; }
.theme-toggle-btn[data-mode="light"] .icon-light { opacity: 1; }
.theme-toggle-btn[data-mode="dark"]  .icon-dark  { opacity: 1; }
```

### B. Dark mode refinado

**B.1 Paleta nueva en tokens.css**:

```
Fondos (escala de elevación):
  --color-bg:           #0F1019    (canvas — más oscuro)
  --color-surface:      #1A1C2E    (cards, panels)
  --color-surface-alt:  #252840    (hover, raised)
  --color-surface-high: #303355    (modales — nueva variable)

Texto (ratios sobre --color-surface = #1A1C2E):
  --color-text-primary:   #F0F1FA  (ratio 14.2:1 AAA)
  --color-text-secondary: #B8BCE8  (ratio 8.1:1 AAA)  — antes #9297D9
  --color-text-disabled:  #6E72A0  (ratio 4.6:1 AA)

Bordes (más visibles, no negros):
  --color-border:   #3A3D5C
  --color-divider:  rgba(184, 188, 232, 0.12)

Primario (para acción visible sobre fondo oscuro):
  --color-primary:        #8B90F0   (más claro que ink-500 — ratio 7.4:1)
  --color-primary-hover:  #A5A9F5
  --color-primary-light:  #2E3192   (usa ink-700 como "light" — contraintuitivo
                                     pero correcto: en dark, "light" = fondo
                                     más índigo para wash effects)
  --color-primary-contrast: #0F1019

Sombras con tinte índigo en lugar de negro plano:
  --shadow-sm:    0 1px 2px rgba(46, 49, 146, 0.30)
  --shadow-md:    0 4px 8px rgba(15, 16, 25, 0.50), 0 2px 4px rgba(46, 49, 146, 0.20)
  --shadow-lg:    0 10px 20px rgba(15, 16, 25, 0.60), 0 4px 8px rgba(46, 49, 146, 0.25)
  --shadow-card:  0 2px 6px rgba(15, 16, 25, 0.40)
  --shadow-modal: 0 24px 48px rgba(15, 16, 25, 0.80)

Navegación dark:
  --nav-sidebar-bg:        #161827   (un poco más oscuro que surface)
  --nav-sidebar-border:    #3A3D5C
  --nav-sidebar-text:      #B8BCE8
  --nav-sidebar-hover:     #252840
  --nav-sidebar-active-bg: #2E3192    (ink-700 mantiene identidad de marca)
  --nav-sidebar-active-text: #F0F1FA

  --nav-topbar-bg:     var(--color-surface)
  --nav-topbar-border: var(--color-border)
  --nav-topbar-text:   var(--color-text-primary)
```

**B.2 Ajustes específicos en componentes**:

Crear `styles/themes/dark.css` (cargar después de todos los componentes) con
overrides para:
- `.ag-theme-balham` en dark: fondos, bordes, hover, selección.
- `.flyout-item:hover`: usar `--color-surface-alt` en lugar de `--ink-050`.
- `.rail-item.is-active::before`: el accent-600 (ocre) se mantiene pero subir
  saturación para visibilidad.
- Badges del dominio (asistencia, desempeño): mantener sus colores hex
  inalterados (son colores semánticos), pero los fondos `*_bg` se ven mal sobre
  superficie oscura → en dark, usar `rgba()` del color con baja alpha.
- ECharts: añadir tema oscuro para los gráficos (paleta de líneas y fondo).

**B.3 Material Symbols**: la fuente Material Symbols Rounded hereda `currentColor`
— no requiere intervención, solo verificar que el contraste de iconos sigue las
mismas reglas que el texto.

## Tareas

| # | Tarea | Archivos |
|---|---|---|
| T1 | Reescribir bloque dark en tokens.css con paleta nueva | `tokens.css` |
| T2 | Convertir `@media` a `[data-theme]` con fallback auto | `tokens.css` |
| T3 | Inyectar JS de theme persistence en `app_layout()` | `layout.py` |
| T4 | Crear `_theme_toggle_btn()` y montarlo en `_topbar()` | `layout.py` |
| T5 | Crear `styles/components/theme-toggle.css` | nuevo |
| T6 | Crear `styles/themes/dark.css` con overrides ag-grid/flyout | nuevo |
| T7 | Registrar `theme-toggle.css` y `dark.css` en `CSS_LOAD_ORDER` | `theme.py` o `__init__.py` |
| T8 | Smoke test manual: ciclar auto→light→dark, recargar página, verificar persistencia | — |
| T9 | Smoke test contraste: tomar capturas en dark mode de 5 páginas representativas | — |
| T10 | Tests + init.py verde | — |

## Criterio done

- Botón en el topbar visible para todos los roles.
- Click cicla auto → light → dark → auto.
- Recargar página preserva el modo elegido.
- En dark mode:
  - Texto principal sobre cards: ratio ≥ 7:1 (AAA).
  - Texto secundario sobre cards: ratio ≥ 4.5:1 (AA).
  - Bordes visibles (no se confunden con el fondo).
  - Sombras con sensación de elevación, no bloques negros.
  - ag-grid: fondo de tabla coherente con el tema, hover de filas visible,
    celda seleccionada con accent.
  - Topbar y rail mantienen identidad de marca (índigo + ocre activo).
- Sin regresión: 740 tests verdes; init.py verde.
- Smoke en 5 páginas mínimo (inicio, estudiantes, planilla_notas, tablero, configuracion_sie).

## Notas y decisiones de diseño

- **Por qué `[data-theme]` y no `class="dark"`**: atributo de datos es más
  semántico, no contamina el namespace de clases, y permite ramificación con
  `:not([data-theme="light"])` para el modo auto.
- **Por qué tres modos (no toggle binario)**: respetar la preferencia del SO es
  un patrón de accesibilidad estándar (macOS, Windows 11). El usuario que no
  toca el botón mantiene el comportamiento "inteligente".
- **Por qué primario más claro en dark (#8B90F0)**: el ink-700 (#2E3192) sobre
  fondo oscuro tiene ratio ~3:1 — insuficiente para AA. El ink-500 (#4B50C0)
  apenas alcanza 4.5:1 y se ve apagado. Una tonalidad más clara (#8B90F0)
  mantiene la familia índigo y da 7.4:1, suficiente para botones y enlaces.
- **Sombras con tinte índigo**: las sombras puramente negras en interfaces
  oscuras crean "huecos" visuales sin profundidad. Un tinte sutil del primario
  da elevación percibida.
- **Material Symbols pueden tener weight diferente en dark**: opcional — bajar
  el weight a 200 en `@media dark` mejora la sensación de no-pesadez. No
  incluido en este spec para mantener consistencia con light; reservado para
  iteración futura.
