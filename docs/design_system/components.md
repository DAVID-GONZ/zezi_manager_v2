# Catálogo de componentes — Design System «Aula Serena»

> **Versión:** 2026-09-28  
> **Proyecto:** AVEDRA (ex ZECI Manager v2)  
> **Stack actual:** Python / NiceGUI + Quasar (Core CSS portable a Vue)

---

## Propósito de este catálogo

Este documento es la referencia canónica de los 18 componentes del design system
«Aula Serena». Está dirigido a cualquier implementer —hoy en NiceGUI, mañana en
Vue— que necesite saber **qué clases CSS aplicar, qué tokens consumen y cómo
instanciarlos correctamente**.

**Cómo usarlo:**

1. Busca el componente por nombre.
2. Lee las clases CSS en la sección «Clases CSS» — esas son las únicas clases
   que debes aplicar; nunca escribas estilos inline.
3. Usa los helpers Python documentados en «Ejemplo (NiceGUI)»; no llames a
   `ui.input`, `ui.select` u otros widgets Quasar directamente desde páginas.
4. Para el fork Vue: aplica las mismas clases CSS. El CSS core transfiere
   intacto porque no contiene selectores `.q-*`, `.ag-*` ni `.nicegui-*` fuera
   de `styles/adapter/`.

**Archivo de contrato público:** [`src/interface/design/styles/CLASS_CONTRACT.md`](../../src/interface/design/styles/CLASS_CONTRACT.md)

---

## 1. badge

**Propósito:** Indicador visual de estado, categoría o nivel. Se usa inline en
tablas, cabeceras y listas para comunicar un estado con color + texto corto.

**Clases CSS:**
- Base: `.badge`
- Variantes semánticas: `.badge-success` · `.badge-warning` · `.badge-error` · `.badge-info` · `.badge-neutral` · `.badge-primary` · `.badge-purple`
- Variantes de asistencia: `.badge-P` · `.badge-FJ` · `.badge-FI` · `.badge-R` · `.badge-E`
- Variantes de desempeño: `.badge-bajo` · `.badge-basico` · `.badge-alto` · `.badge-superior`
- Variantes de convivencia (ag-grid cellClass únicamente): `.badge-fortaleza` · `.badge-dificultad` · `.badge-compromiso` · `.badge-citacion` · `.badge-descargo`

**Variantes:**

| Variante | Uso |
|---|---|
| `success` | Estado correcto, presente, aprobado |
| `warning` | Advertencia, retardo, riesgo |
| `error` | Error, falta, suspendido |
| `info` | Información neutral |
| `neutral` | Estado sin carga semántica |
| `primary` | Destacado en color principal |
| `purple` | Retardo de asistencia |
| `P/FJ/FI/R/E` | Códigos de asistencia |
| `bajo/basico/alto/superior` | Niveles de desempeño académico |

**Estados:** normal (único estado; no tiene hover ni disabled propio)

**Tokens consumidos:**
- `var(--radius-sm)`
- `var(--font-size-label)`
- `var(--color-success)` · `var(--color-success-light)`
- `var(--color-warning)` · `var(--color-warning-light)`
- `var(--color-error)` · `var(--color-error-light)`
- `var(--color-info)` · `var(--color-info-light)`
- `var(--color-surface-alt)` · `var(--color-text-secondary)`
- `var(--color-primary)` · `var(--color-primary-lighter)`
- `var(--attend-presente-bg)` · `var(--attend-presente)` (y demás tokens `attend-*`)
- `var(--desempeno-bajo-bg)` · `var(--desempeno-bajo)` (y demás tokens `desempeno-*`)

**Accesibilidad:** No es interactivo; no requiere `role`. Si comunica estado
crítico, añade `aria-label` al contenedor padre. Contraste garantizado ≥ 4.5:1
en modo claro y oscuro por tokens semánticos.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.status_badge import status_badge, badge_asistencia

# Badge genérico
status_badge("Activo", "success")        # → <span class="badge badge-success">Activo</span>
status_badge("Pendiente", "warning")

# Badge de asistencia
badge_asistencia("P")   # Presente
badge_asistencia("FJ")  # Falta justificada
```

---

## 2. button

**Propósito:** Acción explícita del usuario. Existen cuatro variantes de
intención y dos modificadores de tamaño.

**Clases CSS:**
- Base: `.btn`
- Variantes: `.btn-primary` · `.btn-secondary` · `.btn-danger` · `.btn-ghost`
- Icono solo: `.btn-icon` · `.btn-icon-sm`
- Tamaños: `.btn-sm` · `.btn-lg` (modifica la base)

**Variantes:**

| Clase | Uso |
|---|---|
| `.btn-primary` | Acción principal de la vista (CTA único) |
| `.btn-secondary` | Acción secundaria, confirmar sin riesgo |
| `.btn-danger` | Acción destructiva (eliminar, revocar) |
| `.btn-ghost` | Acción de baja prioridad o en toolbar |
| `.btn-icon` | Solo icono, forma circular (36 × 36 px) |

**Estados:**
- `normal` — color base de la variante
- `hover` — fondo más oscuro / tinte primario
- `disabled` — fondo `var(--color-disabled-bg)`, cursor `not-allowed`
- `focus` — anillo de foco `outline-offset: 2px` (nativo del navegador)

**Tokens consumidos:**
- `var(--space-sm)` · `var(--space-lg)`
- `var(--radius-md)`
- `var(--font-family)` · `var(--font-size-body)` · `var(--font-size-small)` · `var(--font-size-h4)`
- `var(--transition-base)`
- `var(--btn-height)` · `var(--btn-height-sm)` · `var(--btn-height-lg)`
- `var(--color-primary)` · `var(--color-primary-dark)` · `var(--color-primary-hover)` · `var(--color-primary-contrast)` · `var(--color-primary-lighter)`
- `var(--color-error)` · `var(--color-error-dark)`
- `var(--color-disabled-bg)` · `var(--color-disabled-text)`
- `var(--color-text-secondary)` · `var(--color-text-primary)` · `var(--color-surface-alt)`

**Accesibilidad:** Elemento `<button>` nativo. El foco por teclado es nativo.
Para `.btn-icon` añade `aria-label` descriptivo.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger, btn_ghost

btn_primary("Guardar", on_click=guardar, icon="save")
btn_secondary("Cancelar", on_click=cerrar)
btn_danger("Eliminar", on_click=confirmar_eliminar, icon="delete")
btn_ghost("Ver más", on_click=ver_detalle)
```

---

## 3. card

**Propósito:** Superficie base de contenido. Agrupa información relacionada
con borde, sombra y radio estándar.

**Clases CSS:**
- Base: `.andes-card`

**Variantes:** Sin variantes propias; el contenido interno la especializa.

**Estados:**
- `normal` — sombra `var(--shadow-card)`, borde `var(--color-border)`

**Tokens consumidos:**
- `var(--color-surface)`
- `var(--color-border)`
- `var(--radius-lg)`
- `var(--space-lg)`
- `var(--shadow-card)`

**Accesibilidad:** Elemento neutro (`<div>`). Si es interactiva, añade
`role="button"` y `tabindex="0"` al wrapper.

**Ejemplo (NiceGUI):**

```python
from nicegui import ui

with ui.element("div").classes("andes-card"):
    ui.label("Título de la tarjeta").classes("section-title-lg")
    ui.label("Contenido de la tarjeta.")
```

---

## 4. stat-card

**Propósito:** Tarjeta de métrica / KPI con valor numérico destacado, ícono
flotante y acento lateral de color.

**Clases CSS:**
- Base: `.stat-card-wrapper`
- Modificadores de color: `.primary` · `.success` · `.warning` · `.error` · `.danger` · `.info`
- Hijos: `.stat-card-label` · `.stat-card-value` · `.stat-card-subtitle` · `.stat-card-icon-wrap`

**Variantes:** Color del acento lateral y del fondo del ícono según modificador.

**Estados:**
- `normal` — sombra `var(--shadow-card)`
- `hover` — eleva `translateY(-2px)`, sombra `var(--shadow-md)`

**Tokens consumidos:**
- `var(--color-surface)` · `var(--color-divider)`
- `var(--radius-lg)` · `var(--radius-md)`
- `var(--shadow-card)` · `var(--shadow-md)`
- `var(--transition-base)`
- `var(--font-size-small)`
- `var(--color-primary-darker)` · `var(--color-primary-lighter)`
- `var(--color-success)` · `var(--color-success-light)`
- `var(--color-warning)` · `var(--color-warning-light)`
- `var(--color-error)` · `var(--color-error-light)`
- `var(--color-info)` · `var(--color-info-light)`
- `var(--color-text-secondary)` · `var(--color-text-primary)`

**Accesibilidad:** No interactivo. Si contiene datos críticos, añade
`aria-label` con el valor completo.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.stat_card import stat_card

stat_card("Total estudiantes", 342, "school", subtitulo="+12 este mes")
stat_card("Promedio general", "4.1", "bar_chart", variante="success")
stat_card("Faltas sin justificar", 18, "warning", variante="danger")
```

---

## 5. alert

**Propósito:** Banner de retroalimentación contextual fijo en el layout de un
formulario o página. Para retroalimentación efímera usar `toast`.

**Clases CSS:**
- Base: `.alert`
- Variantes: `.alert--error` · `.alert--warning` · `.alert--success` · `.alert--info`

**Variantes:**

| Clase | Uso |
|---|---|
| `.alert--error` | Error de validación, fallo crítico |
| `.alert--warning` | Advertencia que no bloquea el flujo |
| `.alert--success` | Confirmación positiva inline |
| `.alert--info` | Información contextual neutral |

**Estados:** normal (único estado; no es interactivo)

**Tokens consumidos:**
- `var(--radius-md)`
- `var(--space-md)` · `var(--space-sm)`
- `var(--font-size-body)`
- `var(--color-error)` · `var(--color-error-light)`
- `var(--color-warning)` · `var(--color-warning-light)`
- `var(--color-success)` · `var(--color-success-light)`
- `var(--color-info)` · `var(--color-info-light)`

**Accesibilidad:** Añade `role="alert"` para que lectores de pantalla lo
anuncien inmediatamente. En modo oscuro los colores de texto se ajustan
automáticamente vía tokens para garantizar ≥ 4.5:1.

**Ejemplo (NiceGUI):**

```python
from nicegui import ui

# Alerta de error en un formulario de login
with ui.element("div").classes("alert alert--error").props('role="alert"'):
    ui.label("Credenciales incorrectas. Inténtalo de nuevo.")
```

---

## 6. page-header

**Propósito:** Cabecera estándar de cada página con título, subtítulo, ícono
y botones de acción alineados a la derecha.

**Clases CSS:**
- Wrapper: `.page-header-row`
- Hijos: `.page-header-title` · `.page-header-sub`

**Variantes:** Sin variantes; el contenido (botones, ícono) lo especializa.

**Estados:** normal (no es interactivo en sí mismo)

**Tokens consumidos:**
- `var(--space-lg)` · `var(--space-md)`
- `var(--color-divider)`
- `var(--font-family)`
- `var(--ink-700)` (título) · `var(--graphite-500)` (subtítulo)
- `var(--font-size-body)`

**Accesibilidad:** El título debe ser un `<h1>` semántico o mapearse al nivel
correcto de jerarquía. El helper Python usa `ui.label`; en Vue usa `<h1>`.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.page_header import page_header

page_header(
    titulo="Gestión de Estudiantes",
    subtitulo="Lista completa de estudiantes activos",
    icono="school",
    acciones=[
        {"label": "Nuevo", "on_click": crear, "icono": "add", "variante": "primary"},
        {"label": "Exportar", "on_click": exportar, "icono": "download", "variante": "secondary"},
    ],
)
```

---

## 7. section-panel

**Propósito:** Panel con cabecera estándar (ícono + título) que envuelve una
sección de contenido. Equivalente a un `<section>` con borde y sombra.

**Clases CSS:**
- Base: `.panel-card`
- Hijos: `.panel-header` · `.panel-title`

**Variantes:** Sin variantes; el color del ícono se pasa como parámetro.

**Estados:** normal

**Tokens consumidos:**
- `var(--color-surface)` · `var(--color-divider)`
- `var(--radius-xl)`
- `var(--space-lg)` · `var(--space-md)` · `var(--space-sm)`
- `var(--shadow-card)`
- `var(--font-size-h4)` · `var(--color-text-primary)`

**Accesibilidad:** Usa `<div>` semántico. En Vue conviene envolverlo en
`<section aria-labelledby="...">`.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.section_panel import section_panel

with section_panel("Actividad reciente", "history"):
    ui.label("Aquí va el contenido del panel.")
```

---

## 8. input

**Propósito:** Campo de texto, número o fecha con etiqueta estática Formik-style
(label arriba), estado de foco y error, placeholder y hint.

**Clases CSS:**
- Base: `.andes-input` (aplicada al widget Quasar)
- Wrappers de layout: `.form-field-wrap` · `.form-field-label-row`
- Etiqueta: `.form-field-label` · `.form-field-req`
- Textos auxiliares: `.form-field-hint` · `.form-field-error-msg`
- Textarea: añadir `.andes-textarea`

**Variantes:** Misma clase base para `text`, `number`, `date`, `time`,
`password`, `email` y `textarea`.

**Estados:**
- `normal` — borde `var(--color-border)` 1.5 px
- `focus` — borde `var(--color-primary)` 2 px + ring `var(--color-primary-lighter)`
- `error` — borde `var(--color-error)` 2 px + ring error
- `disabled` — fondo `var(--color-surface-alt)`, cursor `not-allowed`

**Tokens consumidos:**
- `var(--radius-md)`
- `var(--color-surface)` · `var(--color-surface-alt)` · `var(--color-border)`
- `var(--color-primary)` · `var(--color-primary-lighter)`
- `var(--color-error)` · `var(--color-text-disabled)`
- `var(--font-size-body)` · `var(--font-family)` · `var(--color-text-primary)` · `var(--color-text-secondary)`
- `var(--font-size-small)` · `var(--font-size-label)`

**Accesibilidad:** El widget Quasar genera `<input>` nativo con `id`; la
etiqueta usa `for` implícito. Añade `aria-required="true"` en campos
obligatorios. El estado de error debe acompañarse de `aria-describedby`
apuntando al mensaje de error.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.form_fields import field_input, field_number, field_date

field_input("Nombre completo", placeholder="Ej: Ana García", requerido=True)
field_number("Edad", placeholder="15")
field_date("Fecha de nacimiento")
```

---

## 9. select

**Propósito:** Selector de opciones de una lista fija o dinámica.
Mismas clases que `input` (`.andes-input`) aplicado a un `ui.select`.

**Clases CSS:**
- Base: `.andes-input` (mismo contrato que input)
- El popup flotante (`.q-menu`) se estiliza en `styles/adapter/` para modo oscuro.

**Variantes:** Sin variantes propias; se diferencia del input solo por el tipo
de widget subyacente.

**Estados:** Igual que `input` (normal · focus · disabled)

**Tokens consumidos:** Iguales que `input` más:
- `var(--color-text-secondary)` (ícono del dropdown)
- `var(--color-surface-high)` (fondo del popup en modo oscuro)

**Accesibilidad:** El `<select>` nativo de Quasar es accesible por teclado.
El popup usa `role="listbox"` internamente.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.form_fields import field_select, filter_select

# En formulario
field_select("Grado", options=["9A", "9B", "10A"], requerido=True)

# En toolbar de filtros
filter_select("Estado", options=["Activo", "Inactivo"])
```

---

## 10. checkbox

**Propósito:** Casilla de verificación para opciones booleanas o selección
múltiple en listas.

**Clases CSS:** Se aplica `.andes-input` al widget Quasar `ui.checkbox` con
`dense`. El contrato de clases no define selector específico de checkbox;
el estilado proviene de la clase base y del adapter Quasar.

**Variantes:** Sin variantes propias de color.

**Estados:**
- `normal` — borde `var(--color-border)`
- `checked` — color de marca `var(--color-primary)`
- `disabled` — opacidad reducida

**Tokens consumidos (inferido):**
- `var(--color-primary)` (marca activa)
- `var(--color-border)`

**Accesibilidad:** El elemento `<input type="checkbox">` nativo. Añade
`aria-label` cuando no hay texto visible.

**Ejemplo (NiceGUI):**

```python
from nicegui import ui

# Checkbox directo (casos simples)
ui.checkbox("Notificar por email").props("dense").classes("andes-input")

# En lista de selección múltiple (ag-grid maneja su propio checkbox)
```

---

## 11. table

**Propósito:** Tabla de datos con ag-Grid (para tablas grandes y editables) o
`ui.table` de NiceGUI (para tablas simples con paginación y búsqueda).

**Clases CSS:**
- Tabla HTML pura: `.andes-table` → `th` · `td`
- ag-Grid helpers: `.data-table-root` · `.data-table-search` · `.data-table-clickable`
- Colores de desempeño (ag-Grid cellClass): `.grade-bajo` · `.grade-basico` · `.grade-alto` · `.grade-superior`
- Toolbar de filtros: `.panel-toolbar` · `.panel-toolbar-spacer`
- Acciones por fila: `.row-actions` · `.row-actions-item` · `.row-actions-name`

**Variantes:**
- Tabla HTML: `.andes-table` para listas simples
- NiceGUI `ui.table`: encapsulada por `data_table()`
- ag-Grid: wrapper `aggrid-scroll-wrapper` con altura fija

**Estados:**
- `normal` — fondo `var(--color-surface-alt)` en cabecera
- `hover fila` — fondo `var(--color-bg)`

**Tokens consumidos:**
- `var(--color-surface)` · `var(--color-surface-alt)` · `var(--color-bg)`
- `var(--font-size-table)` · `var(--font-size-small)` · `var(--font-size-label)`
- `var(--radius-lg)` · `var(--radius-md)`
- `var(--space-md)` · `var(--space-sm)` · `var(--space-xs)`
- `var(--shadow-card)`
- `var(--color-divider)` · `var(--color-border)`
- `var(--color-text-secondary)` · `var(--color-text-primary)`
- `var(--table-header-height)` · `var(--table-row-height)`
- `var(--desempeno-bajo-bg)` · `var(--desempeno-bajo)` (y demás tokens desempeño)

**Accesibilidad:** Usa `<table>` semántico con `<th scope="col">` para la
cabecera. ag-Grid genera su propia estructura ARIA; añade `aria-label` al
wrapper.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.data_table import data_table

columnas = [
    {"name": "nombre", "label": "Nombre", "field": "nombre", "sortable": True},
    {"name": "grado",  "label": "Grado",  "field": "grado"},
]
filas = [{"nombre": "Ana García", "grado": "10A"}]
data_table(columnas, filas, titulo="Estudiantes", on_row_click=ver_detalle)
```

---

## 12. dialog

**Propósito:** Modal de formulario CRUD o de confirmación. Bloquea el fondo y
centra el contenido.

**Clases CSS (form dialog):**
- Base: `.form-dialog-card`
- Variantes de acento: `.variant-danger` · `.variant-warning` · `.variant-info` · `.variant-success`
- Anchos: `.form-dialog-card-sm` · `.form-dialog-card-md` · `.form-dialog-card-lg` · `.form-dialog-card-xl`
- Hijos: `.form-dialog-header` · `.form-dialog-body` · `.form-dialog-title` · `.form-dialog-subtitle` · `.form-dialog-actions`
- Ícono del header: `.form-dialog-icon`

**Clases CSS (confirm dialog):**
- Base: `.confirm-dialog-card`
- Hijos: `.confirm-dialog-head` · `.confirm-dialog-body` · `.confirm-dialog-foot`

**Variantes:** El acento de color en el header (borde superior + color del ícono) varía con `.variant-*`.

**Estados:**
- `normal` — `var(--shadow-modal)`, fondo `var(--color-surface)`

**Tokens consumidos:**
- `var(--color-surface)` · `var(--color-surface-alt)` · `var(--color-border)`
- `var(--radius-lg)` · `var(--radius-md)`
- `var(--shadow-modal)`
- `var(--space-md)` · `var(--space-sm)` · `var(--space-lg)`
- `var(--font-size-h4)` · `var(--font-size-small)` · `var(--font-size-body)`
- `var(--color-text-primary)` · `var(--color-text-secondary)`
- `var(--color-error)` · `var(--color-warning)` · `var(--color-info)` · `var(--color-success)`
- `var(--color-primary-lighter)` · `var(--color-primary)`

**Accesibilidad:** Quasar añade `role="dialog"` y `aria-modal="true"`.
Añade `aria-labelledby` apuntando al `.form-dialog-title`. El foco debe
moverse al primer elemento interactivo al abrir.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.form_dialog import form_dialog

form_dialog(
    titulo="Nuevo estudiante",
    campos=[
        {"name": "nombre", "label": "Nombre completo", "type": "text", "required": True},
        {"name": "grado",  "label": "Grado", "type": "select",
         "options": ["9A", "9B", "10A"]},
    ],
    on_submit=crear_estudiante,
    icono="person_add",
    tamaño="md",
)
```

---

## 13. menu

**Propósito:** Menú de navegación lateral (rail) con ítems de módulo. Se
construye en `app_layout` con el sidebar de NiceGUI; no hay una clase de
contrato específica para el rail porque su CSS vive en `styles/adapter/` (es
100% Quasar/NiceGUI-specific y no porta a Vue sin reescritura).

**Clases CSS:** Las clases de los ítems del menú lateral se definen en
`styles/adapter/` (fuera del scope del CSS core portátil).

**Variantes:** Ítem activo · ítem normal · ítem con badge de notificación.

**Estados:**
- `normal` — fondo transparente
- `hover` — tinte `var(--color-primary-lighter)`
- `activo` — borde lateral + color `var(--color-primary)`

**Tokens consumidos (inferido):**
- `var(--color-primary)` · `var(--color-primary-lighter)`
- `var(--color-surface)` · `var(--color-border)`

**Accesibilidad:** El drawer de Quasar genera `<nav>` con `role="navigation"`.
Cada ítem activo debe tener `aria-current="page"`.

**Ejemplo (NiceGUI):**

```python
# El menú de navegación se configura a través de app_layout() en theme.py.
# Cada módulo registra su ruta; el layout construye el drawer automáticamente.
from src.interface.design.theme import ThemeManager

# En el entrypoint de cada módulo:
ThemeManager.render_layout(
    page_titulo="Inicio",
    page_icono="space_dashboard",
)
```

---

## 14. toast

**Propósito:** Notificación efímera (4 s por defecto) en la esquina inferior
derecha. Para mensajes de éxito, error, advertencia o información tras una acción.

**Clases CSS:**
- Base: `.andes-toast`
- Variantes: `.andes-toast--info` · `.andes-toast--success` · `.andes-toast--warning` · `.andes-toast--error`

**Variantes:**

| Clase | Uso |
|---|---|
| `.andes-toast--info` | Información neutral |
| `.andes-toast--success` | Operación completada |
| `.andes-toast--warning` | Advertencia no crítica |
| `.andes-toast--error` | Fallo de operación (duración 6 s) |

**Estados:** entra por animación Quasar; `duracion_ms=0` requiere cierre manual.

**Tokens consumidos:**
- `var(--radius-md)`
- `var(--font-family)` · `var(--font-size-body)`
- `var(--shadow-lg)`
- `var(--color-surface)` · `var(--color-text-primary)`
- `var(--color-info)` · `var(--color-success)` · `var(--color-warning)` · `var(--color-error)`

**Accesibilidad:** Quasar usa `role="alert"` con `aria-live="assertive"` para
errores y `aria-live="polite"` para el resto. No requiere configuración extra.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.toast import (
    toast_success, toast_error, toast_warning, toast_info
)

toast_success("Grupo guardado correctamente")
toast_error("No se pudo conectar al servidor", titulo="Error de red")
toast_warning("El periodo ya está cerrado")
toast_info("Exportando PDF...", duracion_ms=0)  # Requiere cierre manual
```

---

## 15. tabs

**Propósito:** Navegación por pestañas dentro de una página o panel.
Divide contenido complejo en secciones sin salir de la vista.

**Clases CSS:** Las pestañas se construyen con `ui.tabs` / `ui.tab_panels`
de NiceGUI (wrapper Quasar). El CSS core no define selectores `.q-tab*`;
el estilado vive en `styles/adapter/`.

**Variantes:** Horizontal (por defecto) · vertical (si el layout lo requiere).

**Estados:**
- `activo` — subrayado + color `var(--color-primary)`
- `normal` — texto `var(--color-text-secondary)`
- `hover` — texto `var(--color-text-primary)`

**Tokens consumidos (inferido):**
- `var(--color-primary)`
- `var(--color-text-primary)` · `var(--color-text-secondary)`
- `var(--color-divider)`

**Accesibilidad:** Quasar genera `role="tablist"`, `role="tab"` y
`role="tabpanel"`. La pestaña activa tiene `aria-selected="true"`.

**Ejemplo (NiceGUI):**

```python
from nicegui import ui

with ui.tabs().classes("w-full") as tabs:
    ui.tab("asistencia", label="Asistencia", icon="today")
    ui.tab("notas",      label="Notas",      icon="grade")

with ui.tab_panels(tabs, value="asistencia").classes("w-full"):
    with ui.tab_panel("asistencia"):
        ui.label("Contenido de asistencia")
    with ui.tab_panel("notas"):
        ui.label("Contenido de notas")
```

---

## 16. activity-feed

**Propósito:** Línea de tiempo de actividades recientes con dot-indicator,
etiqueta, categoría y tiempo relativo.

**Clases CSS:**
- Ítem: `.activity-feed-item`
- Dot: `.activity-dot`
- Columna de texto: `.feed-text-col`
- Texto principal: `.feed-label`
- Texto secundario: `.feed-meta`
- Tiempo: `.feed-time`

**Variantes:** Sin variantes; usa el panel `.panel-card` como contenedor.

**Estados:** Los ítems son de solo lectura; el dot es decorativo.

**Tokens consumidos:**
- `var(--space-md)` · `var(--space-sm)`
- `var(--color-divider)`
- `var(--color-primary)` (dot)
- `var(--font-size-table)` · `var(--font-size-small)` · `var(--font-size-label)`
- `var(--color-text-primary)` · `var(--color-text-secondary)` · `var(--color-text-disabled)`

**Accesibilidad:** Lista semántica con `<ol>` o `<ul>` en Vue. En NiceGUI
usa `<div>`; añade `role="list"` al contenedor y `role="listitem"` a cada ítem.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.activity_feed import activity_feed, ActivityItem
from datetime import datetime

items = [
    ActivityItem("Matrícula registrada", "Estudiantes", datetime.now()),
    ActivityItem("Periodo cerrado", "Calendario", "2026-09-15T14:30:00"),
]
activity_feed(items, titulo="Actividad reciente", icono="history")
```

---

## 17. layout

**Propósito:** Estructura de página completa: rail de navegación lateral +
topbar + área de contenido. Es el contenedor raíz de todas las vistas
autenticadas.

**Clases CSS:** Las clases del layout viven en `styles/adapter/` (drawer
de Quasar, topbar). El CSS core solo aporta tokens de color y espaciado.

**Variantes:**
- Rail colapsado (ícono) vs expandido (ícono + texto)
- Topbar con buscador `.topbar-search` y campana `.topbar-notif`

**Estados:** El drawer tiene estado `open` / `mini` manejado por NiceGUI.

**Tokens consumidos (inferido):**
- `var(--color-surface)` · `var(--color-bg)` · `var(--color-border)`
- `var(--space-lg)` · `var(--space-md)`

**Accesibilidad:** El drawer usa `<nav>`. El `<main>` debe tener
`id="main-content"` y el skiplink apuntar a él.

**Ejemplo (NiceGUI):**

```python
# Se invoca desde cada página mediante el decorador de layout.
# Ver src/interface/design/theme.py → ThemeManager.render_layout()

from src.interface.design.theme import ThemeManager

ThemeManager.render_layout(
    page_titulo="Estudiantes",
    page_subtitulo="Listado y gestión",
    page_icono="school",
    page_acciones=[
        {"label": "Nuevo", "on_click": crear, "icono": "add", "variante": "primary"},
    ],
)
```

---

## 18. form-field

**Propósito:** Campo de formulario completo con label estático, widget de
entrada (input/select/textarea), hint y mensaje de error. Es la unidad
atómica de cualquier formulario.

**Clases CSS:**
- Wrapper: `.form-field-wrap`
- Fila de label: `.form-field-label-row`
- Label: `.form-field-label`
- Asterisco requerido: `.form-field-req`
- Icono de tooltip: `.form-field-tooltip-icon`
- Hint: `.form-field-hint`
- Error: `.form-field-error-msg`
- Campo: `.andes-input` (ver componente **input**)

**Variantes:** Determinadas por el tipo de widget interno (input, select,
number, date, textarea).

**Estados:** Los estados los hereda del widget `.andes-input` interno.

**Tokens consumidos:**
- `var(--font-size-small)` · `var(--font-size-label)`
- `var(--color-text-secondary)` · `var(--color-error)` · `var(--color-text-disabled)` (tooltip icon)
- `var(--space-xs)` (gap del wrapper)

**Accesibilidad:** La etiqueta está semánticamente asociada al widget por
Quasar. El mensaje de error se lee si se vincula con `aria-describedby`.
El asterisco `*` va acompañado del texto `aria-required="true"` en el input.

**Ejemplo (NiceGUI):**

```python
from src.interface.design.components.form_fields import (
    field_input, field_select, field_textarea, field_hint
)

# Campo de texto con label, requerido y hint
field_input(
    "Nombre completo",
    placeholder="Ej: Ana García López",
    requerido=True,
    tooltip="Nombre como aparece en el documento de identidad",
)
field_hint("Máximo 100 caracteres")

# Select con label requerido
field_select(
    "Grado",
    options=["9A", "9B", "10A", "10B"],
    requerido=True,
)

# Textarea para observaciones
field_textarea("Observaciones", placeholder="Escribe aquí...")
```

---

## Convenciones del contrato

Estas cuatro reglas son **no negociables** y las verifica `check_design.py`:

1. **Un componente = una clase base semántica** — describe el rol, no la
   apariencia. `.btn`, no `.azul-grande`.

2. **Las variantes cuelgan de la base** — `--variante` o `-codigo`; nunca
   copies el cuerpo de la base en cada variante (usa selector agrupado o
   herencia CSS).

3. **Nada de estilos inline** — salvo valores calculados marcados con el
   comentario `# DYNAMIC` en Python.

4. **Colores solo vía tokens** — `var(--…)` en CSS, `Colors.*` en Python,
   `tokens.ts` en Vue. Ningún hex ni rgb literal si existe un token semántico.
