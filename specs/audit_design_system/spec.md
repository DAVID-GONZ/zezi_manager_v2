# Auditoría de Coherencia — Design System `design/*`

> **Tipo:** Diagnóstico / no implementar.  
> **Alcance:** `src/interface/design/` — `components/`, `layout.py`, `tokens.py`, `styles.css`, `theme.py`.  
> **Objetivo:** Catalogar componentes sin uso, código CSS muerto, tokens obsoletos y
> oportunidades de componentización. No se elimina ni modifica nada.

---

## 1. Componentes Python — inventario de uso real

Método: cruzar las exportaciones de `components/__init__.py` contra los imports
en todos los archivos de `pages/**/*.py` y el resto de `src/`.

### 1.1 Componentes sin ningún import en pages/

| Componente | Exportado en __init__ | Importado en pages/ | Usado internamente |
|---|---|---|---|
| `confirmation_card` | ✅ | ❌ | No (solo en su propio .py y __init__) |
| `page_header` | ✅ | ❌ | No |
| `data_table` | ✅ | ❌ | No |
| `performance_indicator` | ✅ | ❌ | No |
| `base_form` | ✅ | ❌ | **Sí** — importado por `form_dialog.py` |

**Diagnóstico:**
- `confirmation_card`, `page_header`, `data_table`, `performance_indicator` son
  componentes registrados en el design system que ninguna página activa consume.
  Pueden ser: (a) features planificadas nunca implementadas, (b) reemplazadas por
  implementación inline en las pages, o (c) candidatas a eliminación futura.
- `base_form` tiene un consumidor interno (`form_dialog`), por lo que no es
  código muerto aunque las pages no la importen directamente.

**Nota de contexto del historial de commits:**
Los pasos `paso_10i_design_system` y `paso_10j_component_adoption` agregaron estos
componentes con intención de adopción gradual. La adopción efectiva quedó limitada a
`stat_card`, `confirm_dialog`, `form_dialog`, `status_badge`, `badge_estado_general`
y los botones.

### 1.2 Componentes con uso real (baseline de salud)

| Componente | Páginas que lo importan |
|---|---|
| `app_layout` | Todas las pages excepto `login.py` |
| `btn_primary / secondary / danger / ghost / icon` | ~20 pages |
| `form_dialog` | ~12 pages (estudiantes, horarios, admin×4, evaluación×4, convivencia×2) |
| `confirm_dialog` | ~8 pages |
| `stat_card` | `inicio.py`, `estudiantes.py`, `tablero_estadisticos.py` |
| `status_badge` | `inicio.py`, `usuarios.py`, `habilitaciones.py`, `planes_mejoramiento.py`, `planilla_notas.py` |
| `badge_estado_general` | `asignaciones.py`, `configuracion_sie.py`, `usuarios.py` |
| `context_chip` | `layout.py` (topbar interno) |
| `abrir_selector` | `registro_asistencia.py` |
| `badge_asistencia` | Exportada pero no importada directamente por pages; `registro_asistencia.py` usa inline CSS |
| `badge_desempeno` | Exportada pero no importada por pages; `planilla_notas.py` usa CSS classes directas |

---

## 2. `layout.py` — análisis de coherencia interna

### 2.1 Parámetros silenciosamente descartados

`app_layout` acepta `page_icono` y `page_acciones` en su firma, pero la llamada
a `_topbar` en modo nuevo (líneas 541–547) **no los reenvía**:

```python
# layout.py L541-547 (modo nuevo)
_topbar(
    _ctx,
    page_titulo=page_titulo,
    page_subtitulo=page_subtitulo,
    toggle_callback=_toggle_sidebar,
    # ← page_icono y page_acciones: NUNCA pasados
)
```

Impacto: cualquier page que pase `page_icono=` o `page_acciones=` a `app_layout`
no verá el icono ni los botones de acción en el topbar. El parámetro se acepta sin error.

### 2.2 Bug en `_btn_topbar_accion` (línea 197)

```python
# layout.py L194-197
btn = ui.button(on_click=on_click).classes(...)
with btn:
    ...
btn = content   # ← reasigna la variable; el botón pierde su referencia
```

El botón con icono nunca renderiza su contenido de manera controlada. Esta función
está lista en el código pero `page_acciones` no llega a ella (ver 2.1), por lo que
el bug está dormido.

### 2.3 Topbar legacy (`_topbar_legacy`)

Función de ~40 líneas mantenida por compatibilidad. Verificación de uso: **ninguna
page en `pages/`** usa la firma legacy (`titulo_pagina=`, `usuario_nombre=`, etc.)
— todas usan la firma nueva `app_layout(ctx, contenido, ...)`. El path legacy existe
como resguardo pero es código muerto desde el punto de vista del flujo activo.

Diferencias respecto a `_topbar` nuevo que crea deuda visual:
- No renderiza `page_icono` ni `page_subtitulo`.
- El user block usa `ui.element("div")` donde el nuevo usa `ui.row()`.
- No tiene el override de context chip para fondo oscuro.

### 2.4 Clase `.andes-main.sidebar-collapsed` nunca aplicada

En `layout.py`, al colapsar el sidebar solo se aplica la clase `collapsed` al
elemento `nav`. La clase `.sidebar-collapsed` en `.andes-main` (CSS L460-463)
**nunca se aplica al `main_el`**. El area principal no ajusta su margen al colapsar.
El CSS que lo controlaría existe pero el Python no lo activa.

### 2.5 Sub-ítems de NAV_ITEMS usan strings literales para iconos

Los ítems del nivel superior usan `Icons.*` (correcto). Los sub-ítems de Calificaciones,
Convivencia, Informes y Administración usan strings crudos: `"table_chart"`, `"tune"`,
`"lock"`, `"lock_clock"`, `"comment"`, `"rule"`, etc. Esto rompe la trazabilidad
del design system: renombrar un icono en `Icons` no actualiza el sidebar.

---

## 3. `tokens.py` — valores fuera de sincronía con `styles.css`

| Token | Valor en tokens.py | Valor real en styles.css | ¿Sincronizado? |
|---|---|---|---|
| `Colors.TOPBAR_BG` | `"rgba(255, 255, 255, 0.82)"` | `linear-gradient(160deg, rgba(97,27,50,0.97) 0%, ...)` | ❌ Obsoleto |
| `Colors.TOPBAR_BORDER` | `"#E4E4E7"` | `rgba(255, 255, 255, 0.12)` | ❌ Obsoleto |
| `Colors.SIDEBAR_BG` | `"#18181B"` | Documentado como "base del gradient" — aceptable | ⚠️ Parcial |
| `Layout.SIDEBAR_WIDTH` | `180` | `220px` (CSS L163) | ❌ Desincronizado |
| `Layout.SIDEBAR_COLLAPSED` | `58` | No hay ancho en collapsed (usa `translateX(-100%)`) | ⚠️ No aplica |
| `Layout.TOPBAR_HEIGHT` | `60` | `60px` | ✅ |
| `Layout.CONTENT_PADDING` | `24` | `24px` | ✅ |

### 3.1 Icons constants sin ningún uso detectado

Los siguientes valores de `class Icons` nunca aparecen en ningún archivo `.py` de `src/`:

| Constante | Valor | Observación |
|---|---|---|
| `Icons.SETTINGS` | `"settings"` | `Icons.CONFIG = "tune"` cumple el rol en la app |
| `Icons.PIAR` | `"accessible"` | Feature PIAR no implementada |
| `Icons.GUARDIAN` | `"family_restroom"` | Feature acudientes no implementada |
| `Icons.DELETE` | `"delete"` | Las pages usan `btn_danger` con string literal o sin icono |
| `Icons.FILTER` | `"filter_list"` | No hay filtros con este icono |
| `Icons.CANCEL` | `"close"` | Botones cancelar usan la X de NiceGUI nativa |
| `Icons.CHECK` | `"check_circle"` | No utilizado |
| `Icons.ERROR` | `"error"` | Colisiona semánticamente con `Colors.ERROR`; no usado |
| `Icons.INFO` | `"info"` | No utilizado |
| `Icons.BACK` | `"arrow_back"` | No hay navegación "atrás" implementada |
| `Icons.REFRESH` | `"refresh"` | No usado; candidato a uso futuro real |
| `Icons.COLLAPSE` | `"expand_less"` | `Icons.EXPAND` sí se usa; COLLAPSE nunca |

**Total unused: 12 de 35 constantes (34%).**

### 3.2 Clase `Spacing` — uso real

`Spacing.XS/SM/MD/LG/XL/XXL` nunca se importan directamente en pages. El spacing
se consume vía clases CSS de NiceGUI (`gap-md`, `p-lg`, etc.) o via `--space-*`
variables CSS. La clase es documentación de los valores pero no tiene consumidores
Python activos.

---

## 4. `styles.css` — código muerto y redundancias

### 4.1 Bloques explícitamente marcados DEPRECATED

```css
/* DEPRECATED paso_10j: stat_card() ahora usa .stat-card-wrapper (ver más abajo) */
.stat-card         { ... }   /* L3171 */
.stat-card-header  { ... }   /* L3172 */
.stat-card-label   { ... }   /* L3173 */
.stat-card-value   { ... }   /* L3175 */
.stat-card-sub     { ... }   /* L3176 */
.stat-icon-circle  { ... }   /* L3177 */
```

Y el bloque de "compatibilidad" (nunca usado por código actual):
```css
.andes-stat-card  { ... }   /* L631 */
.andes-stat-value { ... }   /* L643 */
.andes-stat-label { ... }   /* L649 */
```

Ambos grupos existen junto al bloque `.stat-card-wrapper` (L526) que es el actual.

### 4.2 `.sidebar-toggle` definida, nunca aplicada desde Python

```css
/* styles.css L244-259 */
.sidebar-toggle { display: flex; ... }
.sidebar-toggle:hover { background: rgba(0,0,0,0.05); }
```

En `layout.py`, el botón toggle del topbar usa `.topbar-toggle-btn` (vía
`ui.element("div").classes("topbar-toggle-btn")`), pero la regla CSS de
`.topbar-toggle-btn` **no existe en styles.css**. La clase `.sidebar-toggle`
que sí está definida no se aplica. El botón funciona por herencia de `div` base.

### 4.3 Regla `.panel-title` duplicada

```css
/* L1645-1649 */
.panel-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); }

/* L1779-1783 (idéntica) */
.panel-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); }
```

Misma regla definida dos veces, mismo valor. La segunda sobreescribe la primera
sin cambio visible.

### 4.4 `.andes-main.sidebar-collapsed` (L460-463) — nunca activada

```css
.andes-main.sidebar-collapsed {
  margin-left: var(--sidebar-collapsed);
  width: calc(100vw - var(--sidebar-collapsed));
}
```

El Python (`layout.py`) nunca agrega ni quita la clase `sidebar-collapsed` al
elemento `.andes-main`. La clase existe en CSS para mover el contenido cuando
el sidebar colapsa, pero la lógica Python solo mueve el sidebar (con `translateX`),
no el área de contenido. Resultado: el contenido queda bajo el sidebar cuando este
está expandido (actualmente el sidebar parte colapsado por defecto para evitar esto).

### 4.5 `col-2`, `col-3`, `col-4` (L3031-3033) — utilidades de bootstrap-style

```css
.col-2 { flex: 0 0 16.666%; max-width: 16.666%; }
.col-3 { flex: 0 0 25%; max-width: 25%; }
.col-4 { flex: 0 0 33.333%; max-width: 33.333%; }
```

Grep en `src/`: ninguna page usa estas clases. Son utilidades heredadas o
pre-escritas; la app usa `form-grid-2`, `form-grid-3` y clases Tailwind/NiceGUI
en su lugar.

---

## 5. Candidatos a componentización desde `layout.py`

Las siguientes estructuras se construyen inline dentro de `_topbar` o `_sidebar`
y podrían extraerse como componentes reutilizables:

| Bloque inline | Ubicación | Beneficio de componentizar |
|---|---|---|
| User block (icon + nombre + rol + logout) | `_user_block_topbar()` | Ya es función; candidate a `components/user_avatar.py` |
| Logo institucional (img tag con fallback) | `_get_logo_institucional()` + render inline | Lógica BD + render mezclados |
| Badge de versión en sidebar footer | `ui.label("v2.0")` hardcoded | Versión hardcodeada, no viene de ninguna variable |
| `context_chip` en topbar | llamada directa | Ya componente, bien hecho |

---

## 6. Resumen ejecutivo

| Categoría | Cantidad | Severidad |
|---|---|---|
| Componentes Python sin uso real en pages | 4 | Media — no causa error, sí confusión |
| Parámetros de app_layout silenciosamente descartados | 2 (`page_icono`, `page_acciones`) | Alta — comportamiento sorpresivo |
| Bug activo en `_btn_topbar_accion` | 1 | Media (dormido por 2.1) |
| Topbar legacy activo pero sin consumidores | 1 | Baja — deuda técnica |
| Tokens Python desincronizados con CSS | 4 valores | Media |
| Icons constants nunca usadas | 12 / 35 | Baja — ruido en API |
| Bloques CSS marcados DEPRECATED | ~9 reglas | Baja — no afecta render |
| Regla CSS duplicada idéntica | 1 (`.panel-title`) | Baja |
| Clase CSS definida pero nunca aplicada desde Python | 2 (`.sidebar-toggle`, `.andes-main.sidebar-collapsed`) | Media |
| Utilidades CSS sin uso | 3 (`.col-2/3/4`) | Baja |
| Versión hardcodeada en sidebar | 1 | Baja |

---

*Generado: 2026-05-21. Base de código: commit `00bcbc0`.*
