# Requisitos: backend_17_contratos_componentes

> Ambito: documentar los componentes del design system como spec
> independiente de NiceGUI, para que el frontend Vue los reproduzca
> sin ingenieria inversa.
>
> Fase 5 del backend. Paralelo con la Fase 3.
>
> IMPORTA para el split: la documentacion viaja a `avedra-shared-contracts`
> y es la referencia del implementer de Vue (/migrate-page).

---

## Catalogo de componentes

R1: EL SISTEMA DEBE tener un documento `docs/design_system/components.md`
    que documente TODOS los componentes del design system.

R2: EL catalogo DEBE cubrir los componentes listados en
    `CLASS_CONTRACT.md` (fuente de verdad de clases CSS).

R3: CADA componente DEBE documentarse con:
    - **Nombre y proposito** — una linea.
    - **Variantes** — lista exhaustiva (ej: badge: success, warning, danger, info, neutral).
    - **Estados** — default, hover, focus, active, disabled, loading, error, empty.
    - **Props/atributos** — lo que el componente acepta (tamanio, variante, icono, etc.).
    - **Clases CSS** — las clases del CLASS_CONTRACT que aplica.
    - **Tokens** — que tokens consume (color, spacing, border-radius, etc.).
    - **A11y** — roles ARIA, navegacion por teclado, contraste.
    - **Ejemplo visual** — descripcion textual del render (no screenshot).

---

## Componentes a documentar

R4: LA lista minima incluye los componentes del CLASS_CONTRACT:
    1. Badge
    2. Button (primario, secundario, ghost, danger)
    3. Card
    4. Stat Card
    5. Alert/Notification (info, success, warning, error)
    6. Page Header
    7. Section Panel
    8. Input (text, number, email, password)
    9. Select
    10. Checkbox / Toggle
    11. Table / Data Grid
    12. Dialog/Modal
    13. Menu / Dropdown
    14. Toast/Snackbar
    15. Tabs
    16. Activity Feed (historial)
    17. Layout (sidebar, topbar, main)
    18. Form Field (field_*, filter_*, inline_*)

---

## Formato

R5: EL documento DEBE ser Markdown plano, legible por humanos y por
    agentes Claude. No usar formatos binarios ni herramientas externas.

R6: CADA componente DEBE tener su propia seccion con heading H2,
    siguiendo el orden de R4.

R7: EL documento DEBE incluir una seccion "Como usar este catalogo"
    al inicio, explicando que es la referencia para el fork Vue.

---

## Fuera de alcance

- Storybook o catalogo interactivo (eso es vue_06_storybook).
- Cambiar los componentes actuales.
- Documentar componentes de NiceGUI/Quasar (solo el contrato portable).
