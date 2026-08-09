# Tasks: mejora_10b — Responsive y mobile-first

Prerrequisitos: ninguno. Desktop (≥1280px) debe quedar visualmente idéntico.

---

## T1 — Tokens de breakpoint

**Archivo:** `src/interface/design/styles/tokens.css`
- Añadir en `:root`: `--bp-sm: 560px; --bp-md: 768px; --bp-lg: 1024px; --bp-xl: 1280px;`.
- Comentario explicando que `@media` usa los valores literales (CSS no interpola vars en media).

---

## T2 — Tipografía y padding fluidos

**Archivo:** `src/interface/design/styles/tokens.css`
- Convertir `--font-size-h1`/`-h2`/`-h3` a `clamp(min, preferido, MÁX)` con el MÁX = valor actual.
- `--content-padding: clamp(16px, 4vw, 24px)`.
- **No** tocar `--font-size-body/-small/-label/-table` (legibilidad fija).
- *criterio*: en 1280px el render es idéntico (el clamp topa en el máximo).

---

## T3 — Consolidar breakpoints existentes a la escala

**Archivos:** los `@media` de `cards.css`, `reset.css`, `sidebar.css`, `content.css`, dominios.
- Donde no cambie el layout, alinear los `max-width: 1100/820/640/560` a `--bp-*`
  (768/1024/560). No forzar cambios visuales; solo homogeneizar.

---

## T4 — Navegación adaptativa (CSS)

**Archivos:** `layout/sidebar.css`, `layout/content.css`, `layout/topbar.css`
- `@media (max-width: 1023px)`: forzar modo rail (ancho `--rail-width`, ocultar labels).
- `@media (max-width: 767px)`: sidebar `position: fixed` off-canvas (translateX(-100%)),
  clase `.is-open` lo muestra + overlay; contenido a `margin-left: 0` / ancho completo.
- Mostrar el botón de menú del topbar solo bajo `--bp-md`.

---

## T5 — Toggle del drawer

**Archivo:** `src/interface/design/layout.py`
- Estado del drawer (abierto/cerrado) + handler del botón de menú del topbar que alterna
  la clase `.is-open` en el contenedor de navegación, y un overlay que cierra al click.
- Handlers como funciones nombradas (no lambdas con `__setitem__`). Sin lógica de dominio.

---

## T6 — No-overflow y táctil

**Archivos:** `components/tables.css`, `domain/horario_parrilla.css`, `reset.css`, `layout/topbar.css`
- Envolver grillas anchas en contenedor `overflow-x: auto`.
- Bajo `--bp-md`: botones icon-only y chips con `min-height: 44px; min-width: 44px`.
- Confirmar que el `body` no hace scroll horizontal en 360px.

---

## T7 — Verificación

- Manual en 360 / 768 / 1280 (DevTools responsive): sin scroll horizontal, drawer OK, desktop idéntico.
- `python scripts/check_design.py --all` y `python init.py` en verde.
- (Si `testing_ui_roadmap` ya tiene Playwright) añadir un test de viewport móvil.
