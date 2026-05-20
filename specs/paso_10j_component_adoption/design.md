# Diseño técnico — paso_10j_component_adoption

## Arquitectura de referencia

```
src/interface/design/components/
  __init__.py            ← ya exporta todo; no cambios
  buttons.py             ← intacto (paso_10i ✅)
  stat_card.py           ← CAMBIAR: usar .stat-card-wrapper
  page_header.py         ← intacto (API correcta)
  confirm_dialog.py      ← intacto
  confirmation_card.py   ← CAMBIAR: eliminar style= estáticos
  status_badge.py        ← intacto
  performance_indicator.py ← intacto
  data_table.py          ← intacto
  base_form.py           ← intacto
  context_selector.py    ← intacto

src/interface/design/styles.css
  ← AÑADIR: .confirmation-card-danger, .confirmation-card-warning, .confirmation-card-info

src/interface/pages/
  inicio.py                    ← T2 (stat_card adoption)
  admin/grupos.py              ← T3 (page_header) + T4 (confirm_dialog) + T5 (badge)
  admin/asignaturas.py         ← T3 (page_header) + T4 (confirm_dialog) + T5 (badge)
  admin/asignaciones.py        ← T3 (page_header) + T4 (confirm_dialog) + T5 (badge)
  admin/usuarios.py            ← T3 (page_header) + T4 (confirm_dialog) + T5 (badge)
  admin/configuracion_sie.py   ← T3 (page_header) + T5 (badge)
  admin/configuracion_institucion.py ← T3 (page_header)
  academico/estudiantes.py     ← T2 (stat_card) + T3 (page_header) + T4 (confirm_dialog) + T5 (badge)
  academico/horarios.py        ← T3 (page_header)
  academico/tablero_estadisticos.py ← T2 (stat_card en _render_kpis)
  evaluacion/configuracion_evaluacion.py ← T4 (confirm_dialog) + T5 (badge)
  evaluacion/habilitaciones.py ← T4 (confirm_dialog) + T5 (badge)
  evaluacion/planes_mejoramiento.py ← T4 (confirm_dialog) + T5 (badge)
  evaluacion/planilla_notas.py ← T5 (badge — solo renders Python)
```

---

## §1 — Inventario de components y su estado post-10i

| Componente | CSS violations (post-10i) | Exportado | Usado en pages |
|---|---|---|---|
| `buttons.py` | 0 ✅ | ✅ | ✅ todas |
| `stat_card.py` | 1 ⚠️ style= dinámico OK, pero clase errónea | ✅ | ❌ 0 páginas |
| `page_header.py` | 0 ✅ | ✅ | ❌ 0 páginas |
| `confirm_dialog.py` | 0 ✅ | ✅ | ❌ 0 páginas |
| `confirmation_card.py` | 2 ❌ style= estáticos (bg + border) | ✅ | ❌ 0 páginas |
| `status_badge.py` | 0 ✅ | ✅ | ✅ solo inicio.py |
| `performance_indicator.py` | 0 ✅ (style= dinámicos justificados) | ✅ | ❌ 0 páginas |
| `data_table.py` | 0 ✅ | ✅ | ❌ 0 páginas |
| `base_form.py` | 1 ⚠️ style= `grid-template-columns: repeat({col},1fr)` | ✅ | ❌ 0 páginas |
| `context_selector.py` | 0 ✅ | ✅ | ✅ via layout.py |

**`base_form.py` — exception documentada:**
`style=f"grid-template-columns: repeat({columnas}, 1fr)"` — `columnas` es un
argumento de runtime → genuinamente dinámico. Es la única manera de CSS grid
variable. Queda como excepción documentada.

---

## §2 — Fix T1: `stat_card()` unificación de diseño

### Problema
El componente usa `.andes-card.stat-card` (layout horizontal: textos izquierda,
icono derecha). Las páginas usan `.stat-card-wrapper {variante}` (layout vertical:
icono arriba, texto abajo, borde coloreado izquierdo). Son diseños distintos;
las páginas usan el más rico visualmente.

### Solución
Actualizar `stat_card()` para producir el layout `.stat-card-wrapper`:

```python
# stat_card.py — implementación nueva
def stat_card(titulo, valor, icono, subtitulo="", variante="primary") -> ui.element:
    _ICON_COLORS = {
        "primary": "var(--color-primary)",
        "success": "var(--color-success)",
        "warning": "var(--color-warning)",
        "danger":  "var(--color-error)",
        "info":    "var(--color-info)",
    }
    icono_color = _ICON_COLORS.get(variante, "var(--color-primary)")

    card = ui.element("div").classes(f"stat-card-wrapper {variante}")
    with card:
        with ui.element("div").classes("stat-card-icon-wrap"):
            ThemeManager.icono(icono, size=22, color=icono_color)
        ui.label(titulo).classes("stat-card-label")
        ui.label(str(valor)).classes("stat-card-value")
        if subtitulo:
            ui.label(subtitulo).classes("stat-card-subtitle")
    return card
```

El import de `ThemeManager` ya existe en el módulo. Eliminar `_BG_MAP` y
`_COLOR_MAP` del bloque anterior (fueron del layout horizontal).

### CSS impacto
Las clases `.stat-card`, `.stat-card-header`, `.stat-icon-circle` (agregadas en
paso_10i) quedan orphan en styles.css. El implementer debe COMENTARLAS o
eliminarlas en styles.css y dejar una nota "deprecated por stat-card-wrapper".

---

## §3 — Fix T1b: `confirmation_card.py` CSS violations

### Problema
```python
card = ui.card().classes("andes-card").style(
    f"background:{bg_color}; border-left: 4px solid {icono_color};"
)
```
Aunque `bg_color` e `icono_color` provienen de un dict `_COLOR_MAP` de 3 entradas,
son estáticos desde el punto de vista CSS (no calculados en runtime, solo elegidos
por variante). → Violación R1.

### Solución
Agregar 3 clases a styles.css:
```css
/* confirmation_card.py — variantes */
.confirmation-card-danger {
  background: var(--color-error-light);
  border-left: 4px solid var(--color-error);
}
.confirmation-card-warning {
  background: var(--color-warning-light);
  border-left: 4px solid var(--color-warning);
}
.confirmation-card-info {
  background: var(--color-info-light);
  border-left: 4px solid var(--color-info);
}
```

En `confirmation_card.py`:
```python
# Antes:
card = ui.card().classes("andes-card").style(
    f"background:{bg_color}; border-left: 4px solid {icono_color};"
)
# Después:
card = ui.card().classes(f"andes-card confirmation-card-{variante}")
```

El título `ui.label(titulo).classes("font-h3").style(f"color:{icono_color}")`:
```python
# Antes:
ui.label(titulo).classes("font-h3").style(f"color:{icono_color}")
# Después:
# Agregar a styles.css:
# .confirmation-card-danger .confirm-card-title { color: var(--color-error); }
# .confirmation-card-warning .confirm-card-title { color: var(--color-warning); }
# .confirmation-card-info .confirm-card-title { color: var(--color-info); }
# En Python:
ui.label(titulo).classes("font-h3 confirm-card-title")
```

---

## §4 — T2: `page_header()` — patrón de migración por página

### Patrón base
```python
# IMPORTAR al inicio de la página:
from src.interface.design.components import page_header

# En la función contenido(), ANTES del primer panel-card:
page_header(
    titulo    = "Título de la Sección",
    subtitulo = "Descripción breve",
    icono     = Icons.X,
    acciones  = [
        {"label": "Nueva acción", "on_click": _abrir_crear, "icono": "add", "variante": "primary"},
    ],  # opcional — omitir si la página no tiene CTA en header
)

# DENTRO del primer panel-card: ELIMINAR el bloque:
# with ui.row().classes("items-center gap-2 mb-4"):
#     ThemeManager.icono(Icons.X, ...)
#     ui.label("Título").classes("text-xl font-bold")
```

### Tabla de adopción por página

| Página | titulo | subtitulo | icono | acciones |
|---|---|---|---|---|
| `grupos.py` | "Gestión de Grupos" | "Crea y administra los grupos académicos" | `Icons.GROUPS` | ninguna (crear está inline en panel) |
| `asignaturas.py` | "Gestión de Asignaturas" | "Áreas de conocimiento y asignaturas del currículo" | `Icons.SUBJECTS` | ninguna |
| `asignaciones.py` | "Asignaciones Docentes" | "Asignaciones de docentes a grupos y asignaturas" | `"assignment_ind"` | ninguna |
| `usuarios.py` | "Gestión de Usuarios" | "Administra cuentas de usuario y roles del sistema" | `Icons.TEACHERS` | `[{"label":"Nuevo usuario","on_click":_abrir_crear_usuario,"icono":"person_add","variante":"primary"}]` |
| `configuracion_sie.py` | "Configuración del SIE" | "Periodos académicos y año escolar activo" | `"settings"` | ninguna |
| `configuracion_institucion.py` | "Información Institucional" | "Datos básicos de la institución educativa" | `"business"` | ninguna |
| `estudiantes.py` | "Gestión de Estudiantes" | "Matrícula, seguimiento y PIAR de estudiantes" | `Icons.STUDENTS` | `[{"label":"Matricular","on_click":_abrir_dialog_matricula,"icono":"person_add","variante":"primary"}, {"label":"Carga CSV","on_click":_abrir_dialog_csv,"icono":"upload_file","variante":"secondary"}]` |
| `horarios.py` | "Horarios" | "Grilla semanal de horarios por grupo" | `Icons.SCHEDULE` | ninguna (o agregar "Nuevo bloque" si el rol lo permite) |

**Nota importante para `asignaciones.py`**: La función que abre el dialog de crear asignación
debe localizarse en el código. Si no existe como función nombrada, el implementer la extrae.

**Nota para `usuarios.py`**: El botón "Nuevo usuario" actualmente puede estar inline
dentro del panel. Si es así, se mueve a `acciones` de `page_header()`.

---

## §5 — T3: `confirm_dialog()` — tabla de sustitución

### Patrón base
```python
# ANTES:
def _eliminar_x(x_id: int, nombre: str) -> None:
    with ui.dialog() as dlg, ui.card():
        ui.label(f"¿Eliminar {nombre}? Esta acción es irreversible.")
        with ui.row().classes("gap-2 mt-4"):
            btn_ghost("Cancelar", on_click=dlg.close)
            btn_danger("Eliminar", on_click=lambda: _confirmar(dlg, x_id))
    dlg.open()

# DESPUÉS:
def _eliminar_x(x_id: int, nombre: str) -> None:
    confirm_dialog(
        titulo          = "Eliminar X",
        mensaje         = f"¿Eliminar {nombre}? Esta acción es irreversible.",
        on_confirm      = lambda: _confirmar(x_id),
        variante        = "danger",
        texto_confirmar = "Eliminar",
    )
```

Nota: `confirm_dialog()` ya abre el dialog internamente (`dialog.open()`). No
se llama `.open()` manualmente.

### Tabla de confirmaciones a migrar

| Página | Función | Trigger | Texto del dialog |
|---|---|---|---|
| `grupos.py` | `_eliminar_grupo()` | Botón eliminar en tabla | "¿Eliminar grupo {codigo}? Esta acción es irreversible." |
| `asignaturas.py` | `_eliminar_area()` aprox. | Botón eliminar área | "¿Eliminar el área {nombre}?" |
| `asignaturas.py` | `_eliminar_asignatura()` aprox. | Botón eliminar asignatura | "¿Eliminar la asignatura {nombre}?" |
| `asignaciones.py` | Confirm desactivar | Botón desactivar | "¿Desactivar la asignación?" |
| `usuarios.py` | `_desactivar_usuario()` aprox. | Botón desactivar | "¿Desactivar usuario {nombre}?" |
| `usuarios.py` | `_cambiar_rol()` aprox. | Botón cambiar rol | "¿Cambiar el rol de {nombre} a {nuevo_rol}?" |
| `estudiantes.py` | `_confirmar_retiro()` | Botón retirar en tabla | "¿Retirar a {nombre} de la matrícula?" |
| `configuracion_evaluacion.py` | Confirm borrar categoría | Botón eliminar categoría | "¿Eliminar la categoría {nombre}?" |
| `habilitaciones.py` | Confirm eliminar (si existe) | Botón eliminar | "¿Eliminar esta habilitación?" |
| `planes_mejoramiento.py` | Confirm cerrar plan | Botón cerrar plan | "¿Cerrar el plan de mejora?" variante="warning" |

**Nota:** El implementer debe localizar las funciones exactas en cada página.
Los nombres en la tabla son aproximados. El criterio es: `with ui.dialog()` con
solo `ui.label` (sin inputs) → candidato a `confirm_dialog()`.

### Diálogos que NO se tocan (CRUD forms)
- `grupos.py` → `_abrir_editar()` (contiene inputs)
- `asignaturas.py` → edit area, edit asignatura (contienen inputs)
- `asignaciones.py` → create asignacion dialog (contiene inputs)
- `usuarios.py` → create usuario dialog (contiene inputs)
- `horarios.py` → ambos dialogs (contienen inputs)
- `estudiantes.py` → dialogs de matricula, CSV, PIAR (contienen inputs)
- `cierre_periodo.py` → muestra conteo dinámico de estudiantes
- `cierre_anio.py` → similar
- `planilla_notas.py` → todos los dialogs con inputs de notas

---

## §6 — T4: `badge_*` — tabla de sustitución

### Importación necesaria
En cada página afectada, agregar al bloque de imports:
```python
from src.interface.design.components import badge_estado_general, status_badge
# (o badge_desempeno si se usan niveles académicos)
```

### Tabla de sustituciones

| Página | Patrón actual | Sustitución |
|---|---|---|
| `asignaciones.py` | `ui.badge("Activa").classes("w-20 badge-success")` | `badge_estado_general(True)` |
| `asignaciones.py` | `ui.badge("Inactiva").classes("w-20 badge-neutral")` | `badge_estado_general(False)` |
| `usuarios.py` | `ui.badge("Activo").classes("w-20 badge-success")` | `badge_estado_general(True)` |
| `usuarios.py` | `ui.badge("Inactivo").classes("w-20 badge-neutral")` | `badge_estado_general(False)` |
| `configuracion_sie.py` | `ui.badge("Activo").classes("badge-success")` | `badge_estado_general(True)` |
| `habilitaciones.py` | `ui.badge(estado).classes(f"... {_ESTADO_CLASES.get(...)}")` | `status_badge(estado, _ESTADO_CLASES.get(estado, "neutral"))` |
| `planes_mejoramiento.py` | `ui.badge(estado).classes(f"... {_ESTADO_CLASES.get(...)}")` | `status_badge(estado, _ESTADO_CLASES.get(estado, "neutral"))` |
| `planilla_notas.py` | `ui.badge(estado_val).classes(f"... {badge_clase}")` | `status_badge(estado_val.capitalize(), badge_clase_sin_prefijo)` — solo si es render Python, no JS |

### Excepciones explícitas (NO se migran)
- `ui.badge(str(n)).classes("badge-primary")` — contador numérico, queda inline
- `ui.badge(str(anio.anio)).classes("badge-primary")` — año, queda inline
- `ui.badge(a.codigo).classes("badge-neutral")` — código de asignatura, queda inline
- `ui.badge(f"{pct}%").classes(f"badge-...")` — porcentaje evaluación, queda inline
- Aggrid `cellRenderer` con HTML string → queda inline (contexto JS)

---

## §7 — T5: `performance_indicator()` — adopción diferida

Como se analizó en requirements.md R7, los usos actuales de barras de progreso
en las páginas son:
- `inicio.py`: `period-bar-track/period-bar-fill` → barra de TIEMPO del periodo, no
  desempeño académico. Diferente semántica. NO adoptar.
- `tablero_estadisticos.py`: gauge y donut son ECharts, no barras Python.

**El componente queda disponible pero sin adopción forzada en este paso.**
El implementer debe buscar con grep:
```
grep -rn "perf-bar-track\|perf-bar-fill" src/interface/pages/
```
Si encuentra alguna ocurrencia, sustituir con `performance_indicator()`.

---

## §8 — T6: Imports y actualización de `__init__.py`

`__init__.py` ya exporta todo correctamente (verificado). No requiere cambios.

En cada página que adopte un nuevo componente, agregar el import correspondiente:
```python
# Al inicio del archivo (bloque design system):
from src.interface.design.components import page_header
from src.interface.design.components import confirm_dialog
from src.interface.design.components import badge_estado_general, status_badge
from src.interface.design.components import stat_card
```

Agrupar los imports en un bloque como ya se hace con `btn_primary`, etc.

---

## §9 — Orden de implementación y dependencias

```
T1-CSS  →  styles.css: confirmation-card-* classes + deprecar stat-card / stat-icon-circle
T1-comp →  confirmation_card.py: eliminar style= estáticos
T1-stat →  stat_card.py: reescribir con .stat-card-wrapper
T2      →  inicio.py, tablero_estadisticos.py, estudiantes.py (stat_card adoption)
T3      →  8 páginas: page_header
T4      →  8 páginas: confirm_dialog (simples)
T5      →  6 páginas: badge_*
T6      →  Verificación: init.py + pytest
```

No hay dependencias circulares. T1-CSS debe ir antes que T1-comp y T1-stat.
T2/T3/T4/T5 son independientes entre sí y pueden hacerse en cualquier orden.

---

## §10 — Verificación final

```bash
# Grep de comprobación post-implementación
grep -rn "ui.badge(\"Activo\")\|ui.badge(\"Inactivo\")\|ui.badge(\"Activa\")\|ui.badge(\"Inactiva\")" src/interface/pages/
# → debe retornar 0 resultados

grep -rn "_stat_card(" src/interface/pages/
# → debe retornar 0 resultados

grep -rn "stat-card-wrapper" src/interface/pages/
# → debe retornar 0 resultados (solo en styles.css)

grep -rn "page_header" src/interface/pages/admin/ src/interface/pages/academico/
# → debe aparecer en cada una de las 8 páginas objetivo

grep -rn "confirm_dialog" src/interface/pages/
# → debe aparecer en las páginas objetivo (R5)

# Tests y harness
$env:PYTHONIOENCODING="utf-8"; python init.py
pytest tests/ -q
```
