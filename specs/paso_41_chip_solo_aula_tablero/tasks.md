# paso_41 — Chip de contexto solo en Aula + Tablero Estadístico

## Contexto y decisión (David)

El chip de contexto solo debe aparecer donde **gestiona algo útil**: las páginas de **Aula** y el **Tablero Estadístico**. En el resto, o no se usa el contexto o se gestiona con **selectores internos** de la propia página. Apagar el chip en todo lo demás (incluido el Dashboard de inicio).

Esto refuerza paso_39/40: el chip queda en **6 páginas**; en las demás `mostrar_contexto=False`. Los flags de dimensión de paso_40 (`mostrar_grupo`/`mostrar_asignatura`) siguen vigentes SOLO en las 6 que conservan el chip.

### KEEP — chip ON (6):
- Aula: `/evaluacion/planilla` (planilla_notas), `/asistencia` (registro_asistencia), `/convivencia/observaciones`, `/convivencia/comportamiento`, `/convivencia/notas` (notas_convivencia).
- `/academico/tablero` (tablero_estadisticos).
Estas operan por grupo+asignación → dimensiones completas (periodo+grupo+asignatura). Mantener/ajustar sus flags a full.

### OFF — `mostrar_contexto=False` (13, las que hoy aún muestran chip):
`inicio`, `horarios_hub`, `admin/asignaciones`, `evaluacion/cierre_anio`, `evaluacion/cierre_periodo`, `evaluacion/configuracion_evaluacion`, `evaluacion/habilitaciones`, `evaluacion/planes_mejoramiento`, `informes/boletin_anual`, `informes/boletin_periodo`, `informes/consolidado_asistencia`, `informes/consolidado_notas`, `informes/estadisticos`.

(Las 11 ya apagadas en paso_39 — estudiantes, admin catálogos, auditoria, usuarios, diagnostico — siguen off.)

## Tareas

### T1 — Apagar el chip en las 13 + verificar que no se rompe la selección
- En cada una de las 13: poner `mostrar_contexto=False` en `app_layout(...)` y **eliminar los flags de dimensión** (`mostrar_grupo`/`mostrar_asignatura`) que quedan sin efecto, y el `on_context_change`/callback de chip que quede muerto (la página ya no recibe cambios del chip).
- **SEGURIDAD (no romper):** para cada una, verificar que el usuario sigue pudiendo elegir el contexto que la página necesita:
  - si la página tiene **selectores internos** (dropdowns de periodo/grupo/etc.) → OK, apagar el chip.
  - si la página solo **lee** `ctx` fijado en otra parte (p.ej. dashboards/informes que reportan sobre el contexto activo) y eso es aceptable → OK.
  - si una página dependía **únicamente del chip** para elegir una dimensión que necesita y **no tiene selector interno** → **NO la rompas**: déjala con el chip o añade el selector mínimo, y **repórtalo** en el progress para decisión. (Según David, todas tienen selector o no lo necesitan; confirmar caso por caso.)

### T2 — Confirmar las 6 KEEP
- Verificar que las 6 KEEP conservan `mostrar_contexto` (no `False`) y muestran las dimensiones correctas (Aula y Tablero = periodo+grupo+asignatura). Ajustar si paso_40 las dejó con un subconjunto incorrecto.

### T3 — Verificación
- `python init.py` VERDE (baseline 1178 passed, 1 skipped; corregir fallout — tests que asumían chip/`on_context_change` en páginas ahora sin chip). check_design + check_imports interface en verde.
- Test: el chip (context_chip) se renderiza SOLO en las 6 rutas KEEP y no en las OFF.
- `progress/impl_paso_41.md` (lista KEEP/OFF aplicada, verificación de selectores internos por página OFF, cualquier página reportada por no tener selector, output de init.py).

## criterio_done
El chip de contexto aparece únicamente en las 5 páginas de Aula + el Tablero Estadístico; en el resto está apagado (`mostrar_contexto=False`), sin flags de dimensión muertos ni callbacks de chip huérfanos; ninguna página quedó sin forma de elegir el contexto que necesita (las que dependían solo del chip se reportaron); `python init.py` verde.
