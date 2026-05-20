# Requisitos — paso_10j_component_adoption

## Contexto

El paso_10i saneó las violaciones CSS en los components y creó buttons.py.
Sin embargo, todos los components del design system (`page_header`, `stat_card`,
`confirm_dialog`, `badge_*`, `performance_indicator`, `data_table`, `base_form`)
fueron creados pero **ninguna página los usa**. Las páginas implementan sus propias
versiones inline, generando duplicación y riesgo de divergencia visual.

Hay además un defecto de diseño: el componente `stat_card()` usa clases CSS
`.andes-card.stat-card` (layout horizontal), mientras que las páginas implementan
la variante `.stat-card-wrapper` (layout vertical con borde coloreado y hover
effect), que es visualmente más rica. Se deben unificar.

## Alcance

Módulo afectado: `src/interface/` (páginas y design system)

## Requisitos funcionales

### R1 — Compliance CSS post-10i (auditoría)
Todos los archivos en `src/interface/design/components/` deben pasar la regla
de conventions.md §6: ningún `style=""` con valores estáticos. Únicamente los
valores genuinamente dinámicos (calculados en tiempo de ejecución) pueden usar
`style=`. Los valores como `color:var(--X)` si son estáticos van en clases CSS.

**Excepción documentada:** `confirmation_card.py` usa `style=` para `background`
y `border-left` calculados dinámicamente desde `variante`. Si los 3 variantes
están hardcodeados en el dict `_COLOR_MAP`, moverlos a clases CSS es obligatorio.

### R2 — `stat_card()` unificado con `.stat-card-wrapper`
El componente `stat_card()` debe producir el layout de `.stat-card-wrapper`:
vertical, icono arriba, borde izquierdo coloreado, hover effect. No debe usar
`.andes-card.stat-card` como antes (layout horizontal). La API pública no cambia:
`stat_card(titulo, valor, icono, subtitulo, variante)`.

### R3 — `stat_card()` adoptado en 3 páginas
Las páginas que definen sus propios helpers inline para tarjetas KPI deben
eliminarlo y usar el componente:
- `inicio.py` — función local `_stat_card()` en `_seccion_stats()`
- `tablero_estadisticos.py` — inline en `_render_kpis()`
- `estudiantes.py` — inline en `resultado_refreshable()` (3 tarjetas de resumen CSV)

### R4 — `page_header()` adoptado en 8 páginas
Las páginas que construyen su título de página con `ThemeManager.icono + ui.label`
dentro del primer `panel-card` deben extraerlo y usar `page_header()` antes de
los paneles:
- `admin/grupos.py`
- `admin/asignaturas.py`
- `admin/asignaciones.py`
- `admin/usuarios.py`
- `admin/configuracion_sie.py`
- `admin/configuracion_institucion.py`
- `academico/estudiantes.py`
- `academico/horarios.py`

El patrón de sustitución:
```python
# Antes (dentro del primer panel-card):
with ui.row().classes("items-center gap-2 mb-4"):
    ThemeManager.icono(Icons.X, size=22, color="var(--color-primary)")
    ui.label("Título de Página").classes("text-xl font-bold")

# Después (ANTES del primer panel-card, fuera de él):
page_header(
    titulo   = "Título de Página",
    subtitulo = "Descripción breve opcional",
    icono    = Icons.X,
)
# El ThemeManager.icono + label se ELIMINA del panel-card
```

Notas:
- `inicio.py` — NO adopta `page_header()`; su `_seccion_saludo()` es una hero card
  diferente al patrón estándar. Queda excluida.
- `tablero_estadisticos.py` — NO adopta `page_header()`; la página empieza con KPIs
  sin cabecera separada. Queda excluida.
- Para páginas con botón de acción principal (ej: "Nuevo estudiante"), ese botón
  pasa al parámetro `acciones` de `page_header()`.

### R5 — `confirm_dialog()` adoptado en confirmaciones simples
Los diálogos que siguen el patrón "título + mensaje + Cancelar + Confirmar" sin
inputs adicionales deben reemplazarse con `confirm_dialog()`. Los CRUD forms
(dialogs con múltiples ui.input/ui.select) quedan intactos.

Diálogos a migrar (ver tabla completa en design.md):
- `grupos.py` — `_eliminar_grupo()` (1 confirm simple)
- `asignaturas.py` — `_eliminar_area()` y `_eliminar_asignatura()` (2 confirms)
- `asignaciones.py` — confirmar desactivar asignación (1 confirm)
- `usuarios.py` — `_desactivar_usuario()` y `_cambiar_rol()` (2 confirms)
- `estudiantes.py` — `_confirmar_retiro()` (1 confirm)
- `configuracion_evaluacion.py` — confirmar borrar categoría (1 confirm)
- `habilitaciones.py` — confirmar eliminar habilitación (1 confirm si existe)
- `planes_mejoramiento.py` — confirmar cerrar/eliminar plan (1 confirm)

Diálogos que QUEDAN INLINE (demasiado complejos para el componente):
- `cierre_periodo.py` — muestra conteo dinámico de estudiantes + multi-párrafo
- `cierre_anio.py` — similar
- Todos los CRUD dialogs (crear/editar grupo, asignatura, usuario, etc.)

### R6 — `status_badge` / `badge_*` adoptados en páginas con `ui.badge()` semántico
Las páginas que usan `ui.badge("Activo").classes("badge-success")` directamente
deben reemplazarlo con las funciones del design system.

Reglas:
- `ui.badge("Activo").classes("... badge-success")` → `badge_estado_general(True)`
- `ui.badge("Inactivo").classes("... badge-neutral")` → `badge_estado_general(False)`
- `ui.badge("Inactiva").classes("... badge-neutral")` → `badge_estado_general(False)`
- `ui.badge(nivel).classes(f"... {CLASES_MAP.get(nivel, ...)}")` → `status_badge(nivel, variante)` donde variante viene del mismo mapa pero como argumento explícito
- Contador numérico: `ui.badge(str(n)).classes("badge-primary")` → **EXCEPCIÓN**: queda inline (no es un badge de estado semántico)
- Aggrid `cellRenderer` HTML strings → **EXCEPCIÓN**: son JS context, quedan inline

Páginas afectadas:
- `admin/asignaciones.py`
- `admin/usuarios.py`
- `admin/configuracion_sie.py`
- `evaluacion/planilla_notas.py` (solo los renders Python, no los aggrid JS)
- `evaluacion/habilitaciones.py`
- `evaluacion/planes_mejoramiento.py`

### R7 — `performance_indicator()` adoptado donde haya barras de desempeño inline
Si la página tiene un bloque que construye manualmente una barra de progreso
coloreada para representar desempeño académico (no barras de tiempo/progreso
de periodo), debe usar `performance_indicator()`.

Evaluación página por página (ver design.md §7 para detalle). En las páginas
actuales, `performance_indicator` no tiene adopción forzada porque:
- `inicio.py` — tiene `period-bar` para progreso de fechas, no desempeño académico
- `tablero_estadisticos.py` — usa ECharts gauge/donut, no barra Python
El componente queda disponible para nuevas secciones (informes, boletines).

**Excepción real:** si la revisión del implementer encuentra una sección que
construya manualmente `perf-bar-track + perf-bar-fill` en alguna página, debe
sustituirse por `performance_indicator()`.

### R8 — `data_table()` y `base_form()` no forzados en páginas existentes
- `data_table()` usa `ui.table` bajo el capó. Las páginas con datos usan `ui.aggrid`
  (más potente, con renders personalizados). No se fuerza migración a `data_table`.
  Queda disponible para páginas futuras sin aggrid.
- `base_form()` está diseñado para formularios standalone. Los CRUD forms existentes
  están en `ui.dialog()` con bindings específicos que requieren acceso directo a cada
  widget. No se fuerza. Queda disponible para nuevas páginas.

### R9 — 0 regresiones
Al final del paso, `python init.py` debe pasar completamente verde y la suite
de tests `pytest tests/ -q` debe reportar ≥607 tests pasando.

### R10 — Clase `.confirmation_card` CSS corregida
`confirmation_card.py` usa `card.style(f"background:{bg_color}; border-left: 4px solid {icono_color}")`.
Estos 3 valores (background por variante, border-left color por variante) son
estáticos y deben moverse a clases CSS:
- `.confirmation-card-danger`, `.confirmation-card-warning`, `.confirmation-card-info`
- El `style=` del card desaparece; se reemplaza por `.classes(f"andes-card confirmation-card-{variante}")`

## Criterio de completado
- `python init.py` → verde (0 errores en todas las comprobaciones)
- `pytest tests/ -q` → ≥607 passed, 0 failed
- Grep `ui.badge\("Activo"\)` en pages/ → 0 resultados
- Grep `ui.badge\("Inactivo"\)` en pages/ → 0 resultados
- Grep `_stat_card\(` en pages/ → 0 resultados (helper local eliminado)
- Grep `stat-card-wrapper` en pages/*.py → 0 resultados (solo en styles.css)
- Grep `page_header` en admin/*.py y academico/[estudiantes,horarios].py → presente
- Grep `confirm_dialog` en las 8 páginas objetivo → presente
