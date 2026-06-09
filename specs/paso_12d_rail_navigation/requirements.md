# Requisitos — paso_12d_rail_navigation

## Contexto

El sidebar actual es un acordeón colapsable: en estado expandido ocupa 220 px y
empuja el contenido; en colapsado se esconde por completo (`translateX(-100%)`,
fix en paso 12a). El patrón crea la contradicción de "abro el menú = pierdo
ancho de planilla". Hoy el sidebar arranca colapsado por defecto, lo que delata
el problema.

Este paso reemplaza el patrón por **rail icon-only de 60 px siempre visible** +
**flyout flotante** para subitems al hover/click. Inspirado en VS Code, Notion,
Figma. No empuja el contenido.

## Alcance

- `src/interface/design/layout.py` — reescribir `_sidebar()` con patrón rail.
- `src/interface/design/styles/layout/sidebar.css` — CSS del rail y flyout.
- `src/interface/design/layout.py` — quitar toggle del topbar (innecesario).

**Fuera de scope:**
- Cambiar `NAV_ITEMS` (estructura de la información): paso 12e.
- Cambiar paleta: paso 12c (debe estar hecho).
- Soporte móvil/responsive completo: si lo abordamos sería un paso aparte.

## Dependencias

Bloqueado por **12a** (estructura modular) y **12c** (paleta Aula Serena, porque
el rail claro asume los nuevos tokens).

## Requisitos funcionales

### R1 — Rail siempre visible

`andes-sidebar` se reemplaza por `andes-rail`:

- Ancho fijo: 60 px (variable `--rail-width`).
- Fondo: `var(--nav-sidebar-bg)` (paper-050 en Aula Serena).
- Border-right: 1 px sutil.
- Posición: `fixed`, ocupa de `top: 60px` a `bottom: 0` (debajo del topbar).
- **Nunca se colapsa, nunca se esconde.** El toggle del topbar deja de existir.

### R2 — Iconos clickeables con tooltip

Cada item del rail es un icono Material Symbols centrado en una zona de 56 × 48 px
clickeable. Al hover, aparece:

- Tooltip a la derecha del icono con el label completo del item.
- Si el item tiene `children`, el tooltip indica "X submenús" y un chevron.

Click:
- Item sin hijos → navega (`ui.navigate.to(item.ruta)`).
- Item con hijos → abre el flyout (ver R3).

### R3 — Flyout flotante para subitems

El flyout es un panel flotante absoluto:

- Posición: anclado al icono padre (alineado top con el icono).
- Ancho: 240 px.
- Aparece a la **derecha** del rail (left: 60px del item).
- Fondo: `var(--color-surface)`.
- Sombra: `var(--shadow-lg)`.
- Border-radius: `var(--radius-lg)`.
- Z-index alto (encima del contenido, por debajo de modales).

Contenido:
- Header con el nombre del grupo en serif (`var(--font-display)`).
- Lista vertical de subitems con icono pequeño + label.
- Item activo destacado con fondo `var(--ink-100)` + barra izquierda accent.
- Subitem `pending` con candado o gris.

Comportamiento:
- Se abre al **click** del icono padre.
- Se cierra al click fuera, click en un subitem (después de navegar), o ESC.
- Hover sobre otro item del rail con hijos → cierra el flyout actual y abre el del nuevo.

### R4 — Indicador de sección activa

Para indicar qué sección está activa:

- Una **barra vertical de 3 px** a la izquierda del icono (color
  `var(--accent-600)`).
- El icono adopta `color: var(--ink-700)`.
- El fondo del item queda con un sutil `var(--ink-100)`.

Para grupos con hijos, el padre se marca activo cuando alguna ruta hija coincide
con `ruta_activa`.

### R5 — Logo institucional

En la cabecera del rail (top, 56 px de alto):

- Si hay logo institucional: imagen cuadrada 36 × 36 px centrada.
- Si no: monograma en serif con las iniciales del nombre de la app o de la
  institución (1-2 letras), color `var(--ink-700)`.

Tooltip al hover: nombre de la institución.

### R6 — Eliminar toggle del topbar

El botón "toggle sidebar" del topbar (`topbar-toggle-btn`) deja de existir. El rail
no necesita toggle. El topbar se simplifica: brand area (sin toggle), page title,
context chip, page actions, logo institucional, user block.

### R7 — Accesibilidad

- Cada item del rail tiene `aria-label` con el label completo.
- Item activo: `aria-current="page"`.
- Item con hijos: `aria-expanded="true|false"`, `aria-haspopup="menu"`.
- El flyout tiene `role="menu"`; sus items, `role="menuitem"`.
- Navegable con teclado: Tab para iconos del rail, Enter para abrir flyout,
  flechas para moverse en el flyout, ESC para cerrar.

### R8 — Comportamiento responsive

En pantallas < 768 px (poco común en este software desktop-primary, pero por
robustez):
- El rail sigue siendo de 60 px (no se oculta).
- Los flyouts se anclan considerando el viewport (no se salen por la derecha).

### R9 — Sin regresión funcional

- Todas las rutas siguen accesibles.
- Filtrado por rol intacto (`_usuario_puede_ver`).
- `python init.py` verde.
- Tests verdes.

### R10 — Reporte visual

`progress/impl_12d.md` describe:
- Captura mental del rail con cada sección.
- Comportamiento del flyout (animación entrada/salida).
- Cualquier ajuste fino que tuviera que hacer.

## Requisitos no funcionales

- **Sin nuevas dependencias** — JS/CSS puro NiceGUI.
- **Sin emojis.**
- **Animación de flyout:** ≤150 ms, easing suave; respeta `prefers-reduced-motion`.
- **Performance:** un solo flyout instanciado a la vez, no uno por item.
