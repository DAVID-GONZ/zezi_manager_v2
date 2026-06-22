# paso_40 — Dimensiones del chip de contexto por página (no por rol)

## Contexto y decisión (David)

El selector de contexto (`context_selector.py`) tiene 3 pasos: **Periodo → Grupo → Asignatura**, y hoy el paso Asignatura se muestra según `mostrar_asignatura`, que `_topbar` fija como `(usuario_rol == "profesor")` — **por ROL, no por página**. Defectos:
- Un **directivo** (director/coordinador) en páginas que necesitan asignación (Planilla, Asistencia, Observaciones, Habilitaciones…) — todas abiertas a directivos — **nunca ve el selector de Asignatura** → no puede fijar el contexto completo. **Bug.**
- Un **profesor** ve el paso Asignatura incluso en páginas que solo usan periodo/grupo → ruido.

Mejora: el chip muestra **exactamente las dimensiones que cada página consume**, declaradas por la página, no derivadas del rol.

## Tareas

### T1 — Flags de dimensión en el layout y el selector
- `context_selector.py`: `context_chip` y `abrir_selector` ya tienen `mostrar_asignatura`; añadir `mostrar_grupo: bool = True`. El diálogo renderiza el paso Grupo solo si `mostrar_grupo` y el paso Asignatura solo si `mostrar_asignatura`; `_actualizar_btn_aplicar` exige solo las dimensiones visibles (asignatura ⇒ grupo ⇒ periodo). Periodo siempre visible (es la base).
- `layout.py` (`app_layout` + `_topbar`): añadir parámetros `mostrar_grupo: bool = True` y `mostrar_asignatura: bool = True`, propagarlos a `context_chip`. **Eliminar la heurística por rol** `mostrar_asignatura=(usuario_rol == "profesor")` — pasa a venir de la página. Defaults `True/True` (comportamiento full actual para páginas que no especifiquen).

### T2 — Clasificar cada página por las dimensiones que usa (REGLA autoritativa)
Para cada página que muestra el chip (las que NO tienen `mostrar_contexto=False`), determinar por **uso real de contexto** y fijar los flags en su `app_layout(...)`:
- Lee `ctx.asignacion_id` → `mostrar_asignatura=True` (implica grupo+periodo).
- Lee `ctx.grupo_id` pero NO `asignacion_id` → `mostrar_grupo=True, mostrar_asignatura=False`.
- Lee solo `ctx.periodo_id`/`anio_id` (agregados institucionales) → `mostrar_grupo=False, mostrar_asignatura=False`.

**Hipótesis de partida (VERIFICAR y corregir leyendo cada página):**
- Asignatura (P+G+A): `planilla_notas`, `registro_asistencia`, `observaciones`, `comportamiento`, `notas_convivencia`, `habilitaciones`, `configuracion_evaluacion`, `planes_mejoramiento`, `tablero_estadisticos` (drill por asignación).
- Grupo (P+G): `consolidado_notas`, `consolidado_asistencia`, `boletin_periodo`, `admin/asignaciones`, `horarios_hub` (verificar: ¿usa asignación?).
- Solo periodo/año: `estadisticos` (institucional), `cierre_periodo`, `cierre_anio`, `boletin_anual`, `inicio` (dashboard).
La REGLA manda sobre la hipótesis: si al leer la página el uso difiere, fijar los flags según el uso real y anotarlo en el progress.

### T3 — Verificación
- `python init.py` VERDE (baseline 1178 passed, 1 skipped). check_design + check_imports interface en verde.
- Test: el selector renderiza el paso Asignatura **según el flag de página, no el rol** (un directivo en una página con `mostrar_asignatura=True` ve el paso; un profesor en una página con `mostrar_asignatura=False` no lo ve). Y el botón Aplicar se habilita con solo las dimensiones visibles.
- `progress/impl_paso_40.md` (tabla página → dimensiones; confirmación de que se eliminó la heurística por rol).

## criterio_done
El chip/selector muestra las dimensiones (periodo/grupo/asignatura) que cada página realmente usa, declaradas por la página vía `app_layout` (no por rol); se eliminó `mostrar_asignatura=(rol=="profesor")`; los directivos ya ven el selector de asignatura en las páginas que lo requieren y no aparece en las que no; el botón Aplicar exige solo las dimensiones visibles; `python init.py` verde.
