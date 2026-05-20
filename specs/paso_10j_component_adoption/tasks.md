# Tasks — paso_10j_component_adoption

## Resumen de tareas

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T1 | CSS fixes + reparación de 2 componentes | styles.css, stat_card.py, confirmation_card.py | R1, R2, R10 |
| T2 | `stat_card()` adoptado en 3 páginas | inicio.py, tablero_estadisticos.py, estudiantes.py | R3 |
| T3 | `page_header()` adoptado en 8 páginas | admin/*, academico/estudiantes, academico/horarios | R4 |
| T4 | `confirm_dialog()` adoptado en 6 páginas | grupos, asignaturas, asignaciones, usuarios, estudiantes, configuracion_evaluacion | R5 |
| T5 | `badge_*` adoptado en 6 páginas | admin/*, evaluacion/* | R6 |
| T6 | Verificación final | — | R9 |

---

## T1 — CSS fixes + reparación de 2 componentes

### T1a — styles.css: agregar clases `confirmation-card-*` y deprecar `stat-card` orphan

**Archivo:** `src/interface/design/styles.css`

**Agregar** (en la sección de `confirmation_card.py` o junto al bloque de `.andes-card`):
```css
/* confirmation_card.py — variantes estáticas */
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

/* confirmation_card title color por variante */
.confirmation-card-danger  .confirm-card-title { color: var(--color-error);   }
.confirmation-card-warning .confirm-card-title { color: var(--color-warning); }
.confirmation-card-info    .confirm-card-title { color: var(--color-info);    }
```

**Deprecar** (comentar o eliminar): las clases `.stat-card`, `.stat-card-header`,
`.stat-icon-circle` que paso_10i agregó y que ya no se usarán tras la unificación.
Agregar comentario:
```css
/* DEPRECATED paso_10j: stat_card() ahora usa .stat-card-wrapper (ver más abajo) */
```

### T1b — `confirmation_card.py`: eliminar `style=` estáticos

**Archivo:** `src/interface/design/components/confirmation_card.py`

**Cambios:**
1. Eliminar `_COLOR_MAP` dict (ya no se necesita para el card)
2. Cambiar la línea del card de:
   ```python
   card = ui.card().classes("andes-card").style(
       f"background:{bg_color}; border-left: 4px solid {icono_color};"
   )
   ```
   a:
   ```python
   card = ui.card().classes(f"andes-card confirmation-card-{variante}")
   ```
3. Cambiar el título de:
   ```python
   ui.label(titulo).classes("font-h3").style(f"color:{icono_color}")
   ```
   a:
   ```python
   ui.label(titulo).classes("font-h3 confirm-card-title")
   ```
4. Mantener las variables `icono_color` e `icono_nombre` solo para el icono
   de ThemeManager (que sí necesita el color como argumento Python, no CSS).
   `_COLOR_MAP` se puede reducir a solo los valores de color para el icono:
   ```python
   _ICONO_MAP = {
       "danger":  ("var(--color-error)",   "warning"),
       "warning": ("var(--color-warning)", "warning"),
       "info":    ("var(--color-info)",    "info"),
   }
   icono_color, icono_nombre = _ICONO_MAP.get(
       variante, ("var(--color-warning)", "warning")
   )
   ```

**Verificación T1b:**
```bash
grep -n "style=" src/interface/design/components/confirmation_card.py
# → debe retornar 0 resultados
```

### T1c — `stat_card.py`: reescribir con `.stat-card-wrapper`

**Archivo:** `src/interface/design/components/stat_card.py`

**Implementación nueva del cuerpo de `stat_card()`:**
```python
def stat_card(
    titulo: str,
    valor: str | int | float,
    icono: str,
    subtitulo: str = "",
    variante: str = "primary",
) -> ui.element:
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

Eliminar: `_BG_MAP`, el bloque `with ui.row().classes("stat-card-header ...")`,
el `with ui.element("div").classes("stat-icon-circle")`.

Mantener: el docstring (actualizar el Returns para decir `ui.element` en vez de
`ui.card`). El import de `ThemeManager` ya está. No se necesita el import de
`_BG_MAP` / `_COLOR_MAP` duplicado.

Mantener `variante="danger"` en el dict aunque el CSS usa `.error` —
el argumento de Python `danger` sigue siendo válido, la CSS class será
`stat-card-wrapper danger`. Esto requiere que en styles.css exista
`.stat-card-wrapper.danger` (verifica; si no existe, añadir alias):
```css
/* Alias danger → error para stat-card-wrapper */
.stat-card-wrapper.danger { /* mismas propiedades que .warning pero rojo */ }
/* Si ya existe como .error, agregar .danger que hereda de .error */
.stat-card-wrapper.danger::before { background: var(--color-error); }
.stat-card-wrapper.danger .stat-card-icon-wrap { background: var(--color-error-light); }
```
Revisar styles.css para confirmar qué variantes existen en `.stat-card-wrapper.*`.

**Verificación T1c:**
```bash
grep -n "andes-card stat-card\|stat-icon-circle\|stat-card-header" src/interface/design/components/stat_card.py
# → 0 resultados
grep -n "stat-card-wrapper" src/interface/design/components/stat_card.py
# → al menos 1 resultado
```

---

## T2 — Adopt `stat_card()` en 3 páginas

**Prerequisito:** T1c completado.

### T2a — `inicio.py`

**Archivo:** `src/interface/pages/inicio.py`

**Agregar import:**
```python
from src.interface.design.components import stat_card
```

**En `_seccion_stats()`:**
Eliminar la función local `_stat_card()` completamente (líneas ~164-188).
En la llamada `_stat_card(titulo=..., valor=..., icono=..., subtitulo=..., variante=...)`,
reemplazar con `stat_card(titulo=..., valor=..., icono=..., subtitulo=..., variante=...)`.
Los argumentos y el grid wrapper `ui.element("div").classes("stats-grid")` quedan intactos.

**Verificación T2a:**
```bash
grep -n "_stat_card" src/interface/pages/inicio.py
# → 0 resultados
grep -n "stat_card" src/interface/pages/inicio.py
# → al menos 1 resultado (import + llamadas)
```

### T2b — `tablero_estadisticos.py`

**Archivo:** `src/interface/pages/academico/tablero_estadisticos.py`

**Agregar import:**
```python
from src.interface.design.components import stat_card
```

**En `_render_kpis(datos)`:**
El bloque actual (líneas ~109-141) tiene 4 tarjetas inline con `.stat-card-wrapper`.
Reemplazar cada bloque:
```python
# ANTES:
with ui.element("div").classes(f"stat-card-wrapper {var_prom}"):
    with ui.element("div").classes("stat-card-icon-wrap"):
        ThemeManager.icono(Icons.GRADES, size=24)
    ui.label(f"{prom:.1f}").classes("stat-card-value")
    ui.label("Promedio ponderado").classes("stat-card-label")
    ui.label("ajustado al periodo").classes("stat-card-subtitle")

# DESPUÉS:
stat_card(
    titulo    = "Promedio ponderado",
    valor     = f"{prom:.1f}",
    icono     = Icons.GRADES,
    subtitulo = "ajustado al periodo",
    variante  = var_prom,  # "success", "warning", o "error" según _kpi_variante()
)
```
Repetir para las otras 3 tarjetas (asistencia, en riesgo, actividades).
El wrapper `ui.element("div").classes("tablero-kpi-row")` queda intacto.

**Verificación T2b:**
```bash
grep -n "stat-card-wrapper" src/interface/pages/academico/tablero_estadisticos.py
# → 0 resultados
grep -n "stat_card" src/interface/pages/academico/tablero_estadisticos.py
# → al menos 1 resultado
```

### T2c — `estudiantes.py`

**Archivo:** `src/interface/pages/academico/estudiantes.py`

**Agregar import:**
```python
from src.interface.design.components import stat_card
```

**En `resultado_refreshable()` (~líneas 337-350):**
Las 3 tarjetas de resultados del CSV masivo:
```python
# ANTES:
with ui.element("div").classes("tablero-kpi-row"):
    with ui.element("div").classes("stat-card-wrapper info"):
        ui.label(str(resultado.total_procesadas)).classes("stat-card-value")
        ui.label("Total procesadas").classes("stat-card-label")
    # ... más tarjetas

# DESPUÉS:
with ui.element("div").classes("tablero-kpi-row"):
    stat_card("Total procesadas", resultado.total_procesadas, "check_circle", variante="info")
    stat_card("Exitosas", resultado.exitosas, "check",
              variante="success" if resultado.exitosas > 0 else "info")
    stat_card("Fallidas", resultado.fallidas, "error",
              variante="danger" if resultado.fallidas > 0 else "success")
```

El resto de `resultado_refreshable()` (errores detallados, botón limpiar) queda intacto.

---

## T3 — `page_header()` adoptado en 8 páginas

**Prerequisito:** ninguno.

### Patrón de import a agregar en cada página:
```python
from src.interface.design.components import page_header
```

### Por página (aplicar patrón de design.md §4):

**T3-1: `admin/grupos.py`**
- Localizar en `contenido()`: el `with ui.element("div").classes("panel-card"):` inicial
- Extraer el bloque `with ui.row().classes("items-center gap-2 mb-4"):` con icono + label
- ANTES del panel-card, agregar:
  ```python
  page_header(
      titulo    = "Gestión de Grupos",
      subtitulo = "Crea y administra los grupos académicos de la institución",
      icono     = Icons.GROUPS,
  )
  ```
- Eliminar el bloque de icono + label del interior del panel-card

**T3-2: `admin/asignaturas.py`**
```python
page_header(
    titulo    = "Gestión de Asignaturas",
    subtitulo = "Áreas de conocimiento y asignaturas del currículo",
    icono     = Icons.SUBJECTS,
)
```

**T3-3: `admin/asignaciones.py`**
```python
page_header(
    titulo    = "Asignaciones Docentes",
    subtitulo = "Asignación de docentes a grupos y asignaturas por periodo",
    icono     = "assignment_ind",
)
```

**T3-4: `admin/usuarios.py`**
```python
page_header(
    titulo    = "Gestión de Usuarios",
    subtitulo = "Cuentas de usuario y roles del sistema",
    icono     = Icons.TEACHERS,
)
```
Si el botón "Nuevo usuario" existe como action inline antes del panel, añadirlo a `acciones`:
```python
acciones = [{"label": "Nuevo usuario", "on_click": _abrir_crear_usuario,
              "icono": "person_add", "variante": "primary"}]
```

**T3-5: `admin/configuracion_sie.py`**
```python
page_header(
    titulo    = "Configuración del SIE",
    subtitulo = "Periodos académicos y configuración del año escolar",
    icono     = "settings",
)
```
**Nota**: esta página tiene múltiples `ThemeManager.icono()` en sub-secciones internas
(líneas ~107 y ~145 con iconos de "event_busy" y "business"). **No tocarlos** — solo
reemplazar el header principal (el `with ui.row().classes("items-center gap-2 mb-4")`
con `ThemeManager.icono(Icons.CONFIG, ...)` y el `ui.label("Configuración SIE")`).

**T3-6: `admin/configuracion_institucion.py`**
```python
page_header(
    titulo    = "Información Institucional",
    subtitulo = "Datos básicos y generales de la institución educativa",
    icono     = "business",
)
```

**T3-7: `academico/estudiantes.py`**
Los botones "Matricular" y "Carga CSV" actuales pasan a `acciones` del header:
```python
page_header(
    titulo    = "Gestión de Estudiantes",
    subtitulo = "Matrícula, estado y PIAR de estudiantes",
    icono     = Icons.STUDENTS,
    acciones  = [
        {"label": "Matricular",  "on_click": _abrir_dialog_matricula, "icono": "person_add",   "variante": "primary"},
        {"label": "Carga CSV",   "on_click": _abrir_dialog_csv,       "icono": "upload_file",   "variante": "secondary"},
    ],
)
```
Si estos botones estaban inline en un panel header o en una fila separada, se eliminan de allí.

**T3-8: `academico/horarios.py`**
```python
page_header(
    titulo    = "Horarios",
    subtitulo = "Grilla semanal de bloques de clase por grupo",
    icono     = Icons.SCHEDULE,
)
```
Si el rol es admin/director y hay botón "Agregar bloque":
```python
acciones = [{"label": "Agregar bloque", "on_click": _abrir_crear_bloque,
              "icono": "add", "variante": "primary"}]
```

**Verificación T3:**
```bash
grep -rn "page_header" src/interface/pages/admin/
# → debe aparecer en los 6 archivos admin
grep -rn "page_header" src/interface/pages/academico/estudiantes.py src/interface/pages/academico/horarios.py
# → debe aparecer en ambos
```

---

## T4 — `confirm_dialog()` adoptado en ~8 páginas

**Prerequisito:** ninguno.

### Patrón de import a agregar en cada página:
```python
from src.interface.design.components import confirm_dialog
```
(Algunos archivos ya importan cosas de components; añadir a ese bloque.)

### Por página:

**T4-1: `admin/grupos.py`**
Función `_eliminar_grupo(grupo_id, codigo)`:
```python
def _eliminar_grupo(grupo_id: int, codigo: str) -> None:
    confirm_dialog(
        titulo          = "Eliminar grupo",
        mensaje         = f"¿Eliminar el grupo {codigo}? Esta acción es irreversible.",
        on_confirm      = lambda: _confirmar_eliminar_grupo(grupo_id, codigo),
        variante        = "danger",
        texto_confirmar = "Eliminar",
    )
```
Renombrar la función de confirmación para que no espere el argumento `dlg`:
`_confirmar_eliminar(dlg, grupo_id, codigo)` → `_confirmar_eliminar_grupo(grupo_id, codigo)`
(quitar el `dlg.close()` de dentro, ya lo hace `confirm_dialog` internamente).

**T4-2: `admin/asignaturas.py`**
Localizar los dialogs de eliminar área y asignatura (~líneas 111, 141, 204, 232).
Identificar cuáles son confirms simples (solo label + 2 botones) y migrarlos.
Los que tienen inputs (edit area, edit asignatura) se omiten.

**T4-3: `admin/asignaciones.py`**
`_desactivar_asignacion()` (línea ~164). Tiene 2 `ui.label()` (uno principal +
uno con nota sobre el historial). Concatenarlos en el parámetro `mensaje`:
```python
confirm_dialog(
    titulo          = "Desactivar asignación",
    mensaje         = f"¿Desactivar asignación '{label}'? El histórico de notas y asistencia se conserva.",
    on_confirm      = lambda: _confirmar_desactivar(asig_id, label),
    variante        = "warning",
    texto_confirmar = "Desactivar",
)
```
Renombrar `_confirmar_desactivar(dlg, asig_id, label)` → `_confirmar_desactivar(asig_id, label)`.

**T4-4: `admin/usuarios.py`**
Solo `_desactivar_usuario()` (línea ~128) es confirm simple — migrar:
```python
confirm_dialog(
    titulo          = "Desactivar usuario",
    mensaje         = f"¿Desactivar la cuenta de '{nombre}'? No podrá iniciar sesión.",
    on_confirm      = lambda: _confirmar_desactivar(usuario_id, nombre),
    variante        = "danger",
    texto_confirmar = "Desactivar",
)
```
Renombrar `_confirmar_desactivar(dlg, usuario_id, nombre)` → `_confirmar_desactivar(usuario_id, nombre)` (quitar `dlg`).

**`_cambiar_rol()` (línea ~158) — NO migrar**: contiene `ui.select` para elegir
el nuevo rol; es un CRUD dialog que queda intacto.

**T4-5: `academico/estudiantes.py`**
El confirm de retiro (~línea 566, función `_confirmar_retiro`):
```python
confirm_dialog(
    titulo          = "Retirar estudiante",
    mensaje         = f"¿Retirar a {nombre} de la matrícula? El estado cambiará a Retirado.",
    on_confirm      = lambda: _ejecutar_retiro(estudiante_id),
    variante        = "danger",
    texto_confirmar = "Retirar",
)
```

**T4-6: `evaluacion/configuracion_evaluacion.py`**
El dialog de borrar categoría (~línea 167):
```python
confirm_dialog(
    titulo          = "Eliminar categoría",
    mensaje         = f"¿Eliminar la categoría '{nombre}'? Se perderán las actividades asociadas.",
    on_confirm      = lambda: _ejecutar_eliminar_categoria(cat_id),
    variante        = "danger",
    texto_confirmar = "Eliminar",
)
```

**T4-7: `evaluacion/habilitaciones.py`**
**No aplica** — el módulo no tiene confirm simple de eliminar habilitación.
El único dialog es `_registrar_nota_dialog()` que contiene inputs (`ui.number`,
`ui.input`). No hay nada que migrar aquí.

**T4-8: `evaluacion/planes_mejoramiento.py`**
**No aplica** — `_cerrar_plan_dialog()` (línea ~156) contiene `ui.select`
(estado de cierre) + `ui.textarea` (observación obligatoria con validación).
Es un CRUD dialog; queda intacto.

**Verificación T4:**
```bash
grep -rn "confirm_dialog" src/interface/pages/
# → al menos 6 resultados en archivos distintos:
#   grupos, asignaturas, asignaciones, usuarios, estudiantes, configuracion_evaluacion
# Comprobar que los dialogs simples anteriores ya no tienen 'ui.dialog' solo con ui.label:
grep -n "with ui.dialog" src/interface/pages/admin/grupos.py
# → solo debe retornar el dialog _abrir_editar() (CRUD), no el de eliminar
```

---

## T5 — `badge_*` adoptado en 6 páginas

**Prerequisito:** ninguno.

### Patrón de import:
```python
from src.interface.design.components import badge_estado_general, status_badge
```

### Por página:

**T5-1: `admin/asignaciones.py`**
```python
# ANTES:
ui.badge("Activa").classes("w-20 badge-success")
ui.badge("Inactiva").classes("w-20 badge-neutral")
# DESPUÉS:
badge_estado_general(True)   # para Activa
badge_estado_general(False)  # para Inactiva
```

**T5-2: `admin/usuarios.py`**
```python
# ANTES:
ui.badge("Activo").classes("w-20 badge-success")
ui.badge("Inactivo").classes("w-20 badge-neutral")
# DESPUÉS:
badge_estado_general(True)
badge_estado_general(False)
```
El badge de rol (`ui.badge(rol).classes(f"... {_ROL_CLASES.get(rol, ...)}")`) →
`status_badge(rol, _ROL_CLASES.get(rol_str, "neutral"))` si `_ROL_CLASES` tiene
variantes compatibles con las clases CSS de badge. Verificar los valores del dict.

**T5-3: `admin/configuracion_sie.py`**
```python
# ANTES:
ui.badge("Activo").classes("badge-success")
# DESPUÉS:
badge_estado_general(True)
```

**T5-4: `evaluacion/habilitaciones.py`**
```python
# ANTES (aproximado):
ui.badge(estado_val).classes(f"w-24 text-center {_ESTADO_CLASES.get(estado_val, 'badge-neutral')}")
# DESPUÉS: extraer la variante del dict y usar status_badge:
variante = _ESTADO_CLASES.get(estado_val, "badge-neutral").replace("badge-", "")
status_badge(estado_val, variante)
```
El dict `_ESTADO_CLASES` puede quedar como helper para la variante string.

**T5-5: `evaluacion/planes_mejoramiento.py`**
Mismo patrón que T5-4.

**T5-6: `evaluacion/planilla_notas.py`**
La línea `ui.badge(estado_val.capitalize()).classes(f"w-24 text-center {badge_clase}")`:
Verificar si es un render Python (dentro de un slot NiceGUI) o dentro de un aggrid
cellRenderer. Si es Python NiceGUI → `status_badge(estado_val.capitalize(), badge_clase.replace("badge-",""))`.
Si es aggrid JS HTML string → DEJAR INTACTO (excepción).

**Verificación T5:**
```bash
grep -rn "ui.badge(\"Activo\")\|ui.badge(\"Inactivo\")\|ui.badge(\"Activa\")\|ui.badge(\"Inactiva\")" src/interface/pages/
# → 0 resultados
grep -rn "badge_estado_general\|status_badge" src/interface/pages/
# → al menos 5-6 archivos
```

---

## T6 — Verificación final

```powershell
# PowerShell (encoding correcto en Windows)
$env:PYTHONIOENCODING = "utf-8"
python init.py
```
→ DEBE SER 100% verde. Si falla algún check de design system, el implementer
lo corrige antes de declarar done.

```bash
pytest tests/ -q
```
→ ≥607 passed, 0 failed.

### Greps de comprobación final:
```bash
# 0 helpers locales de stat_card en pages:
grep -rn "_stat_card\|stat-card-wrapper" src/interface/pages/ --include="*.py"

# 0 ui.badge semánticos sin migrar:
grep -rn "ui\.badge\(\"Activo\"\)\|ui\.badge\(\"Activo\"\)\|ui\.badge\(\"Activa\"\)\|ui\.badge\(\"Inactiva\"\)\|ui\.badge\(\"Inactivo\"\)" src/interface/pages/

# page_header presente en 8 páginas objetivo:
grep -rl "page_header" src/interface/pages/admin/ src/interface/pages/academico/

# confirm_dialog presente en páginas objetivo:
grep -rl "confirm_dialog" src/interface/pages/

# 0 style= estáticos en confirmation_card.py:
grep -n "style=" src/interface/design/components/confirmation_card.py
```

### Actualizar estado al finalizar:
El implementer escribe resultado en `progress/impl_paso_10j.md`.
El reviewer escribe su veredicto en `progress/review_paso_10j.md`.
Solo tras reviewer PASS, el leader actualiza `step_list.json` a `done`.
