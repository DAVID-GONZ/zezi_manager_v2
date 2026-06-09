# Diseño — paso_12c_aula_serena

## Dependencias

Bloqueado por paso 12a (estructura `styles/` modular ya existe).

## 1. Estrategia de cambio

**No se renombran selectores ni variables públicas.** Solo cambian los valores
detrás de las variables `--color-*` y `--nav-*`. Esto garantiza que cualquier
componente que use `var(--color-primary)` adopta automáticamente la nueva paleta.

Las familias nuevas (`--ink-*`, `--accent-*`, `--paper-*`, `--graphite-*`) viven
como **variables internas** en `tokens.css`. El resto del sistema sigue usando
los nombres públicos (`--color-primary`, `--color-bg`, etc.) que ahora se mapean
a las nuevas familias.

## 2. `tokens.css` completo

Estructura del archivo final:

```css
/* tokens.css — Aula Serena */

/* ════ Fuentes ════ */
@import url('...Inter...');
@import url('...Source+Serif+4...');
@import url('...Material+Symbols+Rounded...');

:root {
  /* ── Familias internas ── */
  --ink-900: #0F1E3D;
  --ink-700: #1E3A6F;
  --ink-500: #3B5BA5;
  --ink-300: #8FA8D4;
  --ink-100: #E8EEF9;
  --ink-050: #F4F7FC;

  --accent-600: #B8763A;
  --accent-400: #D89A5B;
  --accent-100: #F7ECDD;

  --paper-000: #FFFFFF;
  --paper-050: #FAFAF7;
  --paper-100: #F2F2EC;
  --paper-200: #E5E5DE;
  --paper-300: #C8C8C0;

  --graphite-900: #1A1A1A;
  --graphite-700: #3D3D3D;
  --graphite-500: #6B6B6B;
  --graphite-300: #9D9D9D;

  /* ── API pública (mapeo) ── */
  --color-primary:           var(--ink-700);
  --color-primary-dark:      var(--ink-900);
  --color-primary-darker:    var(--ink-900);
  --color-primary-light:     var(--ink-500);
  --color-primary-lighter:   var(--ink-100);
  --color-primary-hover:     var(--ink-900);
  --color-primary-disabled:  var(--ink-300);
  --color-primary-contrast:  #FFFFFF;

  /* Mantengo secondary como aliases neutros para compatibilidad */
  --color-secondary:         var(--graphite-500);
  --color-secondary-dark:    var(--graphite-700);
  --color-secondary-light:   var(--paper-100);

  --color-error:             #C13030;
  --color-error-light:       #FBEAEA;
  --color-error-dark:        #9D2525;
  --color-warning:           #C8841C;
  --color-warning-light:     #FBF3E2;
  --color-success:           #2E7D5B;
  --color-success-light:     #EAF4EE;
  --color-info:              var(--ink-500);
  --color-info-light:        var(--ink-100);

  --color-bg:                var(--paper-050);
  --color-surface:           var(--paper-000);
  --color-surface-alt:       var(--paper-100);
  --color-divider:           rgba(0, 0, 0, 0.08);
  --color-border:            var(--paper-200);
  --color-text-primary:      var(--graphite-900);
  --color-text-secondary:    var(--graphite-500);
  --color-text-disabled:     var(--graphite-300);
  --color-text-inverse:      #FFFFFF;
  --color-disabled-bg:       var(--paper-200);
  --color-disabled-text:     var(--graphite-500);

  --nav-sidebar-bg:           var(--paper-050);
  --nav-sidebar-text:         var(--graphite-700);
  --nav-sidebar-hover:        var(--ink-100);
  --nav-sidebar-active-bg:    var(--ink-700);
  --nav-sidebar-active-text:  #FFFFFF;
  --nav-sidebar-border:       var(--paper-200);

  --nav-topbar-bg:     var(--ink-700);
  --nav-topbar-text:   #FFFFFF;
  --nav-topbar-border: rgba(255, 255, 255, 0.10);

  /* Dominio: asistencia */
  --attend-presente:    var(--color-success);
  --attend-presente-bg: var(--color-success-light);
  --attend-fj:          var(--color-warning);
  --attend-fj-bg:       var(--color-warning-light);
  --attend-fi:          var(--color-error);
  --attend-fi-bg:       var(--color-error-light);
  --attend-retraso:     #6D4E9C;
  --attend-retraso-bg:  #F0EAFA;
  --attend-excusa:      var(--ink-500);
  --attend-excusa-bg:   var(--ink-100);

  /* Dominio: desempeño */
  --desempeno-bajo:        #B4322E;
  --desempeno-bajo-bg:     #FAE7E6;
  --desempeno-basico:      var(--accent-600);
  --desempeno-basico-bg:   var(--accent-100);
  --desempeno-alto:        var(--ink-500);
  --desempeno-alto-bg:     var(--ink-100);
  --desempeno-superior:    var(--color-success);
  --desempeno-superior-bg: var(--color-success-light);

  /* Tipografía */
  --font-display: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
  --font-family:  'Inter', system-ui, -apple-system, sans-serif;
  --font-mono:    'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  --font-size-h1:      24px;
  --font-size-h2:      20px;
  --font-size-h3:      17px;
  --font-size-h4:      15px;
  --font-size-body:    14px;
  --font-size-small:   12px;
  --font-size-label:   11px;
  --font-size-table:   13px;

  /* Espaciado, layout, bordes, sombras, transiciones — sin cambios */
  --space-xs: 4px;
  /* ... resto idéntico ... */

  /* Sombras NEUTRAS (sin tinte de color) */
  --shadow-sm:    0 1px 2px 0 rgba(0, 0, 0, 0.04);
  --shadow-md:    0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -1px rgba(0, 0, 0, 0.04);
  --shadow-lg:    0 10px 15px -3px rgba(0, 0, 0, 0.07), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
  --shadow-card:  0 2px 8px rgba(0, 0, 0, 0.04);
  --shadow-modal: 0 20px 40px rgba(0, 0, 0, 0.12);
}

@media (prefers-contrast: more) { ... }
@media (prefers-reduced-motion: reduce) { ... }
```

## 3. `typography.css` actualizado

```css
body {
  font-family: var(--font-family);
  font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';  /* Inter mejor */
}

h1, .display-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--font-size-h1);
  letter-spacing: -0.01em;
}

/* h2, h3, h4 siguen en Inter para mantener consistencia con UI */
h2 { font-family: var(--font-family); font-weight: 600; }
h3 { font-family: var(--font-family); font-weight: 600; }
h4 { font-family: var(--font-family); font-weight: 600; }

.topbar-page-title {
  font-family: var(--font-display);
  font-weight: 600;
}

code, pre, .text-mono {
  font-family: var(--font-mono);
}
```

## 4. `layout/sidebar.css` — adaptación a sidebar claro

Cambios puntuales en el archivo existente (el patrón rail viene en 12d; aquí solo
ajustamos colores):

```css
/* Antes */
.andes-sidebar {
  background: var(--nav-sidebar-bg);  /* era gradient oscuro */
  border-right: var(--nav-border-right);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);
}

/* Después */
.andes-sidebar {
  background: var(--nav-sidebar-bg);  /* mapea ahora a paper-050 */
  border-right: 1px solid var(--nav-sidebar-border);
  box-shadow: none;                    /* sin sombra; el borde basta */
}

.andes-sidebar-item:hover {
  background: var(--nav-sidebar-hover);     /* ink-100 */
  color: var(--graphite-900);               /* texto oscuro al hover */
  transform: none;                          /* quitar translateX(4px) */
}

.andes-sidebar-item.active {
  background: var(--nav-sidebar-active-bg); /* ink-700 */
  color: var(--nav-sidebar-active-text);    /* blanco */
  font-weight: 600;
  box-shadow: none;                         /* sin glow */
}

/* Logo del sidebar — texto oscuro sobre claro */
.sidebar-logo-text {
  color: var(--graphite-900);
}
.sidebar-sub-text {
  color: var(--graphite-500);
}
```

## 5. `layout/topbar.css` — adaptación

```css
/* Antes */
.andes-topbar {
  background: linear-gradient(160deg,
    rgba(97, 27, 50, 0.97) 0%,
    rgba(179, 50, 93, 0.93) 60%,
    rgba(219, 61, 114, 0.88) 100%);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 4px 24px rgba(179, 50, 93, 0.25);
}

/* Después */
.andes-topbar {
  background: var(--nav-topbar-bg);                 /* ink-700 sólido */
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  border-bottom: 1px solid var(--nav-topbar-border);
}
```

## 6. Iconos del sidebar — adaptación al claro

Los iconos del sidebar hoy son blancos. Sobre fondo claro deben ser oscuros.
Ajustar el render en `layout.py` o vía CSS:

```css
.andes-sidebar .material-symbols-rounded {
  color: var(--graphite-700);
}
.andes-sidebar-item.active .material-symbols-rounded {
  color: var(--nav-sidebar-active-text);  /* blanco sobre activo ink-700 */
}
```

Nota: si `layout.py` pasa `color="white"` hardcoded a `ThemeManager.icono()` para
iconos del sidebar, el implementer debe quitar ese argumento y dejar que el CSS
controle el color. Buscar:

```
grep -n "color=\"white\"" src/interface/design/layout.py
grep -n "color=\"rgba(255" src/interface/design/layout.py
```

y reemplazar por `color=None` o quitar el argumento.

## 7. Regeneración de tokens.py

`scripts/sync_tokens.py` (de paso 12a) regenera automáticamente `tokens.py` con
los nuevos valores hex. Las clases `Colors.PRIMARY` ahora valen `#1E3A6F`, etc.

Cualquier código Python que dependa de los valores anteriores (por ejemplo,
`tokens.Colors.PRIMARY == "#B3325D"`) se rompe. **Es esperado.** El implementer
verifica:

```
grep -rn "Colors\.PRIMARY\|Colors\.PRIMARY_DARK\|#B3325D\|#8A2748" src/
```

Si hay un hex de la paleta vieja hardcodeado fuera de `tokens.py` y `tokens.css`,
es bug del paso 11z (no debería existir). El implementer lo lista en
`progress/impl_12c.md` y aplica el reemplazo correspondiente.

## 8. Validación de contraste

Combinaciones críticas a verificar (WCAG AA = 4.5:1 para texto normal, 3:1 para
texto >= 18pt o iconos):

| Texto | Fondo | Combinación | Mínimo | Actual aprox. |
|---|---|---|---|---|
| `--graphite-900` | `--paper-050` | UI body | 4.5:1 | ~16:1 ✓ |
| `--graphite-500` | `--paper-050` | text secondary | 4.5:1 | ~5.4:1 ✓ |
| `#FFFFFF` | `--ink-700` | botón primary, topbar | 4.5:1 | ~9.5:1 ✓ |
| `--graphite-700` | `--paper-050` | sidebar item | 4.5:1 | ~10:1 ✓ |
| `#FFFFFF` | `--accent-600` | badge ocre | 4.5:1 | ~3.8:1 ⚠ usar solo grandes o como BG |
| `--ink-700` | `--ink-100` | hover sidebar | 4.5:1 | ~9:1 ✓ |
| `--color-warning` `#C8841C` | `#FFFFFF` | texto | 4.5:1 | ~3.5:1 ⚠ usar solo como BG con texto oscuro |

Conclusión: **warning y accent NO se usan para texto sobre blanco** — solo para
fondos de badge con texto oscuro encima. Los badges existentes ya siguen ese patrón.

## 9. Alternativa descartada

**Mantener borgoña como acento educativo y añadir azul tinta como primario.**
Descartada: dos colores institucionales fuertes compiten y obligan a decisiones
caso por caso ("¿esto va en azul o en borgoña?"). Un primario único + un acento
sutil (ocre, no rojo) es más sostenible y produce un look más coherente.

## 10. Orden de tareas

1. T1: reescribir `tokens.css` completo.
2. T2: regenerar `tokens.py` (sync script).
3. T3: actualizar `typography.css` (fuente Source Serif).
4. T4: actualizar `layout/sidebar.css` (claro).
5. T5: actualizar `layout/topbar.css` (sólido sin blur).
6. T6: ajustar render de iconos del sidebar.
7. T7: barrido de hex hardcodeados de la paleta vieja.
8. T8: smoke visual + reporte.
9. T9: verificación final.
