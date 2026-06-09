# Requisitos — paso_11z_housekeeping

## Contexto

`python init.py` reporta 53 violaciones del design system en `src/interface/pages/*`.
Estas violaciones bloquean cualquier paso posterior (regla dura de `CLAUDE.md`:
"No declares un paso done sin que `python init.py` esté completamente verde").

Este paso es **desbloqueante puro**: no añade funcionalidad, no cambia comportamiento
observable, solo normaliza el código de las páginas al design system existente para
que el harness vuelva a verde.

## Alcance

Módulos afectados (solo lectura+escritura dentro de `src/interface/pages/`):

- `src/interface/pages/academico/estudiantes.py`
- `src/interface/pages/academico/horarios.py`
- `src/interface/pages/academico/tablero_estadisticos.py`
- `src/interface/pages/admin/configuracion_sie.py`
- `src/interface/pages/evaluacion/cierre_periodo.py`
- `src/interface/pages/evaluacion/configuracion_evaluacion.py`
- `src/interface/pages/evaluacion/habilitaciones.py`
- `src/interface/pages/evaluacion/planes_mejoramiento.py`
- `src/interface/pages/evaluacion/planilla_notas.py`
- `src/interface/pages/informes/estadisticos.py`

**Fuera de scope:**
- `src/interface/design/*` — los componentes/tokens no se tocan en este paso.
- `src/services/`, `src/infrastructure/`, `src/domain/` — el problema es solo de presentación.
- El módulo `tablero_estadisticos.py:763` que llama a `_repo()` directo — eso es un
  bug arquitectónico de capa, no de design system: se aborda aparte si init.py también
  lo reporta como violación (sección C).

## Requisitos funcionales

### R1 — Eliminación de `ui.icon()` en páginas

Toda llamada `ui.icon("…")` o `ui.icon("…", color=…, size=…)` en los archivos del scope
debe reemplazarse por `ThemeManager.icono(...)` con parámetros equivalentes.

- 24 ocurrencias confirmadas en 5 archivos (lista exacta en `design.md` §A).
- Color hex hardcodeado en `habilitaciones.py:453` (`color="#d97706"`) se reemplaza por
  una clase CSS del design system; el color exacto se conserva visualmente.

### R2 — Eliminación de `ui.button(icon=…)`

Las 3 ocurrencias en `estudiantes.py:321/326/331` se migran al patrón:

```python
with ui.button(on_click=…).classes("…"):
    ThemeManager.icono(Icons.X, size=18)
```

### R3 — Colores Quasar hardcodeados

- `estudiantes.py:307`: `"teal" if posee_piar else "grey-4"` → clase CSS del design
  system (`badge-info` / `badge-neutral`).
- `planes_mejoramiento.py:290`: `ui.badge("Sin corte", color="grey")` → `badge-neutral`.

### R4 — `cellStyle` en ag-Grid

Las 3 ocurrencias en `planilla_notas.py:483/509/518` se migran a `cellClass` o
`cellClassRules`. Las clases necesarias se añaden a `styles.css` solo si no existen:

- `483`: `{"fontSize": "11px"}` → clase `.ag-cell-xs` (añadir en styles.css si falta).
- `509`: `{"color": "#0284C7"}` → clase `.ag-cell-info` (color = `--color-info` o
  `--desempeno-alto`).
- `518`: `{"color": "#DC2626"}` → clase `.ag-cell-error` (color = `--color-error`).

### R5 — Imports prohibidos de modelos de dominio en páginas

Tres páginas importan modelos de `src.domain.models.*`. Esto rompe la separación de
capas (interfaz no debe conocer modelos internos del dominio):

- `configuracion_sie.py:32` → `src.domain.models.configuracion`
- `habilitaciones.py:30` → `src.domain.models.nivelacion`
- `estadisticos.py:34` → `src.domain.models.dtos`

**Decisión:** estos imports se reemplazan por uso indirecto a través del servicio
correspondiente (`Container.*_service()`), o por anotaciones de tipo dentro de
`if TYPE_CHECKING:`. La forma exacta depende de cada caso (ver `design.md` §E).

Si un import es estrictamente necesario para que un servicio devuelva el modelo,
se documenta el motivo y se mueve a `TYPE_CHECKING`.

### R6 — Clases CSS Tailwind-style no soportadas

20 clases utilitarias (`col-3`, `bg-blue-50`, `grid-cols-1`, `truncate`, `h-[600px]`,
etc.) se sustituyen por el equivalente del design system o por una clase utilitaria
nueva definida en `styles.css`.

Inventario completo y mapeo en `design.md` §F.

### R7 — No cambio funcional observable

La página debe comportarse y verse **idénticamente** al estado actual después de los
cambios. Esto es refactor puro; cualquier diferencia visual reportada por el reviewer
es un regress que rechaza el paso.

### R8 — Criterio de cierre

`python init.py` retorna exit-code 0 sin violaciones del design system y los 715 tests
unitarios siguen verdes.

## Requisitos no funcionales

- **Reversibilidad:** cada archivo se modifica de forma autocontenida; no se introducen
  dependencias cruzadas nuevas.
- **No deuda nueva:** no se introduce ninguna clase CSS o helper que no esté
  documentada en `design.md`.
