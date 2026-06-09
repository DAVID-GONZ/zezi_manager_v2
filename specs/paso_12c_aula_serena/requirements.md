# Requisitos — paso_12c_aula_serena

## Contexto

El design system actual ("Andes Minimal v2") usa una paleta borgoña/carmesí sobre
sidebar oscuro premium. Tres problemas para un software educativo de uso prolongado:

1. **Carga visual alta.** Sidebar negro premium + topbar con gradient triple +
   verde neón (#47FF59) en estados positivos. Fatiga visual en jornadas de 6-8
   horas de uso.
2. **Confusión semántica primary ↔ error.** El borgoña primario (#B3325D) y el
   rojo de error (#DC2626) viven en el mismo eje cromático. El comentario del
   propio CSS lo admite: `/* Suficiente diferenciación visual del primario */`.
3. **Estética corporativa, no educativa.** Inspiración tipo Linear/Notion (apps
   de productividad) cuando el dominio es gestión académica colombiana.

Este paso reemplaza la paleta por **"Aula Serena"**: tinta académica + ocre
manuscrito + neutros cálidos + tipografía dual (serif para títulos institucionales,
sans para UI cotidiana).

## Alcance

- `src/interface/design/styles/tokens.css` — todas las variables de color.
- `src/interface/design/tokens.py` — se regenera por el script de 12a.
- `src/interface/design/styles/typography.css` — tipografía dual.
- `src/interface/design/styles/layout/sidebar.css` — sidebar de oscuro a claro.
- `src/interface/design/styles/layout/topbar.css` — topbar a azul sólido.
- `src/interface/design/styles/reset.css` — fondo cálido del body.

**Fuera de scope:**
- Cambiar el patrón de navegación (sidebar acordeón → rail): paso 12d.
- Cambiar la información del menú: paso 12e.
- Cambiar componentes funcionalmente (botones, tablas) — solo absorben la nueva
  paleta vía variables CSS.

## Dependencias

Bloqueado por **paso 12a** (split de styles.css y script de sync). Sin la carpeta
`styles/` modular, este paso sería un parche sobre el monolito.

## Requisitos funcionales

### R1 — Nueva paleta primaria "Tinta académica"

Reemplazo completo de `--color-primary*`:

```css
--ink-900: #0F1E3D;
--ink-700: #1E3A6F;   /* color-primary */
--ink-500: #3B5BA5;
--ink-300: #8FA8D4;
--ink-100: #E8EEF9;
--ink-050: #F4F7FC;

--color-primary:          var(--ink-700);
--color-primary-dark:     var(--ink-900);
--color-primary-darker:   var(--ink-900);
--color-primary-light:    var(--ink-500);
--color-primary-lighter:  var(--ink-100);
--color-primary-hover:    var(--ink-900);
--color-primary-disabled: var(--ink-300);
--color-primary-contrast: #FFFFFF;
```

### R2 — Acento ocre "Manuscrito"

NUEVA familia (no existe equivalente hoy). Pensada para badges institucionales,
highlight de fila seleccionada, botón secundario destacado:

```css
--accent-600: #B8763A;
--accent-400: #D89A5B;
--accent-100: #F7ECDD;
```

### R3 — Neutros cálidos "Pergamino y grafito"

Reemplazo de los neutros zinc:

```css
--paper-000: #FFFFFF;
--paper-050: #FAFAF7;     /* color-bg */
--paper-100: #F2F2EC;     /* color-surface-alt y zebra */
--paper-200: #E5E5DE;     /* color-border */
--paper-300: #C8C8C0;

--graphite-900: #1A1A1A;  /* color-text-primary */
--graphite-700: #3D3D3D;
--graphite-500: #6B6B6B;  /* color-text-secondary */
--graphite-300: #9D9D9D;  /* color-text-disabled */

/* Mapeo a variables existentes (mantiene API) */
--color-bg:              var(--paper-050);
--color-surface:         var(--paper-000);
--color-surface-alt:     var(--paper-100);
--color-divider:         rgba(0, 0, 0, 0.08);   /* más sutil que 0.12 */
--color-border:          var(--paper-200);
--color-text-primary:    var(--graphite-900);
--color-text-secondary:  var(--graphite-500);
--color-text-disabled:   var(--graphite-300);
--color-text-inverse:    #FFFFFF;
--color-disabled-bg:     var(--paper-200);
--color-disabled-text:   var(--graphite-500);
```

### R4 — Semánticos desaturados

```css
--color-success:      #2E7D5B;
--color-success-light:#EAF4EE;
--color-warning:      #C8841C;
--color-warning-light:#FBF3E2;
--color-error:        #C13030;
--color-error-light:  #FBEAEA;
--color-error-dark:   #9D2525;
--color-info:         var(--ink-500);   /* reutiliza tinta */
--color-info-light:   var(--ink-100);
```

### R5 — Dominio académico — desempeño

```css
--desempeno-bajo:        #B4322E;
--desempeno-bajo-bg:     #FAE7E6;
--desempeno-basico:      var(--accent-600);  /* ocre */
--desempeno-basico-bg:   var(--accent-100);
--desempeno-alto:        var(--ink-500);     /* tinta */
--desempeno-alto-bg:     var(--ink-100);
--desempeno-superior:    var(--color-success);
--desempeno-superior-bg: var(--color-success-light);
```

### R6 — Dominio académico — asistencia

```css
--attend-presente:    var(--color-success);     /* verde bosque */
--attend-presente-bg: var(--color-success-light);
--attend-fj:          var(--color-warning);     /* ámbar marrón */
--attend-fj-bg:       var(--color-warning-light);
--attend-fi:          var(--color-error);       /* terracota */
--attend-fi-bg:       var(--color-error-light);
--attend-retraso:     #6D4E9C;                  /* violeta apagado */
--attend-retraso-bg:  #F0EAFA;
--attend-excusa:      var(--ink-500);           /* azul tinta */
--attend-excusa-bg:   var(--ink-100);
```

### R7 — Sidebar claro

```css
--nav-sidebar-bg:        var(--paper-050);   /* claro */
--nav-sidebar-text:      var(--graphite-700);
--nav-sidebar-hover:     var(--ink-100);
--nav-sidebar-active-bg: var(--ink-700);
--nav-sidebar-active-text: #FFFFFF;
--nav-sidebar-border:    var(--paper-200);   /* borde derecho sutil */
```

Eliminar el gradient del sidebar. Sin sombra coloreada (`box-shadow` neutro). Sin
`backdrop-filter`.

### R8 — Topbar azul sólido

```css
--nav-topbar-bg:     var(--ink-700);
--nav-topbar-text:   #FFFFFF;
--nav-topbar-border: rgba(255, 255, 255, 0.10);
```

Eliminar el gradient triple y el `backdrop-filter: blur(20px)`. Color sólido. La
sombra del topbar pasa a ser neutra (rgba negro 0.08).

### R9 — Tipografía dual

Cargar dos familias:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,300,0,0');

--font-display: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
--font-family:  'Inter', system-ui, -apple-system, sans-serif;
--font-mono:    'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
```

Aplicar `--font-display` SOLO en:
- `h1` de páginas con `page_header` formal.
- `.topbar-page-title` (título de página en topbar).
- `.login-brand` (splash de login, si existe).

El resto sigue Inter. No reemplazar Inter en tablas, formularios o body.

### R10 — Eliminar efectos cosméticos contraindicados

Buscar y eliminar:
- `backdrop-filter: blur(...)` en cualquier parte (topbar, modales sí permitidos).
- Gradients triples en topbar y sidebar.
- Sombras coloreadas (`rgba(179, 50, 93, 0.x)` y similares) — reemplazar por
  sombras neutras (`rgba(0, 0, 0, 0.05-0.10)`).
- Saturaciones >70% en colores semánticos.

### R11 — Modo "alto contraste" (opcional pero recomendado)

Añadir una variante:

```css
@media (prefers-contrast: more) {
  :root {
    --color-text-primary:    #000000;
    --color-text-secondary:  #1A1A1A;
    --color-border:          #6B6B6B;
    --nav-sidebar-text:      #1A1A1A;
  }
}
```

### R12 — Soporte `prefers-reduced-motion`

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### R13 — Sin regresión funcional

Después de aplicar la paleta:
- `python init.py` verde.
- 715+ tests verdes (sync_tokens debe pasar tras regenerar).
- Todas las páginas siguen siendo funcionales (los selectores CSS no cambian; solo
  cambian valores de variables).

### R14 — Reporte visual

El implementer entrega en `progress/impl_12c.md`:
- Lista de páginas verificadas visualmente (mínimo: login, inicio, planilla de
  notas, asistencia, informes, configuración SIE, estudiantes).
- Captura mental (descripción textual) de cómo se ve cada una.
- Cualquier sorpresa: contraste insuficiente, color que se vio "sucio", componente
  que necesitó ajuste fino.

## Requisitos no funcionales

- **Contraste WCAG AA mínimo** en todas las combinaciones texto/fondo del sistema.
- **Sin emojis.**
- **Sin nuevas dependencias.** Solo cambia CSS + tipografías Google Fonts ya soportadas.
- **Performance:** quitar `backdrop-filter` mejora frame rate en equipos viejos
  (un ganancia colateral importante en colegios con hardware modesto).
