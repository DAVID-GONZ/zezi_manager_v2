# Tareas: backend_17_contratos_componentes

> SCOPE — archivos que pueden editarse:
> `docs/design_system/components.md` (crear),
> `scripts/extract_component_info.py` (crear, auxiliar).
>
> Fuera de scope: codigo CSS, componentes Python, paginas.
>
> No depende de la API REST. Puede ejecutarse en paralelo con Fase 3.

---

## T1 — Script de extraccion auxiliar

Crear `scripts/extract_component_info.py` que por cada archivo en
`styles/components/`:
- Extraiga los selectores CSS (clases).
- Extraiga los tokens consumidos (`var(--...)`).
- Extraiga las variantes (sufijos BEM).
- Imprima un resumen por componente.

**Verificacion:** el script lista al menos 15 componentes con sus clases
y tokens.

---

## T2 — Estructura del catalogo

Crear `docs/design_system/components.md` con:
- Seccion "Como usar este catalogo".
- Un H2 vacio por cada uno de los 18 componentes de R4.

---

## T3 — Documentar componentes basicos (1-6)

Completar las secciones de:
Badge, Button, Card, Stat Card, Alert, Page Header.

Para cada uno: proposito, variantes, estados, clases, tokens, a11y, ejemplo.

**Verificacion:** cada seccion tiene las 7 dimensiones completas.

---

## T4 — Documentar componentes de formulario (7-10, 18)

Completar las secciones de:
Input, Select, Checkbox/Toggle, Form Field (field_*, filter_*, inline_*).

Leer `form_fields.py` para entender los helpers.

---

## T5 — Documentar componentes de estructura (11-17)

Completar las secciones de:
Table, Dialog, Menu, Toast, Tabs, Activity Feed, Layout.

---

## T6 — Revision cruzada contra CLASS_CONTRACT.md

Verificar que:
- Toda clase del CLASS_CONTRACT aparece en al menos un componente.
- Todo componente del catalogo usa clases del CONTRACT.
- No hay componentes huerfanos ni clases sin documentar.

---

## T7 — Cierre

El catalogo esta completo con 18 componentes documentados.
No modifica codigo ni CSS.

**Artefacto:** `progress/impl_backend_17.md`.
